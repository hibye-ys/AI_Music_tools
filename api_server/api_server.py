import json
import os
import uuid
from typing import Literal
from typing import Optional

import boto3
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = FastAPI()


class APIServerSettings(BaseSettings):
    bucket_name: str = "s3musicproject"
    aws_access_key: str = os.environ.get("AWS_ACCESS_KEY")
    aws_secret_access_key: str = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region_name: str = os.environ.get("REGION_NAME")
    mongodb_uri: str = os.environ.get("MONGODB_URI")


settings = APIServerSettings()


class DownloadRequest(BaseModel):
    filename: str
    artist: str
    user_id: str


class SeparateResponse(BaseModel):
    remote_path: str
    message_id: str
    user_id: str


class VCInferenceResponse(BaseModel):
    remote_path: str
    message_id: str


class VCTrainingResponse(BaseModel):
    message_id: str


class DownloadResponse(BaseModel):
    vocal: Optional[str]
    instrum: Optional[str]
    status: Literal["Processing", "Completed"]


class SeparationTask(BaseModel):
    user_id: str
    artist: str
    Origin_file_url: str


class CheckDB(BaseModel):
    user_id: str
    artist: str
    filename: str


def get_s3_client(settings: APIServerSettings):
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )


def get_sqs_client(settings: APIServerSettings):
    return boto3.resource(
        "sqs",
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )


def save_info_to_separationTask(save_data: SeparationTask, settings: APIServerSettings):
    mongo = MongoClient(settings.mongodb_uri)
    db = mongo["music_tools"]
    collection = db["separation"]

    document = {
        "user_id": save_data.user_id,
        "artist": save_data.artist,
        "Origin_file_url": save_data.Origin_file_url,
        "vocal_url": None,
        "instrum_url": None,
        "trained": False,
        "vc_vocal_url": None,
    }

    result = collection.insert_one(document)

    return result.inserted_id


def check_db_for_download(requests: CheckDB):
    try:
        mongo = MongoClient(settings.mongodb_uri)
        db = mongo["music_tools"]
        collection = db["separation"]
        filename = os.path.splitext(requests.filename)[0]
        query_result = collection.find_one(
            {
                "user_id": requests.user_id,
                "artist": requests.artist,
                "vocal_url": f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/public/{requests.user_id}/vocal/{filename}_vocals.wav",
                "instrum_url": f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/public/{requests.user_id}/instrument/{filename}_instrum.wav",
            }
        )

        if query_result is None:
            return "No download URI found", "No download URI found"

        urls = [
            query_result.get("vocal_url", "No download vocal URI found"),
            query_result.get("instrum_url", "No download instrum URI found"),
        ]
        return urls
    except PyMongoError as e:
        print(f"MongoDB error: {e}")
        return "Error querying MongoDB", "Error querying MongoDB"


@app.post("/separate", response_model=SeparateResponse)
def request_to_inference(user_id: str, artist: str, audio: UploadFile = File(...)):
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    remote_path = f"{user_id}/originFile/{audio.filename}"
    Origin_file_url = (
        f"https://s3musicproject.s3.{settings.region_name}.amazonaws.com/{user_id}/originFile/{audio.filename}"
    )

    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)

    save_data = SeparationTask(user_id=user_id, Origin_file_url=Origin_file_url, artist=artist)
    save_info_to_separationTask(save_data=save_data, settings=settings)

    queue = sqs.get_queue_by_name(QueueName="music.fifo")
    response = queue.send_message(
        MessageGroupId=user_id,
        MessageDeduplicationId=remote_path,
        MessageBody=json.dumps({"path": remote_path, "user_id": user_id, "artist": artist}),
    )

    return SeparateResponse(user_id=user_id, remote_path=remote_path, message_id=response["MessageId"])


@app.post("/download", response_model=DownloadResponse)
def download_separated_audio_files(request: DownloadRequest):
    s3 = get_s3_client(settings)
    try:
        requests = CheckDB(user_id=request.user_id, filename=request.filename, artist=request.artist)
        urls = check_db_for_download(requests)

        if urls[0].startswith("No"):
            return DownloadResponse(vocal=urls[0], instrum=urls[1], status="Processing")
        else:
            return DownloadResponse(vocal=urls[0], instrum=urls[1], status="Completed")

    except Exception as e:
        print(f"error: {e}")


@app.post("/vc_training", response_model=VCTrainingResponse)
def request_vc_training(user_id: str, artist: str, files: list[UploadFile] = File(...)):

    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)

    for file in files:
        file_basename = os.path.basename(file.filename)
        file_name = f"{user_id}/{artist}/TrainingDatasets/{file_basename}"
        s3.upload_fileobj(file.file, "s3musicproject", file_name)

    queue = sqs.get_queue_by_name(QueueName="rvc_training.fifo")
    response = queue.send_message(
        MessageGroupId=user_id,
        MessageDeduplicationId=str(uuid.uuid4()),
        MessageBody=json.dumps({"user_id": user_id, "artist": artist}),
    )

    return VCTrainingResponse(message_id=response["MessageId"])


@app.post("/vc_inference", response_model=VCInferenceResponse)
def request_vc_inference(user_id: str, artist: str, audio: UploadFile = File(...)):

    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    remote_path = f"{user_id}/{artist}/rvc_inference/{audio.filename}"
    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)

    queue = sqs.get_queue_by_name(QueueName="rvc_inference.fifo")
    response = queue.send_message(
        MessageGroupId=user_id,
        MessageDeduplicationId=remote_path,
        MessageBody=json.dumps({"filename": audio.filename, "user_id": user_id, "artist": artist}),
    )

    return VCInferenceResponse(remote_path=remote_path, message_id=response["MessageId"])


@app.get("/", response_class=HTMLResponse)
async def main():
    html_content = """
    <!DOCTYPE html>
    <html>
        <form action="/vc_training" method="post" enctype="multipart/form-data">
                <label for="user_id">UserID:</label>
                <input type="text" id="user_id" name="user_id" required><br><br>
                <label for="artist">artist:</label>
                <input type="text" id="artist" name="artist" required><br><br>
                <label for="files">Select directory:</label>
                <input type="file" id="files" name="files" webkitdirectory directory multiple><br><br>
                <input type="submit" value="Upload">
        </form>
    </html>
    """
    return HTMLResponse(content=html_content)

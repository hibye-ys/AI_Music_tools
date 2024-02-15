import json
import os
import uuid
from typing import Literal, Optional

import boto3
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = FastAPI()


class APIServerSettings(BaseSettings):
    bucket_name: str = "s3musicproject"
    aws_access_key: str
    aws_secret_access_key: str
    region_name: str
    mongodb_uri: str


settings = APIServerSettings()


class DownloadRequest(BaseModel):
    filename: str
    user_id: str


class SeparateResponse(BaseModel):
    remote_path: str
    message_id: str
    user_id: str


class RVCinferenceResponse(BaseModel):
    remote_path: str
    message_id: str


class TrainingResponse(BaseModel):
    message_id: str


class DownloadResponse(BaseModel):
    vocal: Optional[str]
    instrum: Optional[str]
    status: Literal["Processing", "Completed"]


class SaveToMongoDB(BaseModel):
    user_id: str
    file_uri: str


class CheckMongoDB(BaseModel):
    user_id: str
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


def save_info_to_separation_mongodb(
    save_data: SaveToMongoDB, settings: APIServerSettings
):
    mongo = MongoClient(settings.mongodb_uri)
    db = mongo["music_tools"]
    collection = db["separation"]

    document = {"user_id": save_data.user_id, "file_uri": save_data.file_uri}

    result = collection.insert_one(document)

    return result.inserted_id


def check_mongodb_for_download(requests: CheckMongoDB):
    try:
        mongo = MongoClient(settings.mongodb_uri)
        db = mongo["music_tools"]
        collection = db["separation_output"]
        filename = os.path.splitext(requests.filename)[0]
        query_result = collection.find_one(
            {
                "user_id": requests.user_id,
                "vocal_uri": f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/public/separation/{requests.user_id}/{filename}_vocals.wav",
                "instrum_uri": f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/public/separation/{requests.user_id}/{filename}_instrum.wav",
            }
        )

        if query_result is None:
            return "No download URI found", "No download URI found"

        urls = [
            query_result.get("vocal_uri", "No download URI found"),
            query_result.get("instrum_uri", "No download URI found"),
        ]
        print(urls)
        return urls
    except PyMongoError as e:
        print(f"MongoDB error: {e}")
        return "Error querying MongoDB", "Error querying MongoDB"


@app.post("/separate", response_model=SeparateResponse)
def request_to_inference(user_id: str, audio: UploadFile = File(...)):
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    remote_path = f"{user_id}/separation/{audio.filename}"
    file_uri = f"https://s3musicproject.s3.{settings.region_name}.amazonaws.com/{user_id}/sepatation/{audio.filename}"

    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)

    save_data = SaveToMongoDB(user_id=user_id, file_uri=file_uri)
    save_info_to_separation_mongodb(save_data=save_data, settings=settings)

    queue = sqs.get_queue_by_name(QueueName="music.fifo")
    response = queue.send_message(
        MessageGroupId=user_id,
        MessageDeduplicationId=remote_path,
        MessageBody=json.dumps({"path": remote_path, "user_id": user_id}),
    )

    return SeparateResponse(
        user_id=user_id, remote_path=remote_path, message_id=response["MessageId"]
    )


@app.post("/download", response_model=DownloadResponse)
def download_separated_audio_files(request: DownloadRequest):
    s3 = get_s3_client(settings)
    try:
        requests = CheckMongoDB(user_id=request.user_id, filename=request.filename)
        urls = check_mongodb_for_download(requests)

        if urls[0].startswith("No"):
            return DownloadResponse(vocal=urls[0], instrum=urls[1], status="Processing")
        else:
            return DownloadResponse(vocal=urls[0], instrum=urls[1], status="Completed")

    except Exception as e:
        print(f"error: {e}")


@app.post("/rvc_training", response_model=TrainingResponse)
def request_rvc_training(user_id: str = Form(...), files: list[UploadFile] = File(...)):

    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)

    for file in files:
        file_basename = os.path.basename(file.filename)
        file_name = f"{user_id}/TrainingDatasets/{file_basename}"
        s3.upload_fileobj(file.file, "s3musicproject", file_name)

    queue = sqs.get_queue_by_name(QueueName="rvc_training.fifo")
    response = queue.send_message(
        MessageGroupId=user_id,
        MessageDeduplicationId=str(uuid.uuid4()),
        MessageBody=json.dumps({"user_id": user_id}),
    )

    return TrainingResponse(message_id=response["MessageId"])


@app.post("/rvc_inference", response_model=RVCinferenceResponse)
def request_rvc_training(user_id: str, audio: UploadFile = File(...)):

    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    remote_path = f"{user_id}/rvc_inference/{audio.filename}"
    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)

    queue = sqs.get_queue_by_name(QueueName="rvc_inference.fifo")
    response = queue.send_message(
        MessageGroupId=user_id,
        MessageDeduplicationId=remote_path,
        MessageBody=json.dumps({"filename": audio.filename, "user_id": user_id}),
    )

    return RVCinferenceResponse(
        remote_path=remote_path, message_id=response["MessageId"]
    )


@app.get("/", response_class=HTMLResponse)
async def main():
    html_content = """
    <!DOCTYPE html>
    <html>
        <form action="/rvc_training" method="post" enctype="multipart/form-data">
                <label for="user_id">UserID:</label>
                <input type="text" id="user_id" name="user_id" required><br><br>
                <label for="files">Select directory:</label>
                <input type="file" id="files" name="files" webkitdirectory directory multiple><br><br>
                <input type="submit" value="Upload">
        </form>
    </html>
    """
    return HTMLResponse(content=html_content)

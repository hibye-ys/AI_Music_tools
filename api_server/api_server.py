from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic_settings import BaseSettings
import boto3
import requests
from dotenv import load_dotenv
from typing import Optional, Literal
from pydantic import BaseModel, Field
import json
import uuid
import os

load_dotenv()

app = FastAPI()

class APIServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    aws_access_key: str
    aws_secret_access_key: str
    region_name: str

settings = APIServerSettings()

class DownloadRequest(BaseModel):
    file_prefix: str
    
class SeparateResponse(BaseModel):
    remote_path: str
    message_id: str
    
class TrainingResponse(BaseModel):
    message_id: str
    

class DownloadResponse(BaseModel):
    vocal: Optional[str]
    instrum: Optional[str]
    status: Literal["Processing", "Completed"]
    

def get_s3_client(settings: APIServerSettings):
    return boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )

def get_sqs_client(settings: APIServerSettings):
    return boto3.resource(
        'sqs',
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )



@app.post("/separate", response_model=SeparateResponse)
def request_to_inference(user_id: str, audio: UploadFile = File(...)):
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    remote_path = f"{user_id}/{audio.filename}"
    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)


    queue = sqs.get_queue_by_name(QueueName='music.fifo')
    response = queue.send_message(MessageGroupId=user_id,
                                  MessageDeduplicationId=remote_path,
                                  MessageBody=json.dumps({"path": remote_path}))

    return SeparateResponse(
        remote_path=remote_path,
        message_id=response['MessageId']
    )


@app.post('/download')
def check_processed_audio_inS3(request: DownloadRequest):
    s3 = get_s3_client(settings)
    try:
        vocal_path = f'public/{request.file_prefix}_vocals.wav'
        instrum_path = f'public/{request.file_prefix}_instrum.wav'
        s3.head_object(Bucket=settings.bucket_name, Key=vocal_path)
        s3.head_object(Bucket=settings.bucket_name, Key=instrum_path)
    except s3.exceptions.NoSuchKey as e:
        return DownloadResponse(
            vocal=None,
            instrum=None,
            status="Processing"
        )
    return DownloadResponse(
        vocal=f"https://s3musicproject.s3.amazonaws.com/{vocal_path}",
        instrum=f"https://s3musicproject.s3.amazonaws.com/{instrum_path}",
        status="Completed",
    )



@app.post('/rvc_training')
def request_rvc_training(user_id: str = Form(...), files: list[UploadFile] = File(...)):
    
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)


    for file in files:
        file_basename = os.path.basename(file.filename)
        file_name = f"{user_id}/TrainingDatasets/{file_basename}"        
        s3.upload_fileobj(file.file, 's3musicproject', file_name)

    
    queue = sqs.get_queue_by_name(QueueName='rvc_training.fifo')
    response = queue.send_message(MessageGroupId=user_id,
                                  MessageDeduplicationId=str(uuid.uuid4()),
                                  MessageBody=json.dumps({"user_id": user_id}))

    
    return TrainingResponse(message_id=response['MessageId'])


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
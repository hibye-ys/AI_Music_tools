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

load_dotenv()

app = FastAPI()

class APIServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    AWS_ACCESS_KEY: str
    AWS_SECRET_ACCESS_KEY: str
    REGION_NAME: str
    inference_url: str

settings = APIServerSettings()


'''class UploadFileModel(BaseModel):
    file: Optional[UploadFile] = None'''

class DownloadRequest(BaseModel):
    file_prefix: str
    
class SeparateResponse(BaseModel):
    remote_path: str
    #status_code: int
    

class DownloadResponse(BaseModel):
    vocal: Optional[str]
    instrum: Optional[str]
    status: Literal["Processing", "Completed"]
    

def get_s3_client(settings: APIServerSettings):
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REGION_NAME,
    )

def get_sqs_client(settings: APIServerSettings):
    return boto3.resource(
        'sqs',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REGION_NAME,
    )



@app.post("/separate", response_model=SeparateResponse)
def request_to_inference(audio: UploadFile = File(...), user_id: str = Form()):
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    remote_path = f"{user_id}/{audio.filename}"
    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)

    # request to inference_server
    #response = requests.post(settings.inference_url, json={"path": remote_path})

    # to SQS
    queue = sqs.get_queue_by_name(QueueName='music.fifo')
    response = queue.send_message(MessageGroupId=user_id,
                                  MessageDeduplicationId=remote_path,
                                  MessageBody=json.dumps({"path": remote_path}))

    return SeparateResponse(
        remote_path=remote_path,
        #status_code=response.status_code
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
def request_rvc_training(user_id: str, folder: str = Form(...), 
                         files: list[UploadFile] = File(...)):
    
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    
    response = []
    for file in files:
        # S3에 저장될 파일 이름 생성 (UUID를 사용하여 고유한 이름을 생성)
        file_name = f"{folder}/{uuid.uuid4()}_{file.filename}"
        
        # 파일을 S3에 업로드
        s3.upload_fileobj(file.file, 's3musicproject', file_name)

        # 응답 목록에 업로드된 파일 정보 추가
        response.append({"file_name": file.filename, "s3_object_name": file_name})
    
    queue = sqs.get_queue_by_name(QueueName='rvc_training.fifo')
    response = queue.send_message(MessageGroupId=user_id,
                                  #MessageDeduplicationId=remote_path,
                                  MessageBody=json.dumps({"user_id": user_id}))

    
    
    return JSONResponse(status_code=200, content={"uploaded_files": response})


@app.get("/")
async def main():
    return 'hello'

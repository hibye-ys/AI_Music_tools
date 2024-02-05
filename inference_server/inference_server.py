from fastapi import FastAPI, File, UploadFile , HTTPException, BackgroundTasks, Form
from fastapi.responses import HTMLResponse
import requests
import boto3
from botocore.exceptions import NoCredentialsError
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings
import inference
import json
import tempfile
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class InferenceServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    AWS_ACCESS_KEY: str
    AWS_SECRET_ACCESS_KEY: str
    REGION_NAME: str

settings = InferenceServerSettings()

@app.get("/")
async def main():
    return 'O_O'

class InferenceRequest(BaseModel):
    path: str = Form(...)


def get_s3_client(settings: InferenceServerSettings):
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REGION_NAME,
    )

def get_sqs_client(settings: InferenceServerSettings):
    return boto3.client(
        'sqs',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REGION_NAME,
    )

def separate_model(path: str):
    s3 = get_s3_client(settings)
    sqs = get_sqs_client(settings)
    # 임시 디렉토리 설정
    with tempfile.TemporaryDirectory() as temp_dir:
        local_file_path = f"{temp_dir}/origin.wav"
        s3.download_file('s3musicproject', path, local_file_path)

        with open('options.json', 'r') as file:
            options = json.load(file)

        inference.predict_with_model(
            input_audios=local_file_path,
            output_folder=temp_dir,
            options=options
        )
        vocal_local_path = f"{temp_dir}/origin_vocals.wav"
        instrum_local_path = f"{temp_dir}/origin_instrum.wav"
        vocal_remote_path = f"public/{os.path.splitext(path)[0]}_vocals.wav"
        instrum_remote_path = f"public/{os.path.splitext(path)[0]}_instrum.wav"
        s3.upload_file(vocal_local_path, "s3musicproject", vocal_remote_path)
        s3.upload_file(instrum_local_path, "s3musicproject", instrum_remote_path)



@app.on_event('startup')
async def start_message_polling():
    sqs = get_sqs_client(settings)
    queue_url = sqs.get_queue_url(QueueName='music.fifo')['QueueUrl']
    
    async def poll_sqs_messages():
        while True:
            messages = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10, # 한 번에 받을 최대 메시지 수
                WaitTimeSeconds=20 # 롱 폴링 대기 시간
            )
            for message in messages:
                try:
                    message_body = json.loads(message.body)
                    path = message_body['path']
                    separate_model(path)
                    
                    message.delete()
                except Exception as e:
                    print(f'Error processing message: {e}')
            
            await asyncio.sleep(1) #wait for next polling

    asyncio.create_task(poll_sqs_messages())
    
'''###### process_audio #######
@app.post('/inference')
def process_audio(request: InferenceRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(separate_model, request.path)
    return {"status": "ok"}'''

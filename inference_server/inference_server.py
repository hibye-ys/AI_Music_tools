from fastapi import FastAPI, File, UploadFile , HTTPException, BackgroundTasks
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
    path: str = None


def get_s3_client(settings: InferenceServerSettings):
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REGION_NAME,
    )


def separate_model(path: str):
    s3 = get_s3_client(settings)
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


###### process_audio #######
@app.post('/inference')
def process_audio(request: InferenceRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(separate_model, request.path)
    return {"status": "ok"}

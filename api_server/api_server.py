from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from pydantic_settings import BaseSettings
import boto3
import requests
from dotenv import load_dotenv
from typing import Optional, Literal
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI()

class APIServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    AWS_ACCESS_KEY: str
    AWS_SECRET_ACCESS_KEY: str
    REGION_NAME: str
    inference_url: str
    
    class Config:
        env_file = '.env'


settings = APIServerSettings()


class UploadFileModel(BaseModel):
    file: Optional[UploadFile] = None

class DownloadRequest(BaseModel):
    file_prefix: str = Field(..., description="Name of file to check in S3")
    
class SeparateResponse(BaseModel):
    remote_path: str
    status_code: int
    

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


@app.post("/separate", response_model=SeparateResponse)
def request_to_inference(audio: UploadFile = File(...), user_id: str = Form()):
    s3 = get_s3_client(settings)
    remote_path = f"{user_id}/{audio.filename}"
    s3.upload_fileobj(audio.file, settings.bucket_name, remote_path)

    # request to inference_server
    response = requests.post(settings.inference_url, {"path": remote_path})

    return SeparateResponse(
        remote_path=remote_path,
        status_code=response.status_code
    )


@app.get('/download')
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


@app.get("/")
async def main():
    content = """
<body>
<form action="/separate/" enctype="multipart/form-data" method="post">
<input name="file" type="file">
<input type="submit">
</form>
</body>
    """
    return HTMLResponse(content=content)

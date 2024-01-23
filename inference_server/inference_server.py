from fastapi import FastAPI, File, UploadFile , HTTPException
from fastapi.responses import HTMLResponse
import requests
import boto3
from botocore.exceptions import NoCredentialsError
from pathlib import Path
import glob
import inference
import json
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

#aws_api_keys
aws_access_key = os.getenv('AWS_ACCESS_KEY')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region_name = os.getenv("REGION_NAME")

@app.get("/")
async def main():
    return 'O_O'


###### process_audio #######
@app.post('/process_audio/')
def process_audio(filename:str):
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name)

    # 임시 디렉토리 설정
    temp_dir =  tempfile.TemporaryDirectory()
    temp_file_path = os.path.join(temp_dir.name,filename)

    #s3에서 파일 다운로드 후 임시 디렉토리에 저장
    try:
        s3.download_file('s3musicproject', filename, temp_file_path)
        print(f'downloaded {filename}')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    #process 된 파일 임시 디렉토리
    processed_temp_dir = tempfile.TemporaryDirectory()

    #options 에서 input, output 을 빼고 임시 디렉토리 경로를 받을 수 있게 경로를 수정
    with open('options.json', 'r') as file:
        options = json.load(file)

    print('options', options)
    
    
    inference.predict_with_model(input_audios=temp_file_path,
                                output_folder=processed_temp_dir.name,
                                options=options)


    print(os.listdir(processed_temp_dir.name))

    #프로세스된 파일들 s3에 업로드
    for output_file in os.listdir(processed_temp_dir.name):
        s3.upload_file(os.path.join(processed_temp_dir.name, output_file) , 's3musicproject', output_file)

    temp_dir.cleanup()
    processed_temp_dir.cleanup()


    return 'success inference'

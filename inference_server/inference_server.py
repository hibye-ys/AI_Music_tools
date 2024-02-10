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
from typing import TypedDict

load_dotenv()


class InferenceServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    aws_access_key: str
    aws_secret_access_key: str
    region_name: str

settings = InferenceServerSettings()


def get_s3_client(settings: InferenceServerSettings):
    return boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )

def get_sqs_client(settings: InferenceServerSettings):
    return boto3.client(
        'sqs',
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
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


class InferenceMessage(TypedDict):
    path: str


def poll_sqs_messages():
    sqs = get_sqs_client(settings)
    queue_url = sqs.get_queue_url(QueueName='music.fifo')['QueueUrl']
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=1000
        )
        messages = response.get('Messages', [])
        for message in messages:
            try:
                message_body = json.loads(message['Body'])
                path = message_body['path']
                separate_model(path)
                
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])
            except Exception as e:
                print(f'Error processing message: {e}')

if __name__ == "__main__":
    asyncio.run(poll_sqs_messages())

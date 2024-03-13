import asyncio
import json
import os
import tempfile

import boto3
import inference
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pymongo import MongoClient
from pymongo import ReturnDocument

load_dotenv()


class InferenceServerSettings(BaseSettings):
    bucket_name: str = "s3musicproject"
    aws_access_key: str = os.environ.get("AWS_ACCESS_KEY")
    aws_secret_access_key: str = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region_name: str = os.environ.get("REGION_NAME")
    mongodb_uri: str = os.environ.get("MONGODB_URI")


class FetchToDB(BaseModel):
    user_id: str
    artist: str
    vocal_url: str
    instrum_url: str


settings = InferenceServerSettings()


def get_s3_client(settings: InferenceServerSettings):
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )


def get_sqs_client(settings: InferenceServerSettings):
    return boto3.client(
        "sqs",
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )


def fetch_to_db(save_data: FetchToDB, settings: InferenceServerSettings):
    mongo = MongoClient(settings.mongodb_uri)
    db = mongo["music_tools"]
    collection = db["separation"]

    collection.find_one_and_update(
        {"user_id": save_data.user_id, "artist": save_data.artist},
        {"$set": {"vocal_url": save_data.vocal_url, "instrum_url": save_data.instrum_url}},
        return_document=ReturnDocument.AFTER,
    )
    return print("db update completed")


def separate_model(path: str, user_id: str, artist: str):
    s3 = get_s3_client(settings)
    with tempfile.TemporaryDirectory() as temp_dir:
        local_file_path = f"{temp_dir}/origin.wav"
        s3.download_file("s3musicproject", path, local_file_path)

        with open("options.json", "r") as file:
            options = json.load(file)

        inference.predict_with_model(input_audios=local_file_path, output_folder=temp_dir, options=options)
        vocal_local_path = f"{temp_dir}/origin_vocals.wav"
        instrum_local_path = f"{temp_dir}/origin_instrum.wav"
        vocal_remote_path = f"public/{user_id}/vocal/{os.path.basename(os.path.splitext(path)[0])}_vocals.wav"
        instrum_remote_path = f"public/{user_id}/instrument/{os.path.basename(os.path.splitext(path)[0])}_instrum.wav"
        s3.upload_file(vocal_local_path, settings.bucket_name, vocal_remote_path)
        s3.upload_file(instrum_local_path, settings.bucket_name, instrum_remote_path)

        vocal_url = f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/{vocal_remote_path}"
        instrum_url = f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/{instrum_remote_path}"

        save_data = FetchToDB(user_id=user_id, vocal_url=vocal_url, instrum_url=instrum_url, artist=artist)
        fetch_to_db(save_data=save_data, settings=settings)


async def poll_sqs_messages():
    sqs = get_sqs_client(settings)
    queue_url = sqs.get_queue_url(QueueName="music.fifo")["QueueUrl"]
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            VisibilityTimeout=200,
        )
        messages = response.get("Messages", [])
        print(messages)
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                path = message_body["path"]
                user_id = message_body["user_id"]
                artist = message_body["artist"]
                separate_model(path, user_id, artist)

                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
            except Exception as e:
                print(f"Error processing message: {e}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(poll_sqs_messages())

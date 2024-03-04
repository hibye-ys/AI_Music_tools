import asyncio
import glob
import json
import os
import tempfile

import boto3
from dotenv import load_dotenv
from main import run_infer_script
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


settings = InferenceServerSettings()


class rvcInferenceRequest(BaseModel):
    user_id: str
    filename: str
    artist: str


class FetchToDB(BaseModel):
    user_id: str
    artist: str
    vc_vocal_url: str


def fetch_to_db(save_data: FetchToDB, settings: InferenceServerSettings):
    mongo = MongoClient(settings.mongodb_uri)
    db = mongo["music_tools"]
    collection = db["separation"]

    collection.find_one_and_update(
        {"user_id": save_data.user_id, "artist": save_data.artist},
        {"$set": {"vc_vocal_url": save_data.vc_vocal_url}},
        return_document=ReturnDocument.AFTER,
    )
    return print("db update completed")


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


def rvc_inference_model(request: rvcInferenceRequest):
    s3 = get_s3_client(settings)

    with tempfile.TemporaryDirectory() as temp_dir:
        logs_path = os.path.join(temp_dir, f"logs/{request.user_id}")
        os.makedirs(logs_path, exist_ok=True)
        file_path = os.path.join(temp_dir, "inference")
        os.makedirs(file_path, exist_ok=True)

        for item in s3.list_objects_v2(
            Bucket="s3musicproject", Prefix=f"{request.user_id}/{request.artist}/TrainingFiles"
        )["Contents"][1:]:
            file_name = os.path.basename(item["Key"])
            s3.download_file("s3musicproject", item["Key"], os.path.join(logs_path, file_name))
        print("TrainingFiles download complete")

        s3.download_file(
            "s3musicproject",
            f"{request.user_id}/{request.artist}/rvc_inference/{request.filename}",
            os.path.join(file_path, request.filename),
        )
        print("File for inference download complete")

        pth_file = glob.glob(os.path.join(logs_path, "*e.pth"))[0]
        print("pth_file:", pth_file)
        index_path = glob.glob(os.path.join(logs_path, "trained_*.index"))[0]
        print("index_path:", index_path)
        input_path = os.path.join(file_path, request.filename)
        print("input_path:", input_path)
        output_path = os.path.join(file_path, f"{os.path.splitext(request.filename)[0]}_output.wav")
        output_remote_path = f"public/{request.user_id}/vc_vocal/{os.path.splitext(request.filename)[0]}_output.wav"
        f0method = "rmvpe"
        f0up_key = 0
        filter_radius = 0
        index_rate = 0.0
        hop_length = 128
        split_audio = False
        f0autotune = False

        run_infer_script(
            f0up_key=f0up_key,
            filter_radius=filter_radius,
            index_rate=index_rate,
            hop_length=hop_length,
            f0method=f0method,
            input_path=input_path,
            output_path=output_path,
            pth_file=pth_file,
            index_path=index_path,
            split_audio=split_audio,
            f0autotune=f0autotune,
        )
        print("-" * 100)

        s3.upload_file(output_path, "s3musicproject", output_remote_path)
        print("Upload completed")

        vc_vocal_url = f"https://{settings.bucket_name}.s3.{settings.region_name}.amazonaws.com/{output_remote_path}"

        # save_data = FetchToDB(user_id=request.user_id, vc_vocal_url=vc_vocal_url, artist=request.artist)
        # fetch_to_db(save_data=save_data, settings=settings)


async def poll_sqs_messages():
    sqs = get_sqs_client(settings)
    queue_url = sqs.get_queue_url(QueueName="rvc_inference.fifo")["QueueUrl"]
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            VisibilityTimeout=100,
        )

        messages = response.get("Messages", [])
        print(messages)
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                user_id = message_body["user_id"]
                filename = message_body["filename"]
                artist = message_body["artist"]
                request_model = rvcInferenceRequest(user_id=user_id, filename=filename, artist=artist)
                rvc_inference_model(request_model)

                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
            except Exception as e:
                print(f"Error processing message: {e}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(poll_sqs_messages())

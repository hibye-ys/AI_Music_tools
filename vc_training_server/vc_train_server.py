import asyncio
import glob
import json
import os
import tempfile
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv
from main import run_extract_script
from main import run_preprocess_script
from main import run_train_script
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pymongo import MongoClient
from pymongo import ReturnDocument

load_dotenv()


class TrainingServerSettings(BaseSettings):
    bucket_name: str = "s3musicproject"
    aws_access_key: str
    aws_secret_access_key: str
    region_name: str
    mongodb_uri: str


settings = TrainingServerSettings()


class vcTrainRequest(BaseModel):
    user_id: str
    artist: str


def get_s3_client(settings: TrainingServerSettings):
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )


def get_sqs_client(settings: TrainingServerSettings):
    return boto3.client(
        "sqs",
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.region_name,
    )


def fetch_to_db(user_id: str, artist: str):
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo["music_tools"]
    collection = db["separation"]

    collection.find_one_and_update(
        {"user_id": user_id, "artist": artist},
        {"$set": {"trained": True}},
        return_document=ReturnDocument.AFTER,
    )
    return print("db update completed")


def vc_train_model(request: vcTrainRequest):
    s3 = get_s3_client(settings)

    with tempfile.TemporaryDirectory() as temp_dir:
        datasets = os.path.join(temp_dir, "dataset")
        os.makedirs(datasets, exist_ok=True)
        for item in s3.list_objects_v2(
            Bucket="s3musicproject", Prefix=f"{request.user_id}/{request.artist}/TrainingDatasets"
        )["Contents"][1:]:
            file_name = os.path.basename(item["Key"])
            s3.download_file("s3musicproject", item["Key"], os.path.join(datasets, file_name))
            print(f'downloaded:{item["Key"]}')
        print("download complete")

        dataset_path = datasets
        logs_path = os.path.join(temp_dir, "logs")
        os.makedirs(logs_path, exist_ok=True)
        model_name = f"{request.user_id}/{request.artist}"
        sampling_rate = "48000"
        rvc_version = "v2"
        f0method = "rmvpe"
        hop_length = 128
        save_every_epoch = 10
        save_only_latest = True
        save_every_weights = False
        total_epoch = 1000
        batch_size = 16
        gpu = 0
        pitch_guidance = True
        pretrained = True
        custom_pretrained = False
        g_pretrained_path = None
        d_pretrained_path = None

        run_preprocess_script(
            logs_path=str(logs_path),
            model_name=str(model_name),
            dataset_path=dataset_path,
            sampling_rate=str(sampling_rate),
        )

        run_extract_script(
            logs_path=logs_path,
            model_name=model_name,
            rvc_version=rvc_version,
            f0method=f0method,
            hop_length=hop_length,
            sampling_rate=sampling_rate,
        )

        run_train_script(
            model_name=model_name,
            rvc_version=rvc_version,
            save_every_epoch=save_every_epoch,
            save_only_latest=save_only_latest,
            save_every_weights=save_every_weights,
            total_epoch=total_epoch,
            sampling_rate=sampling_rate,
            batch_size=batch_size,
            gpu=gpu,
            pitch_guidance=pitch_guidance,
            pretrained=pretrained,
            custom_pretrained=custom_pretrained,
            logs_path=logs_path,
            g_pretrained_path=g_pretrained_path,
            d_pretrained_path=d_pretrained_path,
        )

        with open("lowestValue.txt", "r") as f:
            lowestValue = str(f.read().strip())

        g_path = glob.glob(os.path.join(logs_path, model_name, "G_*.pth"))[-1]
        d_path = glob.glob(os.path.join(logs_path, model_name, "D_*.pth"))[-1]
        index_path = glob.glob(os.path.join(logs_path, model_name, "trained_*.index"))[-1]
        pths_path = glob.glob(os.path.join(logs_path, request.user_id, "*e.pth"))
        for path in pths_path:
            if path.split("_")[1].split("e")[0] == lowestValue:
                pth_path = path
            else:
                pth_path = sorted(pths_path)[-1]

        s3.upload_file(g_path, "s3musicproject", f"{model_name}/TrainingFiles/{os.path.basename(g_path)}")
        s3.upload_file(d_path, "s3musicproject", f"{model_name}/TrainingFiles/{os.path.basename(d_path)}")
        s3.upload_file(index_path, "s3musicproject", f"{model_name}/TrainingFiles/{os.path.basename(index_path)}")
        s3.upload_file(pth_path, "s3musicproject", f"{model_name}/TrainingFiles/{os.path.basename(pth_path)}")

        print("TraingFiles Upload completed")
        # fetch_to_db(request.user_id, request.artist)


def poll_sqs_messages():
    sqs = get_sqs_client(settings)
    queue_url = sqs.get_queue_url(QueueName="rvc_training.fifo")["QueueUrl"]
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5, VisibilityTimeout=1000
        )

        messages = response.get("Messages", [])
        print(messages)
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                user_id = message_body["user_id"]
                artist = message_body["artist"]
                request = vcTrainRequest(user_id=user_id, artist=artist)
                vc_train_model(request)

                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
            except Exception as e:
                print(f"Error processing message: {e}")


if __name__ == "__main__":
    asyncio.run(poll_sqs_messages())

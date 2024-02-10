import requests
import boto3
from botocore.exceptions import NoCredentialsError
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings
import json
import tempfile
import os
import asyncio
from dotenv import load_dotenv
import glob

from main import (
    run_infer_script,
    run_batch_infer_script,
    run_tts_script,
    run_preprocess_script,
    run_extract_script,
    run_train_script,
    run_index_script,
    run_model_information_script,
    run_model_fusion_script,
    run_tensorboard_script,
    run_download_script,
)

load_dotenv()


class InferenceServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    aws_access_key: str
    aws_secret_access_key: str
    region_name: str

settings = InferenceServerSettings()


class rvcTrainRequest(BaseModel):
    user_id: str 


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
    
    
def rvc_train_model(user_id: rvcTrainRequest): 
    s3 = get_s3_client(settings)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for item in s3.list_objects_v2(Bucket='s3musicproject', Prefix=f'{user_id}/TrainingDatasets')['Contents'][1:]:
            file_name = os.path.basename(item['Key'])
            datasets = os.path.join(temp_dir, 'dataset')
            os.makedirs(datasets, exist_ok=True)
            s3.download_file('s3musicproject', item['Key'], os.path.join(datasets, file_name))
        print('download complete')
        
        
        dataset_path = datasets
        logs_path = os.path.join(temp_dir, 'logs')
        os.makedirs(logs_path, exist_ok=True)
        model_name = user_id #@param {type:"string"}
        sample_rate = "48k" #@param ["32k", "40k", "48k"] {allow-input: false}
        sampling_rate = '48000'
        rvc_version = "v2" #@param ["v2", "v1"] {allow-input: false}
        f0method = "rmvpe" #@param ["pm", "dio", "crepe", "crepe-tiny", "harvest", "rmvpe"] {allow-input: false}
        hop_length = 128 #@param {type:"slider", min:1, max:512, step:0}
        sr = int(sample_rate.rstrip('k'))*1000
        save_every_epoch = 5 #@param {type:"slider", min:1, max:100, step:0}
        save_only_latest = True #@param{type:"boolean"}
        save_every_weights = True #@param{type:"boolean"}
        total_epoch = 5 #@param {type:"slider", min:1, max:10000, step:0}
        batch_size = 15 #@param {type:"slider", min:1, max:25, step:0}
        gpu = 0 # @param {type:"number"}
        pitch_guidance = True #@param{type:"boolean"}
        pretrained = False #@param{type:"boolean"}
        custom_pretrained = False #@param{type:"boolean"}
        #g_pretrained_path = f'/home/lee/workplace/rvc_server/logs/{model_name}' # @param {type:"string"}
        #d_pretrained_path = f'/home/lee/workplace/rvc_server/logs/{model_name}'

        run_preprocess_script(logs_path=logs_path, 
                              model_name=model_name, 
                              dataset_path=dataset_path, 
                              sampling_rate=sr)
      
        run_extract_script(logs_path=logs_path, 
                           model_name=model_name, 
                           rvc_version=rvc_version, 
                           f0method=f0method, 
                           hop_length=hop_length, 
                           sampling_rate=sr)
        
        run_train_script(model_name=model_name,
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
                g_pretrained_path=None,
                d_pretrained_path=None,
                )
        

    
        pth_paths = glob.glob(os.path.join(logs_path, user_id, '*.pth'))
        g_path = pth_paths[0]
        d_path = pth_paths[1]
        
        pth_path = glob.glob(os.path.join(logs_path, '*e.pth'))[0]
        index_path = glob.glob(os.path.join(logs_path, user_id, 'trained_*.index'))[0]
        
        
        s3.upload_file(g_path, 's3musicproject', f'{user_id}/TrainingFiles/{os.path.basename(g_path)}')
        s3.upload_file(d_path, 's3musicproject', f'{user_id}/TrainingFiles/{os.path.basename(d_path)}')
        s3.upload_file(pth_path, 's3musicproject', f'{user_id}/TrainingFiles/{os.path.basename(pth_path)}')
        s3.upload_file(index_path, 's3musicproject', f'{user_id}/TrainingFiles/{os.path.basename(index_path)}')
        

async def poll_sqs_messages():
    sqs = get_sqs_client(settings)
    queue_url = sqs.get_queue_url(QueueName='rvc_training.fifo')['QueueUrl']
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
            VisibilityTimeout=1000
        )

        messages = response.get('Messages', [])
        print(messages)
        for message in messages:
            try:
                message_body = json.loads(message['Body'])
                user_id = message_body['user_id']
                rvc_train_model(user_id)
                
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])
            except Exception as e:
                print(f'Error processing message: {e}')
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(poll_sqs_messages())
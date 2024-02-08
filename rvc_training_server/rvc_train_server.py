from fastapi import FastAPI, File, UploadFile , HTTPException, BackgroundTasks, Form
from fastapi.responses import HTMLResponse
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

app = FastAPI()


@app.get('/')
async def main():
    return 'Welcome to RVC_Train_Server'


class InferenceServerSettings(BaseSettings):
    bucket_name: str = 's3musicproject'
    AWS_ACCESS_KEY: str
    AWS_SECRET_ACCESS_KEY: str
    REGION_NAME: str

settings = InferenceServerSettings()


class rvcTrainRequest(BaseModel):
    user_id: str 


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
    
    
def rvc_train_model(user_id: str): 
    s3 = get_s3_client(settings)
    
    with tempfile.TemporaryDirectory() as temp_dir:
    
        #download_dataset
        for item in s3.list_objects(Bucket='s3musicproject', Prefix=f'{user_id}/TrainingDatasets/wavs')['Contents']:
        
            file_name = os.path.basename(item['Key'])
            datasets = os.path.join(temp_dir, 'dataset')
            os.makedirs(datasets, exist_ok=True)
            s3.download_file('s3musicproject', item['Key'], os.path.join(datasets, file_name))
        
        
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
        save_only_latest = False #@param{type:"boolean"}
        save_every_weights = False #@param{type:"boolean"}
        total_epoch = 10 #@param {type:"slider", min:1, max:10000, step:0}
        batch_size = 15 #@param {type:"slider", min:1, max:25, step:0}
        gpu = 0 # @param {type:"number"}
        pitch_guidance = True #@param{type:"boolean"}
        pretrained = False #@param{type:"boolean"}
        custom_pretrained = False #@param{type:"boolean"}
        #g_pretrained_path = f'/home/lee/workplace/rvc_server/logs/{model_name}' # @param {type:"string"}
        #d_pretrained_path = f'/home/lee/workplace/rvc_server/logs/{model_name}'

        #preprocessing
        run_preprocess_script(logs_path=logs_path, 
                              model_name=model_name, 
                              dataset_path=dataset_path, 
                              sampling_rate=sr)
        #extract_f0
        run_extract_script(logs_path=logs_path, 
                           model_name=model_name, 
                           rvc_version=rvc_version, 
                           f0method=f0method, 
                           hop_length=hop_length, 
                           sampling_rate=sr)
        #train
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
        
        #pth_path
        pth_files = glob.glob(logs_path + "*.pth")
        if pth_files:
            pth_path = pth_files[0]
        else:
            print("No .pth files found")
            
        #index_path 
        index_files = glob.glob(logs_path + user_id + "*.index")
        if index_files:
            index_path = index_files[1]
        else:
            print("No .pth files found")
        
        s3.upload_file(pth_path, 's3musicproject', f'{user_id}/TrainingFiles')
        s3.upload_file(index_path, 's3musicproject', f'{user_id}/TrainingFiles')
        
        
@app.post('/rvc_train_server')
def rvc_training(request: rvcTrainRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(rvc_train_model, request.user_id)
    return {"status": "ok"}
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
import shutil
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import requests
import tempfile
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

#aws_api_keys
aws_access_key = os.getenv('AWS_ACCESS_KEY')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region_name = os.getenv("REGION_NAME")


@app.post("/uploadfile/")
async def request_to_inference(audio: UploadFile = File(...)):
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name)
    

    
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await audio.read())
        file_path = temp_file.name
    

    s3.upload_file(file_path, 's3musicproject', audio.filename)

    ##request to inference_server
    inference_url = ''
    response = requests.post(inference_url, audio.filename) #S3 FILE PATH, NOT FILENAME

    os.remove(file_path)

    return {'upload success': audio.filename, 'reuest to inference': response.status_code}


@app.get('/check_s3/')
def check_processed_audio_inS3(filename : str):
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name)

    #check file exist 
    filename = filename.split('.')[0]
    print(filename)
    
    try:
        filenames = [f'{filename}_vocals.wav', f'{filename}_instrum.wav']
        print(filenames)
        download_uris = []
        for file in filenames:
            s3.head_object(Bucket='s3musicproject', Key=file)
            download_uri = f"https://s3musicproject.s3.amazonaws.com/{file}"
            download_uris.append(download_uri)

        return download_uris
    
    except s3.exceptions.NoSuchKey as e:
        return "processing..."
    
    except NoCredentialsError:
        return 'Wrong AWS auth Information'


@app.get("/")
async def main():
    content = """
<body>
<form action="/uploadfile/" enctype="multipart/form-data" method="post">
<input name="file" type="file">
<input type="submit">
</form>
</body>
    """
    return HTMLResponse(content=content)

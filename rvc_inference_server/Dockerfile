
FROM python:3.10


WORKDIR /usr/src/app


COPY ./requirements.txt ./requirements.txt


RUN pip install -r requirements.txt

RUN sudo apt update && sudo apt install ffmpeg

COPY . .


ENTRYPOINT [ "python", "rvc_train_server.py" ]

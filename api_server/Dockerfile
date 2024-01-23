# Python 이미지 사용
FROM python:3.10

# 작업 디렉토리 설정
WORKDIR /usr/src/app

# 현재 디렉토리의 내용을 이미지로 복사
COPY . .

# 필요한 라이브러리 설치
RUN pip install --no-cache-dir fastapi[all] uvicorn boto3 python-dotenv requests


# 포트 8000 노출
EXPOSE 8000

# FastAPI 애플리케이션 실행
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]

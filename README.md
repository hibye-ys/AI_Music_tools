# AI_Music_tools

### 🎹 Introduction

사용자가 원하는 노래를 처리한 후 노래를 부를 수 있는 기능을 제공합니다.
그리고 사용자의 데이터를 학습해서 Ai_song_Cover, Pitch Extraction 기능을 제공합니다.

이 프로젝트는 크게 4가지 요소로 나뉘어 집니다

- 노래 제목, 가수명을 입력하면 유튜브에서 노래를 자동으로 다운로드 해주는 기능을 제공합니다.
- Vocal 과 MR을 분리하는 기능을 제공합니다 (separate_server)
- 녹음한 데이터를 학습해 AI_Song_Cover 기능을 제공합니다 (rvc_training_server, rvc_inference_server)
- 자신이 녹음한 소리와 올바른 소리를 비교해 pitch guide 기능을 제공합니다

---
### ⚒️ Architecture
<img width="3242" alt="AI_Music_Tools" src="https://github.com/hibye-ys/AI_Music_tools/assets/57881969/9e241a2f-2548-4dd6-acb0-4d35ff6acc6f">

---------------------
### 🔑 Requirements

- AWS 계정이 필요합니다 (AWS의 api Key를 환경변수에 지정)
  
- Voice Conversion Training 시 10G 이상의 VRAM이 필요합니다
  

---

### 🧲 installation

#### Download the latest version
```
git clonehttps://github.com/hibye-ys/AI_Music_tools.git
```

#### AWS API Key & DB Setting
- Download direnv
  - see https://github.com/direnv/direnv/blob/master/docs/installation.md
- Setup
  - see https://github.com/direnv/direnv/blob/master/docs/hook.md

```python
# make .envrc file and export your API Key
AWS_ACCESS_KEY = ''
AWS_SECRET_ACCESS_KEY = ''
REGION_NAME = ''

#implementation
$ direnv allow

```

- set docker containers
  

```python
docker-compose up
```

---


### ⏳ Project Progress

- download songs (추가 예정)
  
  - Coding
  - API, Queue, DB 시스템
- Separation
  
  - ~~AI_Model Refactoring~~
  - ~~API, Queue, DB 시스템~~
- Voice Conversion
  
  - ~~AI_Model Refactoring~~
  - ~~API, Queue, DB 시스템~~
  - Combine Voice Conversion and Instrument
- Pitch Estimation (추가예정)
  - AI_Model Refactoring 
  - API, Queue, DB 시스템
    
- 인터페이스 설계 및 프론트앤드 (진행중)

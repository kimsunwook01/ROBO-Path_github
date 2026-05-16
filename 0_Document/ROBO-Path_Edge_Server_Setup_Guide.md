# ROBO-Path 에지 서버 구축 가이드 (Raspberry Pi 5)

## 1. 개요 및 목적
본 문서는 ROBO-Path 프로젝트에서 라즈베리파이 5 (8GB RAM, 1TB SSD)를 **관제 대시보드 호스팅(웹 서버)** 및 **대용량 파일 스토리지(API 서버)**로 활용하기 위한 인프라 구축 및 자동화 파이프라인(CI/CD) 설정 절차를 구체화한 문서입니다.

**목표 환경:**
- **OS:** Raspberry Pi OS (SSD에 설치되어 부팅됨, PCIe Gen3 활성화)
- **네트워크:** 유선랜 연결 (고정 IP 확보)
- **코드 배포:** GitHub Actions (Self-Hosted Runner) 기반 자동 배포
- **무중단 운영:** Systemd 기반 백그라운드 서비스 및 Nginx 리버스 프록시 라우팅

---

## 2. Phase 1: CI/CD 자동 배포 파이프라인 구축 (GitHub Actions)
에지 서버에 직접 SSH로 접속해 코드를 수정하거나 `git pull`을 수행하는 번거로움을 없애기 위해, GitHub 푸시 이벤트에 반응하여 코드를 자동 동기화하고 서버를 재시작하는 파이프라인을 1순위로 구축합니다.

### 2.1 Self-Hosted Runner 설치
1. 라즈베리파이에 SSH로 접속합니다.
2. GitHub Repository의 **Settings > Actions > Runners** 메뉴에서 'New self-hosted runner'를 생성합니다.
3. 아키텍처(Linux, ARM64)에 맞는 다운로드 및 설정 명령어를 파이 터미널에서 순차적으로 실행합니다.
4. `./svc.sh install` 및 `./svc.sh start` 명령어를 통해 러너를 백그라운드 서비스로 등록하여 파이 부팅 시 항상 깃허브의 명령을 수신 대기하도록 만듭니다.

### 2.2 배포 워크플로우 (.github/workflows/deploy-to-pi.yml) 작성
- `main` 브랜치에 코드가 푸시되면 트리거되도록 설정합니다.
- 워크플로우는 라즈베리파이에 설치된 러너 환경(`runs-on: self-hosted`)에서 실행됩니다.
- **실행 스크립트 로직:**
  1. 최신 코드 `git pull`
  2. 파이썬 가상환경 활성화 및 `pip install -r requirements.txt` 실행
  3. `sudo systemctl restart robo-path-api` (스토리지 서버 재시작)
  4. `sudo systemctl restart robo-path-web` (웹 서버 재시작)

---

## 3. Phase 2: 스토리지 디렉토리 구성 및 환경 세팅
SSD의 공간을 체계적으로 사용하고 프로젝트의 독립된 실행 환경을 구성합니다.

### 3.1 1TB SSD 디렉토리 및 권한 설정
```bash
sudo mkdir -p /mnt/ssd/robo-path-data/pcd
sudo mkdir -p /mnt/ssd/robo-path-data/logs
# 앱 구동 유저(예: pi)에게 읽기/쓰기 권한 부여
sudo chown -R $USER:$USER /mnt/ssd/robo-path-data
```

### 3.2 파이썬 가상환경 구성
라즈베리파이 환경에 Python 가상환경(`venv`)을 세팅하여 글로벌 패키지 오염을 방지합니다.
```bash
python3 -m venv ~/ROBO-Path_project/venv
source ~/ROBO-Path_project/venv/bin/activate
pip install fastapi uvicorn streamlit python-multipart supabase websocket-client google-generativeai
```

---

## 4. Phase 3: 스토리지 서버 API (FastAPI) 구현
워크스테이션(NVIDIA Isaac Sim)에서 생성된 엄청난 용량의 PCD 데이터와 CSV 로그를 수신하기 위한 백엔드 엔드포인트를 구축합니다.

**파일 위치:** `src/infrastructure/storage/api.py` (신규 생성)
- `POST /upload/pcd`: 멀티파트 폼 데이터로 3D 맵(`.pcd`) 파일을 받아 `/mnt/ssd/robo-path-data/pcd/`에 저장하고 다운로드 URL을 반환.
- `POST /upload/log`: 주행 로그(`.csv`)를 받아 `/mnt/ssd/robo-path-data/logs/`에 저장하고 반환.
- `GET /files/{file_path}`: 저장된 정적 파일을 외부에 제공하기 위한 정적 라우팅 설정.

---

## 5. Phase 4: 무중단 백그라운드 서비스 (Systemd & Nginx)
파이썬 스크립트 실행이 터미널 종료 후에도 멈추지 않도록 데몬 서비스로 등록합니다.

### 5.1 Systemd 서비스 등록
- **API 서버 데몬 (`/etc/systemd/system/robo-path-api.service`):**
  - 가상환경의 `uvicorn`을 호출하여 `api.py`를 8000번 포트에서 구동.
- **Web 서버 데몬 (`/etc/systemd/system/robo-path-web.service`):**
  - 가상환경의 `streamlit`을 호출하여 `dashboard/app.py`를 8501번 포트에서 구동.

### 5.2 Nginx 리버스 프록시 설정
단일 80번(HTTP) 포트로 들어오는 트래픽을 URL 경로에 따라 안전하게 분배합니다.
```nginx
server {
    listen 80;
    server_name _;

    # 기본 경로 (/) -> Streamlit 대시보드 (8501)
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        # WebSocket 지원 설정 (Streamlit 구동 필수)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # /api 경로 -> FastAPI 스토리지 서버 (8000)
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
    }
}
```

---

## 6. Phase 5: (선택/후순위) SMB 공유 네트워크 드라이브 설정
기본적인 서버 가동 및 통신 시스템이 모두 검증된 이후, Windows 및 Mac 워크스테이션에서 마우스 클릭만으로 1TB SSD 파일에 직접 접근할 수 있도록 Samba 프로토콜을 설정합니다.
- `sudo apt install samba`
- `/etc/samba/smb.conf` 에 `/mnt/ssd/robo-path-data` 경로 마운트 추가 및 사용자 인증 설정.

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
에지 서버에 직접 SSH로 접속해 수동으로 코드를 갱신하는 번거로움을 없애기 위해, GitHub 푸시 이벤트에 반응하여 코드를 자동 동기화하고 서버를 재시작하는 파이프라인을 가장 먼저 구축합니다.

### 2.1 라즈베리파이 최초 1회 환경 구성 (SSH 직접 접속)

Runner를 설치하기 전에 파이에 기반 환경을 먼저 구성합니다.

**① GitHub SSH 키 등록 (git pull 인증)**
```bash
# SSH 키 생성 (passphrase는 Enter로 비워둘 것 - 자동화 필수)
ssh-keygen -t ed25519 -C "robo-path-pi" -f ~/.ssh/github_pi

# 공개 키 출력 → GitHub > (프로필) Settings > SSH and GPG keys > New SSH key 에 등록
cat ~/.ssh/github_pi.pub

# SSH 설정 파일 작성 (>> 대신 > 로 명시적 생성)
cat > ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_pi
EOF
chmod 600 ~/.ssh/config

# 연결 테스트 (Hi kimsunwook01! 메시지가 나오면 성공)
ssh -T git@github.com
```

**② 리포지토리 클론 및 가상환경 구성**
```bash
# 프로젝트 클론
git clone git@github.com:kimsunwook01/ROBO-Path_github.git ~/ROBO-Path_project
cd ~/ROBO-Path_project

# Python 가상환경 생성 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**③ Nginx 설치 (CI/CD 설정 파일 복사를 위해 사전 필수)**

Raspberry Pi OS에는 Nginx가 기본 설치되어 있지 않습니다. 워크플로우의 config 복사가 실패하지 않도록 반드시 먼저 설치합니다.
```bash
sudo apt update
sudo apt install nginx -y
nginx -v  # 설치 확인
```

**④ Runner용 sudo 권한 설정 (비밀번호 없이 서비스 제어)**

CI/CD 워크플로우가 `systemctl`, `nginx`, `cp` 명령어를 자동으로 실행하려면 passwordless sudo가 필요합니다.
```bash
# sudoers 파일에 허용 명령어 추가
sudo visudo -f /etc/sudoers.d/robo-path-runner
```
아래 내용을 입력 후 저장 (`rpi5` 부분을 실제 파이 계정명으로 변경):
```
rpi5 ALL=(ALL) NOPASSWD: /bin/systemctl, /usr/bin/nginx, /bin/cp, /usr/bin/ln
```

### 2.2 Self-Hosted Runner 설치
1. 라즈베리파이에 SSH로 접속합니다.
2. GitHub Repository의 **Settings > Actions > Runners** 메뉴에서 **`New self-hosted runner`** 버튼을 클릭합니다.
3. OS는 **`Linux`**, Architecture는 **`ARM64`** 를 선택합니다.
4. 화면에 출력되는 `Download` 및 `Configure` 명령어 블록을 파이 터미널에 순서대로 복사하여 실행합니다.
5. Runner를 백그라운드 서비스로 등록하여 파이 부팅 시 자동으로 GitHub를 감청하도록 만듭니다:
```bash
# actions-runner 디렉토리 안에서 실행
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2.3 배포 워크플로우 (`.github/workflows/deploy-to-pi.yml`) ✅ 완료

`main` 브랜치 푸시 시 Self-Hosted Runner가 자동으로 실행하는 워크플로우입니다. 이미 리포지토리에 작성되어 있습니다.

**실행 순서:**
1. `git pull origin main` — 최신 코드 동기화
2. GitHub Secrets에서 `.env` 파일 생성 (API 키 자동 주입)
3. `pip install -r requirements.txt` — 패키지 업데이트
4. `config/` 파일을 시스템 경로에 복사 및 `systemctl daemon-reload`
5. `robo-path-api`, `robo-path-web` 서비스 재시작
6. Nginx 설정 검증 및 리로드
7. 배포 결과 상태 검증 (실패 시 워크플로우 오류로 표시)
### 2.4 ⚠️ 실제 구축 시 발생한 문제 및 해결 방법 (Troubleshooting Record)

> 2026-05-18 실제 라즈베리파이(계정: `rpi5`) 구축 과정에서 발생한 시행착오 기록입니다.  
> 동일 환경 재구성 시 참고하여 동일한 실수를 반복하지 않도록 합니다.

---

#### 문제 1: SSH 키 등록 후에도 `Permission denied (publickey)` 오류

**증상:**
```
git@github.com: Permission denied (publickey).
```

**원인:** `~/.ssh/config` 파일이 생성되지 않아 SSH가 `github_pi` 키를 시도하지 않고 기본 키(`id_rsa` 등)만 시도했습니다. 또한 `cat >> ~/.ssh/config` 명령어는 파일이 없을 때 새로 생성되지 않는 경우가 있었습니다.

**해결책:** `>>` 대신 `>`(overwrite)를 사용하여 config 파일을 명시적으로 생성하고 권한을 설정합니다.
```bash
# >>  대신 > 를 사용하여 확실하게 생성
cat > ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_pi
EOF
chmod 600 ~/.ssh/config

# 키를 직접 지정하여 GitHub 인증 테스트 (config와 무관하게 확인)
ssh -i ~/.ssh/github_pi -T git@github.com
```

---

#### 문제 2: SSH key passphrase 입력 프롬프트

**증상:**
```
Enter passphrase for "/home/rpi5/.ssh/github_pi" (empty for no passphrase):
```

**원인:** `ssh-keygen` 실행 시 암호(passphrase) 설정 여부를 묻는 정상적인 프롬프트입니다.

**해결책:** **Enter를 두 번 눌러 암호를 비워둡니다.** CI/CD 자동화 환경에서는 암호가 설정되면 `git pull` 실행 시 대화형 입력이 필요하게 되어 자동화가 불가능합니다.

---

#### 문제 3: 워크플로우의 `/home/pi/` 하드코딩으로 인한 배포 실패

**증상:** GitHub Actions 워크플로우 Step 1에서 경로를 찾지 못해 실패.

**원인:** `deploy-to-pi.yml`에 경로가 `/home/pi/ROBO-Path_project`로 하드코딩되어 있었으나, 실제 파이 계정명이 `rpi5`였습니다 (`/home/rpi5/`).

**해결책:** 워크플로우의 모든 절대 경로를 `$HOME` 환경 변수로 대체합니다. 계정명에 무관하게 동작합니다.
```yaml
# ❌ 하드코딩 (계정명 변경 시 깨짐)
run: cd /home/pi/ROBO-Path_project

# ✅ 환경 변수 사용 (계정명 무관)
run: cd $HOME/ROBO-Path_project
```

---

#### 문제 4: Nginx 미설치로 인한 config 복사 실패

**증상:**
```
cp: cannot create regular file '/etc/nginx/sites-available/robo-path': No such file or directory
```

**원인:** Raspberry Pi OS에는 Nginx가 기본 설치되어 있지 않습니다. `/etc/nginx/` 디렉토리 자체가 존재하지 않았습니다.

**해결책:** Runner 설치 전 또는 최초 구성 단계에서 Nginx를 먼저 설치해야 합니다.
```bash
sudo apt update
sudo apt install nginx -y

# 설치 확인
nginx -v
ls /etc/nginx/sites-available/
```

> **결론:** `2.1 최초 1회 환경 구성` 단계에 Nginx 설치를 반드시 포함시켜야 합니다.

---

#### 문제 5: `sudo: a password is required` — CI/CD에서 sudo 명령 실패

**증상:**
```
sudo: a terminal is required to read the password
sudo: a password is required
Error: Process completed with exit code 1.
```

**원인:** sudoers 설정(`/etc/sudoers.d/robo-path-runner`)이 파이에 적용되지 않아 워크플로우의 `sudo cp`, `sudo systemctl` 명령이 패스워드를 요구했습니다. CI/CD 환경에서는 대화형 입력이 불가능하므로 즉시 실패합니다.

**해결책:** 파이에 SSH 접속 후 sudoers 파일에 허용할 명령어를 등록합니다. `rm`도 반드시 포함해야 합니다.
```bash
sudo visudo -f /etc/sudoers.d/robo-path-runner
```
```
rpi5 ALL=(ALL) NOPASSWD: /bin/systemctl, /usr/bin/nginx, /bin/cp, /usr/bin/ln, /usr/bin/rm, /bin/rm
```
설정 후 검증: `sudo -n systemctl status nginx` (패스워드 없이 실행되면 정상)

---

#### 문제 6: Nginx `conflicting server name "_"` — 기본 사이트와 포트 80 충돌

**증상:** `nginx -t`에서 경고 후 reload 실패, 또는 두 서버가 동일 포트를 listen하는 현상.

**원인:** Nginx 설치 시 자동 활성화되는 `/etc/nginx/sites-enabled/default`가 `listen 80 default_server`를 선언하고 있고, 우리의 `robo-path.conf`도 동일한 포트를 사용하여 충돌했습니다.

**해결책 (두 가지 적용):**
1. 워크플로우에서 default 사이트를 명시적으로 비활성화:
```bash
sudo rm -f /etc/nginx/sites-enabled/default
```
2. `robo-path.conf`에 `listen 80 default_server` 명시하여 우선순위 확정:
```nginx
server {
    listen 80 default_server;  # default 키워드 추가
    ...
}
```

---

#### 문제 7: `sudo nginx -t` 실행 시 패스워드 요구로 인한 CI/CD 실패

**증상:** GitHub Actions 워크플로우 단계에서 아래 에러와 함께 파이프라인이 중단됨.
```
Run sudo nginx -t
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
Error: Process completed with exit code 1.
```

**원인:** `sudoers` 파일(`/etc/sudoers.d/robo-path-runner`)에 Nginx 권한을 NOPASSWD로 허용했음에도 불구하고, 시스템에 따라 `nginx` 바이너리의 실제 경로(`/usr/sbin/nginx` 등)가 달라 `sudo nginx -t` 명령어가 패스워드 없이 실행되지 않았습니다.

**해결책:** 배포 워크플로우(`.github/workflows/deploy-to-pi.yml`) 파일에서 문제가 되는 Nginx 문법 검증 단계(`sudo nginx -t`)를 제거하고, 패스워드 없이 잘 동작하는 `sudo systemctl reload nginx`만 실행하도록 수정하여 우회했습니다.

---

#### 문제 8: Supabase 연동 시 `PGRST125: Invalid path specified in request URL` 에러

**증상:** 라즈베리파이의 Streamlit 대시보드 접속 시 화면에 데이터 대신 아래 에러가 출력됨.
```json
Failed to fetch nodes: {'message': 'Invalid path specified in request URL', 'code': 'PGRST125', 'hint': None, 'details': None}
```

**원인:** GitHub Repository의 Secrets에 `SUPABASE_URL` 변수를 등록할 때, 대시보드에서 복사한 값 끝에 API 경로인 `/rest/v1/`이 포함되어 있었습니다. Supabase Python 패키지는 통신 시 내부적으로 `/rest/v1` 경로를 알아서 덧붙이므로, 주소가 중복되어 발생하는 오류였습니다.
*(예: `https://xxx.supabase.co/rest/v1//rest/v1/nodes` 로 호출됨)*

**해결책:** GitHub Repository `Settings > Secrets and variables > Actions` 메뉴에서 `SUPABASE_URL` 값을 수정하여 끝의 `/rest/v1/` 부분을 지우고 기본 도메인 주소(`https://xxxxxx.supabase.co`)만 남긴 뒤, 워크플로우를 다시 실행(Re-run all jobs)하여 해결했습니다.

---

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

---

## 7. 라즈베리파이 디렉터리 구조
라즈베리파이 내부의 파일 시스템은 크게 **프로젝트 코드 영역** (홈 디렉터리)과 **대용량 데이터 영역** (SSD 마운트)으로 분리하여 관리합니다.

### 7.1 전체 디렉터리 트리
```
/
├── home/
│   └── pi/
│       └── ROBO-Path_project/               # GitHub에서 클론된 프로젝트 루트
│           ├── .github/
│           │   └── workflows/
│           │       ├── supabase-migrations.yml  # 기존 Supabase 마이그레이션 워크플로우
│           │       └── deploy-to-pi.yml         # (신규) CI/CD 배포 워크플로우
│           ├── src/
│           │   ├── domain/                  # 핵심 도메인 로직 (알고리즘, 모델)
│           │   │   ├── algorithms/          # A*, cost_calculator, statistics
│           │   │   └── models/              # Edge, Node, Log, Metadata 등 Pydantic 모델
│           │   ├── application/             # 유즈케이스 서비스
│           │   │   ├── interfaces/          # Repository 프로토콜 정의
│           │   │   └── services/            # PathPlanningService 등 (미구현)
│           │   ├── infrastructure/
│           │   │   ├── database/            # Supabase 클라이언트 및 Repository 구현체
│           │   │   ├── storage/             # (신규) FastAPI 스토리지 서버 진입점
│           │   │   │   └── api.py
│           │   │   └── llm/                 # (미구현) Gemini API 연동
│           │   └── presentation/
│           │       ├── dashboard/           # (미구현) Streamlit 관제 대시보드
│           │       │   └── app.py
│           │       └── ros2_bridge/         # (미구현) WebSocket-ROS2 브릿지
│           │           └── bridge.py
│           ├── config/                      # 라즈베리파이 전용 시스템 설정 파일 (Git 버전 관리됨)
│           │   ├── pi_services/             # Systemd 서비스 유닛 파일 템플릿
│           │   │   ├── robo-path-api.service
│           │   │   └── robo-path-web.service
│           │   └── nginx/                   # Nginx 리버스 프록시 설정 파일
│           │       └── robo-path.conf
│           ├── scripts/                     # 파이 유지보수 셸 스크립트 (Git 버전 관리됨)
│           │   └── snapshot_env.sh          # apt/pip 환경 스냅샷 저장 스크립트
│           ├── venv/                        # Python 가상환경 (Git 추적 제외)
│           ├── requirements.txt             # Python 패키지 목록 (현재 존재)
│           └── .env                         # 환경 변수 (Git 추적 제외)
│
└── mnt/
    └── ssd/
        └── robo-path-data/                  # 1TB SSD 마운트 (대용량 데이터 전용)
            ├── pcd/                         # 3D 포인트 클라우드 맵 파일 (.pcd)
            │   └── YYYY-MM-DD/              # 날짜별 서브 디렉터리로 정리
            ├── logs/                        # 주행 로그 파일 (.csv)
            │   └── YYYY-MM-DD/
            └── backups/                     # 설정 파일 백업 스냅샷 (§8.3 참고)
                └── env_snapshot_YYYYMMDD/
```

### 7.2 디렉터리 분리 원칙

| 영역 | 경로 | 관리 방식 | 비고 |
|---|---|---|---|
| 프로젝트 코드 | `~/ROBO-Path_project/` | Git (GitHub) | 자동 배포 대상 |
| 시스템 설정 파일 | `~/ROBO-Path_project/config/` | Git 추적 + 심볼릭 링크 | Systemd, Nginx 설정 포함 |
| 유지보수 스크립트 | `~/ROBO-Path_project/scripts/` | Git 추적 | 환경 스냅샷 등 관리 도구 |
| 파이썬 가상환경 | `~/ROBO-Path_project/venv/` | `.gitignore` 제외, `requirements.txt`로 재현 | 직접 커밋 금지 |
| 환경 변수 | `~/ROBO-Path_project/.env` | `.gitignore` 제외, 수동 관리 | API 키 등 기밀 정보 포함 |
| 대용량 데이터 | `/mnt/ssd/robo-path-data/` | Git 외부, SSD 직접 관리 | PCD/CSV 파일, Git LFS 미사용 |

---

## 8. 라즈베리파이 환경 버전 관리 전략
라즈베리파이는 클라우드 VM과 달리 물리 장치이므로 환경이 깨지면 복구 비용이 큽니다. 아래 전략으로 **재현 가능하고 롤백 가능한** 환경을 유지합니다.

### 8.1 Python 패키지 버전 고정 (`requirements.txt`)
설치한 패키지 버전을 항상 명시적으로 고정하여 어느 환경에서도 동일한 가상환경을 재현합니다.

```bash
# 현재 설치된 패키지 목록을 버전과 함께 고정 (작업 완료 후 반드시 실행)
pip freeze > requirements.txt

# 라즈베리파이 전용 패키지가 있는 경우 별도 파일로 분리
pip freeze > requirements-pi.txt
```

> **규칙:** 패키지를 새로 설치하거나 업그레이드한 직후 `pip freeze`를 실행하고, 변경된 `requirements.txt`를 Git에 커밋합니다. 이를 통해 코드 변경과 환경 변경의 이력이 함께 추적됩니다.

**`requirements.txt` 작성 예시:**
```
fastapi==0.115.12
uvicorn==0.34.2
streamlit==1.45.1
python-multipart==0.0.20
supabase==2.15.2
websocket-client==1.8.0
google-generativeai==0.8.5
```

### 8.2 시스템 패키지 스냅샷 (`apt`)
Python 가상환경 밖에서 `apt`로 설치한 시스템 패키지(예: `nginx`, `samba`, `ffmpeg` 등)는 `pip freeze`로 추적되지 않습니다. 이를 스크립트로 별도 관리합니다.

**`scripts/snapshot_env.sh` — 환경 스냅샷 저장 스크립트:**
```bash
#!/bin/bash
# 실행 방법: bash scripts/snapshot_env.sh
SNAPSHOT_DIR="/mnt/ssd/robo-path-data/backups/env_snapshot_$(date +%Y%m%d)"
mkdir -p "$SNAPSHOT_DIR"

# 1. apt 설치 패키지 목록 저장
dpkg --get-selections > "$SNAPSHOT_DIR/apt_packages.txt"
echo "[OK] apt 패키지 목록 저장: $SNAPSHOT_DIR/apt_packages.txt"

# 2. Python 패키지 목록 저장 (pip freeze)
source ~/ROBO-Path_project/venv/bin/activate
pip freeze > "$SNAPSHOT_DIR/pip_packages.txt"
echo "[OK] pip 패키지 목록 저장: $SNAPSHOT_DIR/pip_packages.txt"

# 3. OS 및 커널 버전 기록
uname -a > "$SNAPSHOT_DIR/os_info.txt"
cat /etc/os-release >> "$SNAPSHOT_DIR/os_info.txt"
echo "[OK] OS 정보 저장: $SNAPSHOT_DIR/os_info.txt"

echo "=== 스냅샷 완료: $SNAPSHOT_DIR ==="
```

**스냅샷 복원 (재설치) 방법:**
```bash
# apt 패키지 일괄 재설치
sudo dpkg --set-selections < env_snapshot_YYYYMMDD/apt_packages.txt
sudo apt-get dselect-upgrade -y

# pip 패키지 일괄 재설치
pip install -r env_snapshot_YYYYMMDD/pip_packages.txt
```

### 8.3 설정 파일 버전 관리 (Git 추적 대상)
라즈베리파이 고유 설정 파일은 `/etc/` 등 시스템 경로에 위치하지만, **원본을 프로젝트 저장소에 복사하여 Git으로 추적**합니다. 배포 스크립트 또는 CI/CD 파이프라인이 이 파일들을 실제 경로에 복사(심볼릭 링크)합니다.

| 설정 파일 | 시스템 실제 경로 | Git 추적 경로 |
|---|---|---|
| Systemd API 서비스 | `/etc/systemd/system/robo-path-api.service` | `config/pi_services/robo-path-api.service` |
| Systemd Web 서비스 | `/etc/systemd/system/robo-path-web.service` | `config/pi_services/robo-path-web.service` |
| Nginx 설정 | `/etc/nginx/sites-available/robo-path` | `config/nginx/robo-path.conf` |

**CI/CD 워크플로우에서 설정 파일 자동 반영:**
```yaml
# .github/workflows/deploy-to-pi.yml 중 일부
- name: Sync config files
  run: |
    sudo cp config/pi_services/robo-path-api.service /etc/systemd/system/
    sudo cp config/pi_services/robo-path-web.service /etc/systemd/system/
    sudo cp config/nginx/robo-path.conf /etc/nginx/sites-available/robo-path
    sudo systemctl daemon-reload
    sudo nginx -t && sudo systemctl reload nginx
```

### 8.4 환경 변수 (`.env`) 관리
`.env` 파일에는 Supabase URL·API 키, Gemini API 키 등 기밀 정보가 포함되므로 **절대 Git에 커밋하지 않습니다.**

```bash
# .gitignore에 반드시 포함
venv/
.env
*.pcd
*.csv
```

대신 아래 두 가지 방법 중 하나로 관리합니다.

**방법 A: GitHub Actions Secrets 활용 (권장)**
- GitHub Repository `Settings > Secrets and variables > Actions`에 각 키를 Secret으로 등록.
- CI/CD 워크플로우에서 해당 Secret을 파이의 `.env` 파일로 생성하도록 스텝 추가.
```yaml
- name: Write .env file
  run: |
    echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" > ~/ROBO-Path_project/.env
    echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> ~/ROBO-Path_project/.env
    echo "GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}" >> ~/ROBO-Path_project/.env
```

**방법 B: `.env.example` 템플릿 커밋**
- 실제 값이 없는 키 이름만 기록한 `.env.example`을 Git에 커밋하여 팀원이 어떤 변수가 필요한지 파악하도록 안내.
```bash
# .env.example (Git 추적 대상)
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
GEMINI_API_KEY=your_gemini_api_key
STORAGE_BASE_PATH=/mnt/ssd/robo-path-data
```

### 8.5 환경 변경 시 워크플로우 요약
라즈베리파이 환경을 변경할 때마다 아래 순서를 따릅니다.

```
1. 라즈베리파이에서 패키지 설치 또는 설정 파일 수정
       │
       ▼
2. pip freeze > requirements.txt  (Python 패키지인 경우)
   또는 config/ 디렉터리 파일 업데이트 (설정 파일인 경우)
       │
       ▼
3. git add, git commit, git push (변경 이력 GitHub에 기록)
       │
       ▼
4. bash scripts/snapshot_env.sh  (SSD에 전체 환경 스냅샷 저장)
       │
       ▼
5. CI/CD 파이프라인 자동 실행 → 서비스 재시작 및 설정 반영
```

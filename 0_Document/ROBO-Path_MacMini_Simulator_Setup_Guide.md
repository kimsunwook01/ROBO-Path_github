# ROBO-Path 맥미니(시뮬레이터 서버) 셋업 가이드 및 복구 전략

이 문서는 ROBO-Path 시스템의 시뮬레이터를 상시 구동하는 **Mac Mini** 환경의 초기 세팅, 디렉터리 관리 원칙, 그리고 재난 복구(Disaster Recovery) 전략을 기술합니다. 라즈베리파이(Edge Server)와 상호보완적으로 작동하며, 전체 시스템의 가상 환경 제어 및 데이터 생성을 담당합니다.

---

## 1. 개요 및 역할 (Overview & Role)

*   **하드웨어 스펙:** Mac Mini (M2 Pro, 10코어 CPU / 16코어 GPU, 16GB RAM, 512GB SSD)
*   **운영체제:** macOS
*   **핵심 역할:**
    *   **Unity 시뮬레이터 상시 구동:** 로봇의 물리적 이동, Raycast 탐색, 가중치 지표(L, S, E) 생성
    *   **경량 지표 전송:** 생성된 메타데이터를 Supabase 클라우드로 즉각 전송
    *   **대용량 파일 전송:** 주행 로그, 탐색 복셀 데이터(Octree 직렬화 파일) 등 대용량 파일을 라즈베리파이 스토리지로 HTTP 전송
*   **비고:** 기존 초기 아키텍처에서 구상되었던 NVIDIA Isaac Sim + 워크스테이션 조합을 완전히 대체하는 현재 주력 시뮬레이터 서버입니다. 향후 엄청난 물리 연산이 필요한 경우에 한해 워크스테이션으로 이전(Scale-up)될 수 있습니다.

---

## 2. 디렉터리 구조 (Directory Structure)

라즈베리파이와 동일하게 전체 저장소를 클론하되, 맥미니의 저장 공간(512GB) 제약을 고려하여 **대용량 파일은 로컬에 영구 보관하지 않고 임시 버퍼(Buffer)에만 보관**한 뒤 전송 즉시 삭제합니다.

```text
~/ROBO-Path_project/              # GitHub 클론 루트 (프로젝트 코드 및 Unity 프로젝트)
├── Unity/                        # Unity 시뮬레이터 프로젝트 폴더
│   ├── Assets/
│   │   ├── Scripts/
│   │   │   ├── Network/          # WebSocketServer, HeartbeatSender
│   │   │   ├── Robot/            # 이동 제어, Raycast, 피드백 연산 로직
│   │   │   ├── Data/             # MapVersionManager, 메타데이터 관리
│   │   │   ├── Voxel/            # 복셀 및 Octree 시각화/최적화
│   │   │   └── Debug/            # SimulatorLogger, SimulatorValidator
│   │   ├── Scenes/
│   │   └── Tests/
│   │       ├── EditMode/         # Unity CLI 테스트 코드
│   │       └── PlayMode/
│   ├── ProjectSettings/
│   ├── Packages/
│   └── Logs/                     # simulator.log, TestResults.xml (자동화 검증)
├── src/                          # 파이썬 브릿지 백엔드 (라즈베리파이와 구조 공유)
├── .github/workflows/
│   └── deploy-to-mac.yml         # 맥미니 자동 배포 워크플로우
├── .env                          # 환경변수 파일 (보안상 Git 추적 제외)
└── (참고: Unity의 Library/, Temp/, Build/ 등은 .gitignore로 제외됨)

~/robo-path-buffer/               # 임시 데이터 버퍼 영역 (Git 외부, 홈 디렉터리 하위)
├── logs/                         # 전송 대기 중인 주행 로그 (CSV)
└── voxel/                        # 전송 대기 중인 탐색 복셀 데이터 파일 (Octree 직렬화 파일 등)
(※ 전송 성공 시 즉각 삭제되며, 실패 시 일정 용량 초과 시 자동 삭제되도록 스크립팅 구성)
```

---

## 3. 디렉터리 분리 원칙 (Directory Separation Principles)

| 영역 (Zone) | 경로 (Path) | 주요 용도 및 특징 | Git 관리 여부 |
| :--- | :--- | :--- | :--- |
| **Unity 프로젝트** | `~/ROBO-Path_project/Unity/` | Unity 시뮬레이터 코드, 에셋, 씬 관리 | O |
| **파이썬 브릿지** | `~/ROBO-Path_project/src/` | Supabase 연동 및 라즈베리파이 통신 스크립트 | O |
| **임시 버퍼** | `~/robo-path-buffer/` | 생성 직후 전송 대기 중인 파일 거치대 (스토리지 확보용) | X (로컬, 전송 후 삭제) |
| **환경변수** | `~/ROBO-Path_project/.env` | 통신 설정 및 API 키 보관 | X (로컬 백업 필수) |
| **가상환경** | `~/miniconda3/envs/robopath/` | 파이썬 브릿지 구동용 인터프리터 및 패키지 | X (requirements.txt 관리) |

---

## 4. Unity 설치 및 모듈 (Unity Environment)

맥미니에서 자동화 및 크로스 빌드를 원활하게 수행하기 위해 다음 모듈을 반드시 포함하여 설치해야 합니다.

1.  **Unity Hub:** 공식 사이트에서 Mac용 설치
2.  **Unity 에디터:** 버전 **6000.4.11f1 (Unity 6.4)** 설치
    *   *Windows 개발 PC와 버전 불일치 시 직렬화 오류가 발생하므로 반드시 버전을 일치시킵니다.*
3.  **필수 빌드 모듈 (Add Modules):**
    *   `Mac Build Support (Mono)`
    *   `Mac Dedicated Server Build Support` (헤드리스 자동 빌드용)
4.  **필수 패키지 (Package Manager):**
    *   `AI Navigation`
    *   `ProBuilder`
    *   `Cinemachine`

---

## 5. GitHub Actions Self-hosted Runner 구성

코드 푸시 후 맥미니에 변경 사항이 자동 반영되도록 CI/CD 파이프라인을 구축합니다.

1.  **동작 원리:** `main` 브랜치에 코드가 병합되면 `.github/workflows/deploy-to-mac.yml`이 트리거되어 맥미니의 코드를 Pull 하고 헤드리스 시뮬레이터를 재시작합니다.
2.  **Runner 등록:**
    *   GitHub 저장소 Settings > Actions > Runners > New self-hosted runner 선택
    *   운영체제로 `macOS` (Architecture: `ARM64`)를 선택 후 안내된 스크립트 순차 실행
    *   `./svc.sh install && ./svc.sh start` 를 통해 서비스로 등록하여 재부팅 시 자동 실행되도록 구성
3.  **⚠️ 주의 사항 (경로 하드코딩 금지):**
    *   라즈베리파이 셋업 사례에서 홈 디렉터리 하드코딩으로 인한 오류가 자주 발생했습니다. 
    *   워크플로우 및 셸 스크립트 작성 시 절대 경로 대신 `$HOME/ROBO-Path_project` 또는 `~`를 사용하거나 환경변수로 동적 처리해야 합니다.

---

## 6. 운영 모드 및 실행 스크립트 (Execution Modes)

모니터 연결 문제 및 원격 제어 편의성을 위해 **SSH 접속 후 헤드리스 터미널 구동**을 기본으로 합니다.

### 6.1. 헤드리스 모드 (상시 운영)
GUI 없이 백그라운드에서 물리 연산 및 네트워크 통신만 수행합니다. (가장 낮은 리소스 점유)
```bash
# ~/ROBO-Path_project/scripts/run_simulator.sh
#!/bin/bash
export PROJECT_PATH="$HOME/ROBO-Path_project/Unity"
"/Applications/Unity/Hub/Editor/6000.4.11f1/Unity.app/Contents/MacOS/Unity" \
  -batchmode \
  -nographics \
  -projectPath "$PROJECT_PATH" \
  -executeMethod "SimulatorLauncher.RunHeadless" \
  -logFile "$PROJECT_PATH/Logs/simulator.log" &
```

### 6.2. GUI 모드 (시연 및 디버깅)
시연이나 육안 검증이 필요할 때 모니터를 연결하거나 화면 공유로 직접 에디터/빌드 앱을 구동하여 자유 카메라를 확인합니다.

---

## 7. 환경변수 세팅 (.env)

`~/ROBO-Path_project/.env` 파일에는 다음 항목들이 필수적으로 구성되어야 합니다.

```env
# Supabase 연결 정보 (경량 메타데이터 전송용)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJhbGci...

# Unity 내장 WebSocket 서버 포트 (명령 수신)
SIMULATOR_HOST=0.0.0.0
SIMULATOR_WS_PORT=8765

# 라즈베리파이 스토리지 서버 주소 (대용량 파일 전송용)
EDGE_SERVER_URL=http://<RASPBERRY_PI_IP>:8000
UPLOAD_LOG_ENDPOINT=/upload/log
UPLOAD_VOXEL_ENDPOINT=/upload/voxel

# 임시 버퍼 설정
BUFFER_PATH=~/robo-path-buffer
MAX_BUFFER_SIZE_MB=5000

# (선택) LLM 분석용 키
GEMINI_API_KEY=AIza...
```

---

## 8. 재난 복구 전략 (Disaster Recovery Strategy)

맥미니는 물리적인 장비이므로 OS 포맷, 디스크 교체, 또는 알 수 없는 환경 충돌 시 신속한 복구를 위한 체크리스트가 준비되어야 합니다.

### 복구 체크리스트 (재설치 순서)
- [ ] **저장소 클론:** `git clone <repo-url> ~/ROBO-Path_project`
- [ ] **환경 복원:** 백업해둔 `.env` 파일을 프로젝트 루트에 복사 (팀 내 1Password 등 보안 저장소 보관 필수)
- [ ] **버퍼 생성:** `mkdir -p ~/robo-path-buffer/logs ~/robo-path-buffer/voxel`
- [ ] **Unity 런타임 복원:** Unity Hub를 통해 정확히 `6000.4.11f1` 설치 및 Mac Build 모듈 추가
- [ ] **패키지 복원:** `Packages/manifest.json`이 Git으로 관리되므로 Unity 프로젝트를 한 번 열어주면 패키지가 자동 복원됨
- [ ] **Python 가상환경 복원:**
  ```bash
  conda create -n robopath python=3.12 -y
  conda activate robopath
  pip install -r requirements.txt
  ```
- [ ] **Self-hosted Runner 복원:** 기존 Runner 연결 해제 후 섹션 5의 절차에 따라 Runner 재등록 및 서비스(`svc.sh`) 재설치
- [ ] **가동 확인:** `pytest tests/` 실행 및 헤드리스 스크립트 실행 후 로그 확인

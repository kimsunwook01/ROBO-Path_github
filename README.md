# ROBO-Path (하드웨어 피드백 기반 입체 주행 경험 데이터베이스)

Unity 6.4 3D 시뮬레이션 환경(Mac Mini M2 Pro)과 라즈베리파이 에지 서버, 그리고 Supabase 클라우드를 연동하여 로봇의 플랫폼별 물리 피드백(부하율, 안정성, 효율성)을 반영하는 경험 기반 자율주행 경로 최적화 시스템입니다.

자세한 시스템 아키텍처 및 수학적 지표 연산식은 [기술 설계 보고서](0_Document/ROBO-Path_Design_Report.md) 에서 확인할 수 있습니다.

---

## 1. 시스템 구성도 (Architecture Overview)
본 프로젝트는 전기세 절감 및 연산 효율화를 위해 **3-Tier 하이브리드 분산 구조**로 작동합니다.
- **Mac Mini (M2 Pro)**: Unity 6.4 기반 가상 캠퍼스 시뮬레이션 구동 및 탐색(Raycast) 엔진 연산
- **Raspberry Pi 5**: 1TB SSD 기반 대용량 파일 스토리지(FastAPI) 및 Streamlit 관제 웹 서버 호스팅
- **Supabase**: PostgreSQL 기반 클라우드 메타데이터 저장 및 실시간 상태 동기화

---

## 2. 시작 가이드 (Prerequisites & Installation)

본 프로젝트는 핵심 도메인 로직과 인프라 설정이 엄격히 분리된 **클린 아키텍처(Clean Architecture)**를 따릅니다.

### 2.1 사전 요구 사항
* **Python:** 3.10 이상 권장
* **Mac Mini:** macOS 환경, Unity 6.4 (6000.4.11f1)
* **Edge Server:** Raspberry Pi 5 (Nginx, Systemd, GitHub Actions Runner 기반 무중단 환경 구성 완료)
* **Cloud:** Supabase 계정 및 프로젝트 연동 완료 (RLS 정책 적용 완료)

### 2.2 설치 및 환경 구성 (로컬 테스트용)
```bash
# 1. 저장소 클론
git clone https://github.com/kimsunwook01/ROBO-Path_github.git
cd ROBO-Path_github

# 2. Python 가상환경 구성 (또는 Conda 사용)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 환경 변수 설정
# .env 파일을 프로젝트 루트에 생성하고 아래 필수 값들을 채웁니다. (GitHub Secrets 활용 권장)
# SUPABASE_URL=...
# SUPABASE_KEY=...
# SIMULATOR_HOST=192.168.x.x  # 맥미니 로컬 IP
# SIMULATOR_WS_PORT=8765       # Unity WebSocket 포트
```

---

## 3. 디렉토리 구조 (Directory Structure)

```text
ROBO-Path_github/
├── Unity/                       # Unity 6.4 가상 캠퍼스 및 시뮬레이션 환경
├── .github/workflows/           # CI/CD 자동 배포(macOS, RPi) 및 마이그레이션 파이프라인
├── 0_Document/                  # 기획 및 아키텍처 설계 문서 등
├── config/                      # 라즈베리파이 시스템 설정 (Nginx, Systemd)
├── scripts/                     # 환경 스냅샷 및 DB 유지보수 등 셸 스크립트
├── src/                         # 핵심 소스 코드 (클린 아키텍처 기반)
│   ├── domain/                  # 핵심 알고리즘(A*) 및 Pydantic 데이터 모델
│   ├── application/             # Use Case 및 Repository 인터페이스(Protocol)
│   ├── infrastructure/          # 외부 기술 구현체 (Supabase DB, FastAPI Storage)
│   └── presentation/            # UI 및 외부 진입점 (Streamlit Dashboard, WebSocket Client Bridge)
├── tests/                       # 단위/통합 테스트 스크립트
├── environment.yml              # Conda 환경 의존성
├── requirements.txt             # Pip 의존성 목록
└── README.md                    # 프로젝트 소개 (현재 파일)
```

---

## 4. 실행 및 배포 방법 (How to Run & Deploy)

본 프로젝트의 운영 환경은 GitHub Actions를 통해 라즈베리파이 에지 서버로 소스 코드가 **무중단 자동 배포(CI/CD)** 되도록 구성되어 있습니다.

### 4.1 에지 서버 웹 대시보드 접속
1. 코드를 수정한 뒤 GitHub `main` 브랜치에 Push합니다.
2. 라즈베리파이의 배포 파이프라인이 즉시 가동되어 최신 코드를 당겨오고, 패키지를 갱신한 뒤 서버를 재시작합니다.
3. 배포가 완료되면 동일 로컬 네트워크 망에서 브라우저를 열고 라즈베리파이 IP 주소(예: `http://192.168.219.113`)로 접속합니다.
4. **ROBO-Path Database Explorer** 대시보드가 정상적으로 로드되며 Supabase와 실시간 연동되는 것을 확인할 수 있습니다.

### 4.2 인프라 및 아키텍처 관리 규칙
* **의존성 동기화:** Python 패키지를 새로 설치한 경우, 반드시 `requirements.txt`에 명시하고 커밋하여 라즈베리파이의 서버 환경과 동기화되도록 해야 합니다.
* **데이터 무결성 검증:** 데이터베이스에 적재되거나 연산에 사용되는 모든 데이터는 반드시 `src/domain/models` 디렉터리에 정의된 `Pydantic` 클래스를 통과하도록 설계되어 있습니다.
* **의존성 방향 준수:** `domain` 계층은 어떠한 외부 인프라 기술(DB 클라이언트 등)에도 의존해서는 안 되며, 통신 로직은 `infrastructure` 계층에 작성하여 인터페이스를 통해 주입(DI)합니다.

# ROBO-Path (하드웨어 피드백 기반 입체 주행 경험 데이터베이스)

NVIDIA Isaac Sim 시뮬레이션 환경과 라즈베리파이 에지 서버, 그리고 Supabase 클라우드를 연동하여 로봇의 플랫폼별 물리 피드백(부하율, 안정성, 효율성)을 반영하는 경험 기반 자율주행 경로 최적화 시스템입니다.

자세한 시스템 아키텍처 및 수학적 지표 연산식은 [기술 설계 보고서](0_Document/ROBO-Path_Design_Report.md) 에서 확인할 수 있습니다.

---

## 1. 시스템 구성도 (Architecture Overview)
본 프로젝트는 전기세 절감 및 연산 효율화를 위해 **3-Tier 하이브리드 분산 구조** 로 작동합니다.
- **Workstation**: NVIDIA Isaac Sim 구동 및 대용량 데이터(Point Cloud) 정제
- **Raspberry Pi 5**: 1TB SSD 기반 경량 지도/로그 저장 및 Streamlit 관제 웹 서버 구동
- **Supabase**: PostgreSQL 기반 클라우드 메타데이터 및 실시간 상태 동기화

---

## 2. 시작 가이드 (Prerequisites & Installation)

본 프로젝트는 의존성 관리를 위해 `conda`를 사용합니다.

### 2.1 사전 요구 사항
* **Python:** 3.10 이상 권장
* **Workstation:** Ubuntu 환경, NVIDIA Isaac Sim, ROS2 (`rosbridge_suite`)
* **Edge Server:** Raspberry Pi 5 (1TB SSD 마운트 완료 상태)
* **Cloud:** Supabase 계정 및 프로젝트 (향후 생성 예정)
* **API:** Google Gemini API Key (향후 발급 예정)

### 2.2 설치 및 환경 구성
```bash
# 1. 저장소 클론 (경로는 예시입니다)
git clone https://github.com/kimsunwook01/ROBO-Path_github.git
cd ROBO-Path_project

# 2. Conda 가상환경 생성 및 활성화
conda env create -f environment.yml
conda activate robopath

# (참고) pip를 통한 패키지 추가 시
# pip install -r requirements.txt
```

## 3. 디렉토리 구조 (Directory Structure)

현재 프로젝트는 초기 기획 단계로, 향후 다음과 같은 기본 구조로 확장될 예정입니다.

```text
ROBO-Path_project/
├── 0_Document/                  # 기획 및 아키텍처 설계 문서 등
│   ├── ROBO-Path_Design_Report.md
│   └── ROBO-Path_Software_Architecture.md # 클린 아키텍처 설계서
├── src/                         # 핵심 소스 코드 (클린 아키텍처 기반)
│   ├── domain/                  # 비즈니스 로직 및 Pydantic 데이터 모델 (의존성 없음)
│   ├── application/             # Use Case 및 인터페이스(Protocol) 정의
│   ├── infrastructure/          # 외부 기술 구현체 (Supabase, Gemini API 등)
│   └── presentation/            # UI 및 외부 진입점 (Streamlit, ROS2 Bridge)
├── tests/                       # 단위/통합 테스트 스크립트
├── Command_list.md              # 주요 명령어 모음집
├── environment.yml              # Conda 환경 의존성
├── requirements.txt             # Pip 의존성 목록
└── README.md                    # 프로젝트 소개 (현재 파일)
```

## 4. 개발 및 협업 규칙 (Contribution Rules)

* **의존성 관리:**
  * 새로운 라이브러리를 설치한 경우, 반드시 `environment.yml` 또는 `requirements.txt`를 갱신해야 합니다. (갱신 방법은 `Command_list.md` 참조)
* **코드 컨벤션:** 
  * Python PEP 8 가이드라인을 따릅니다.
  * DB 적재 등 무결성이 중요한 데이터 처리는 반드시 `Pydantic` 클래스를 통과하도록 설계해야 합니다.
* **커밋 메시지 (권장):**
  * `태그: 작업 내용` 형식을 사용합니다. (예: `FEAT: A* 알고리즘 기초 로직 작성`, `MODIFY: README.md 내용 수정`)

## 5. 실행 방법 (How to Run)

> 🚧 **현재 프로젝트는 기반 인프라 기획 단계입니다.**

구체적인 소스 코드가 작성된 이후, 다음 요소들의 실행 방법을 이곳에 추가할 예정입니다.
1. Workstation의 ROS2 Bridge 서버 구동 방법
2. 라즈베리파이의 Streamlit 대시보드 웹 서버 실행 명령어
3. 시뮬레이터(Isaac Sim)와의 연동 테스트 방법

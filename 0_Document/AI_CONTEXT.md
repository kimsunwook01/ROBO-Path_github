# 🤖 AI Context & Project Status Reference

이 문서는 AI 어시스턴트가 프로젝트의 컨텍스트를 기억 상실 없이 명확히 인지하고, 일관된 방향으로 코딩 및 아키텍처 설계를 이어나가기 위한 **상태 요약 및 지침서**입니다. 
> **AI Instruction:** 새로운 대화 세션을 시작하거나 구조적인 코드를 작성하기 전에 반드시 이 문서를 최우선으로 읽고 지침을 따르세요.

---

## 1. 프로젝트 요약 (Project Overview)
- **프로젝트명:** ROBO-Path (로봇 기종별 하드웨어 피드백 기반 입체 주행 경험 데이터베이스)
- **목표:** 정적인 2D 지도를 넘어, 플랫폼(바퀴형/보행형)의 실제 물리적 주행 피드백(부하율, 안정성 등)을 가중치로 반영하는 최적 경로 탐색 시스템 구축
- **핵심 기술 스택:** Python 3.10+, Supabase (PostgreSQL DB), Streamlit (UI), Google Gemini API (자연어 피드백), NVIDIA Isaac Sim (시뮬레이터), ROS2 (제어 브릿지)

## 2. 핵심 아키텍처 및 코딩 원칙 (Core Principles)

본 프로젝트는 "바이브 코딩"으로 인한 스파게티 코드를 방지하기 위해 엄격한 **클린 아키텍처(Clean Architecture)**를 따릅니다.

- **인프라 분산 구조 (3-Tier):** 
  1. Workstation (고성능 연산 및 시뮬레이터 구동)
  2. Raspberry Pi 5 (대용량 파일 스토리지 및 관제 대시보드 호스팅)
  3. Supabase (경량화 메타데이터 및 지표 통계 클라우드 DB)
- **🚨 AI가 코딩 시 절대 준수해야 할 규칙:**
  1. **의존성 방향:** `domain` 계층은 절대 외부 라이브러리(DB 클라이언트, Streamlit 등)를 `import`해서는 안 됩니다. 순수 파이썬 로직만 존재해야 합니다.
  2. **의존성 주입 (DI):** DB 통신 로직은 `infrastructure` 계층에 작성하고, 인터페이스(Protocol)를 통해 `application` 계층에 주입하여 결합도를 낮춰야 합니다.
  3. **데이터 검증:** 모든 DB 삽입 전후에는 반드시 `Pydantic` 클래스를 통해 타입 및 값의 무결성을 검증해야 합니다.

## 3. 관련 문서 링크 (Related Documents)
자세한 기술 명세가 필요할 경우 아래 문서들을 참조하세요.
- 전체 기획 및 분산 처리 명세: `0_Document/ROBO-Path_Design_Report.md`
- 데이터베이스 ERD 및 DDL 스키마: `0_Document/ROBO-Path_Supabase_DB_Architecture.md`
- 폴더 구조 및 계층별 분리 전략: `0_Document/ROBO-Path_Software_Architecture.md`
- 대시보드 연동 기획(Streamlit): `0_Document/ROBO-Path_Streamlit_Dashboard_Plan.md`

---

## 4. 진행 상황 타임라인 (Current Status & Next Steps)

**✅ [완료된 작업]**
- [x] 프로젝트 초기 요구사항 분석 및 방향성 수립
- [x] .env 파일 추적 해제 및 Git 기초 설정 완료
- [x] 클린 아키텍처 기반의 4계층(`domain`, `application`, `infrastructure`, `presentation`) 폴더 구조 세팅
- [x] Supabase 클라우드 데이터베이스 초기 DDL 및 스키마 설계 완료
- [x] Supabase 초기화용 마이그레이션 SQL 코드(`supabase/migrations/...`) 작성 및 로컬 Git 커밋 완료
- [x] **DB 구축 및 연동:** Supabase 콘솔에서 프로젝트 생성 후 GitHub Actions 기반의 마이그레이션 자동 배포 파이프라인 구축 완료
- [x] 모든 테이블에 대한 Row Level Security (RLS) 활성화 및 익명 읽기 허용 정책 마이그레이션 SQL 코드 작성 완료
- [x] **2. 핵심 도메인 모델 작성 (`src/domain/models/`)**
  - `MapMetadata`, `Robot`, `Node` 계층, `Edge`, `MissionLog`, `Incident` 등 Pydantic 기반 무결성 검증 모델 작성 완료
- [x] **3. Supabase Client 및 의존성 주입 구조 설계 (`src/infrastructure/`, `src/application/`)**
  - Supabase 연결 싱글톤 클라이언트, Repository 통신 규약(Protocol), Supabase용 Repository 구현체 작성 완료
- [x] **4. 순수 도메인 알고리즘 설계 및 구현 (`src/domain/algorithms/`)**
  - 플랫폼 가중치 기반 Edge Cost 산출, A* 경로 탐색, 하드웨어 피드백 통계 누적(Aggregation) 로직 구현 완료

**🚀 [현재 대기 중인 작업 (Next Action)]**
- [ ] **5. 애플리케이션 서비스 계층 구현 (`src/application/services/`)**
  - [ ] 도메인 알고리즘(A*)과 인프라(Repository)를 연결하여 경로를 탐색하는 `PathPlanningService` 작성
  - [ ] 주행 로그가 삽입되면 엣지 통계를 갱신하는 `FeedbackAggregationService` 작성
- [ ] **6. LLM 기반 피드백 지식화 파이프라인 (`src/infrastructure/llm/`)**
  - [ ] Google Gemini API 연동 모듈 작성 (자연어 피드백 -> 구조화된 JSON)
- [x] **7. 관제 대시보드 UI 구축 (`src/presentation/dashboard/`)**
  - [x] [Phase 1] Supabase-Streamlit 데이터 연동 검증 및 테이블 출력 (`app.py`) - **완료** (라즈베리파이 CI/CD 환경에서 구동 및 RLS 통신 검증)
  - [ ] [Phase 2] Streamlit 기반의 노드/엣지 지도 시각화 대시보드 뼈대 작성
  - [ ] [Phase 3] A* 경로 탐색 시뮬레이터 폼 및 결과 시각화
- [ ] **8. 에지 서버(라즈베리파이) 인프라 및 통신 구현 (`src/infrastructure/storage/`, `src/presentation/ros2_bridge/`)**
  - [x] [Phase 1] GitHub Actions Self-Hosted Runner 기반 CI/CD 자동 배포 파이프라인 구축 (**완료** - Runner가 Systemd 서비스로 등록, 부팅 시 자동 실행)
  - [x] [Phase 2] 라즈베리파이 1TB SSD 마운트 권한 및 파이썬 가상환경(venv) 세팅 (**완료** - `/home/rpi5/ROBO-Path_project/venv/` 구성)
  - [x] [Phase 3] 로컬 SSD 스토리지 파일(PCD, 원천 로그) 관리용 FastAPI 엔드포인트 구현 (**완료** - `src/infrastructure/storage/api.py` 구현, `/upload/pcd`, `/upload/log`, `/files/{path}`, `/health` 엔드포인트)
  - [x] [Phase 4] Systemd 무중단 서비스 데몬 등록 및 Nginx 리버스 프록시 라우팅 설정 (**완료** - `robo-path-api.service` 활성화, Nginx 포트 80 라우팅 적용)
  - [ ] [Phase 5] 웹소켓 기반 ROS2 제어 브릿지 스크립트 작성 및 통신망 구축 (**다음 작업**)

> **Update Rule:** 이 파일은 프로젝트의 주요 마일스톤이 달성되거나 아키텍처 정책이 변경될 때마다 AI에 의해 갱신되어야 합니다.

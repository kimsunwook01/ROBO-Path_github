# ROBO-Path Streamlit 대시보드 초기 연동 기획 (Intermediate Dashboard)

본 기획은 인프라 및 DB 초기화 작업 직후, 복잡한 애플리케이션 서비스 로직(A* 경로 탐색, LLM 피드백 등)을 구현하기에 앞서 **Supabase 데이터베이스와 Streamlit 대시보드 간의 데이터 연동을 브라우저 상에서 가볍게 확인하기 위한 중간 단계 작업**을 정의합니다.

## 1. 목적 (Objective)

- 전체 UI/UX를 거창하게 디자인하는 대신, 오직 **데이터베이스에 저장된 테이블 데이터가 Streamlit을 통해 정상적으로 조회되고 화면(표 형식)에 출력되는지**를 검증합니다.
- 인프라(Supabase 클라이언트)와 프레젠테이션(Streamlit) 계층 간의 연결 파이프라인이 정상 동작하는지 테스트하는 "Proof of Concept" 역할을 합니다.

## 2. 작업 내역 (Proposed Changes)

### Presentation Layer (Dashboard)

#### `src/presentation/dashboard/app.py` 생성
- **역할:** Streamlit 애플리케이션의 메인 엔트리 포인트 및 연동 테스트 스크립트
- **구현 스펙:**
  - `st.title()`, `st.header()` 등을 활용한 단순 레이아웃 구성
  - 이미 구현되어 있는 `src/infrastructure/database/client.py` 및 Repository 클래스(`supabase_node_repo.py`, `supabase_edge_repo.py`)를 활용하여 데이터 Fetch 로직 작성
  - 조회된 데이터를 `st.dataframe()`을 사용하여 단순 표 형태로 화면에 렌더링
  - 연동 성공 여부를 직관적으로 알 수 있도록 데이터 로딩 상태(Loading spinner) 추가 및 성공/실패 시 `st.success()`, `st.error()` 메시지 출력

## 3. 검증 계획 (Verification Plan)

1. 워크스테이션(로컬) 터미널에서 아래 명령어를 실행하여 Streamlit 서버를 구동합니다.
   ```bash
   streamlit run src/presentation/dashboard/app.py
   ```
2. 웹 브라우저(`http://localhost:8501`)로 자동 연결되는지 확인합니다.
3. 브라우저 화면상에 Supabase DB에 적재된 `nodes` 및 `edges` 테이블의 데이터가 DataFrame(표) 형태로 정상 출력되는지 육안으로 확인합니다.

---

## 4. 검증 결과 및 완료 상태 (Status: Completed)

- **2026-05-18:** 초기 로컬 테스트 계획을 수정하여, 실제 운영 환경인 라즈베리파이(Edge Server)의 CI/CD 파이프라인(GitHub Actions)을 통해 즉시 배포하고 검증하는 방식으로 전환했습니다.
- **결과:**
  - Nginx 리버스 프록시(80 포트 -> 8501 포트) 라우팅 검증 완료.
  - GitHub Secrets를 이용한 `.env` 자동 주입(Supabase URL, Key) 파이프라인 검증 완료.
  - Supabase SQL Editor를 통해 더미 데이터를 삽입한 후(RLS 정책 하에), Streamlit 대시보드에서 `nodes` 및 `map_edges` 테이블 데이터를 성공적으로 불러오고 시각화(표)하는 것을 확인했습니다.
- **결론:** 프레젠테이션 계층(Streamlit) - 인프라 계층(라즈베리파이 서버) - 데이터 계층(Supabase) 간의 End-to-End 통신 파이프라인이 완벽히 구축되었습니다.

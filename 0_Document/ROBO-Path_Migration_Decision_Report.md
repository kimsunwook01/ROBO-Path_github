> ⚠️ **[고정 문서 / FROZEN DOCUMENT]**
> 본 문서는 2026-06-13 시점의 설계 전환 의사결정을 기록한 스냅샷입니다.
> 이후 프로젝트 설계가 변경되더라도 본 문서는 수정하지 않으며,
> 문서 최신화·일괄 수정·용어 정리 등의 지시 대상에서 제외합니다.
> 당시의 결정 맥락과 사유를 보존하는 것이 목적입니다.

---

# ROBO-Path 설계 전환 의사결정 보고서 (Migration Decision Report)

**작성 시점:** 2026-06-13
**문서 성격:** 의사결정 기록(Decision Log) 스냅샷
**배경:** 데이터베이스 과목 기말 프로젝트. AI 에이전트(Antigravity)를 활용한 개발을 전제로, 시뮬레이터 환경을 포함한 다수의 설계 결정이 단기간에 집중적으로 변경되었다. 본 보고서는 그 전환의 내용과 **사유**를 시간순으로 기록하여, 이후 구현 단계 및 보고서 작성 시 맥락을 잃지 않도록 한다.

---

## 1. 핵심 전환: 시뮬레이터 환경 변경

- **관련 커밋:** `3c635e0` (MODIFY: 문서 수정. 시뮬레이션 구현 유니티 + 맥미니 m2 pro 구성으로 변경)
- **주요 수정 파일:** `0_Document/ROBO-Path_Software_Architecture.md`, `0_Document/ROBO-Path_Unity_Simulator_Architecture.md`

**변경 전:** NVIDIA Isaac Sim + Ubuntu 22 워크스테이션 (RTX 5090, 9950X3D, DDR5 64GB)
**변경 후:** Unity 6.4 (6000.4.11f1) + Mac Mini (M2 Pro, 16GB)

**사유:**
- Isaac Sim은 처음 다루는 도구로 설치·세팅·씬 구성에 학습 비용이 크고, 단기 마감에 부적합하다고 판단.
- 본 프로젝트의 핵심은 데이터베이스(피드백 누적 → 경로 최적화)이며, 정밀 물리 시뮬레이션은 부차적이다. Unity의 NavMesh 기반 시뮬레이션으로 충분하다.
- 시뮬레이션이 가벼워지면서 고성능 GPU(워크스테이션)가 필수가 아니게 되었고, 상시 가동 시 전력 효율이 뛰어난 Mac Mini가 더 적합하다고 판단(워크스테이션 약 400W급 대비 Mac Mini 약 25W급).
- Mac/Linux 크로스 빌드가 가능하므로 Windows 개발 PC에서 개발하고 Mac Mini에서 구동하는 구조가 성립한다.

**보존 사항:** 워크스테이션은 폐기하지 않으며, 향후 성능 부족 시 또는 실제 Isaac Sim 연동 시 대체/확장 옵션으로 유지한다. 라즈베리파이와 Supabase의 역할 및 기존 백엔드는 변경 없이 유지한다.

---

## 2. 시뮬레이션 범위 조정 경과

초기 구상에서 최종 범위까지 단계적으로 축소되었다.

- **초기:** 아파트 단지 + 건물 내부(복도, 계단)에서 로봇이 현관까지 배달.
- **1차 조정:** 건물 내부 구현은 다층 NavMesh의 난이도와 무료 에셋 부재로 부담이 크다고 판단. 단독주택 단지 야외 이동(언덕, 계단, 평지, 터널)으로 축소, 배달 목표는 주택 현관 앞.
- **2차 조정:** 맵 규모를 연세대 미래캠퍼스 일부를 모델로 한 약 500m × 500m 가상 캠퍼스로 확정. 실제 지명을 모델링하지 않고 가상 지역으로 구성("프레임워크는 실제와 동일, 데이터만 가상" — 실서비스 시 맵만 교체 가능하도록).
- **최종:** 건물 내부 구현은 보류(3단계 여유 시 검토). 자율 탐색은 핵심 기능으로 유지. NPC(사람/자동차) 및 그 인식 AI는 별도 프로젝트 수준이라 제외.

---

## 3. 자율 탐색 및 3D 시각화 결정

- **관련 커밋:** `db77306` (ADD: 시뮬레이터 아키텍쳐 설계 문서 추가), `29de377` (ADD: 시뮬레이션 최적화 명세서 추가)
- **주요 수정 파일:** `0_Document/ROBO-Path_Unity_Simulator_Architecture.md`, `0_Document/ROBO-Path_Optimization_Specification.md`

### 3.1 자율 탐색 (핵심 기능)
- "위성 지도만 주어진 초기 상태에서 로봇이 스스로 탐색하며 지도를 채워나가는" 시뮬레이션 게임 컨셉.
- 실제 LiDAR/SLAM 대신 **Raycast 기반 시야 감지**로 LiDAR를 모사(전방 180도, Ray 36개, 최대 30m). Ray 히트 지점 주변 노드를 DISCOVERED로 전환.
- "사전 정의된 길을 탐색으로 발견하는 것이 의미가 있는가"라는 의문에 대해: 본 과목은 DB 과목이므로 SLAM 자율 매핑이 아닌 "데이터 누적 → 경로 최적화"가 평가 핵심이다. 사전 정의 그래프는 PoC 단계로 두고, 클린 아키텍처상 infrastructure 교체만으로 실제 SLAM 연동이 가능하도록 설계.

### 3.2 3D 시각화 (B안: Fog of War)
- **결정:** PCD(포인트 클라우드) 직접 생성(A안) 대신, Unity 씬의 실제 3D 모델을 활용하되 로봇이 관측한 표면만 드러내는 Fog of War 방식(B안) 채택.
- **사유:** 로봇 센서를 1:1로 구현한 것이 아니므로 가짜 PCD 생성은 부적절. 미탐색/사각지대는 가리고, 관측한 표면만 점진적으로 공개하는 방식이 컨셉에 부합.
- 미탐색 영역 색상은 사용자 선택(검정 기본/투명/하양), 탐색 시점이 오래된 영역일수록 어둡게(Temporal Fading).
- **`pcd_file_url` 필드 의미 재정의:** 기존 "3D 포인트 클라우드 파일 경로" → "탐색 복셀 데이터(Octree 직렬화) 파일 경로". 스키마 변경 최소화를 위해 필드명은 유지.

### 3.3 복셀 최적화 (필수 기능, 별도 명세서로 분리)
- 표면 복셀화(Surface Voxelization): 드러난 면만 복셀화, 내부 볼륨 무시.
- Octree 동적 해상도: 평탄면은 크게 병합, 복잡한 사물은 최소 0.1m³까지 세분화.
- 2.5D 높이 처리, 거리 기반 컬링, 청크 단위 로드/언로드.
- Mac Mini(16GB)로 상시 가동 가능하도록 설계. 성능 부족 시 워크스테이션 이전.
- **Antigravity 기술 검토 반영:** 바이너리 직렬화 우선(GC 스파이크 방지), Temporal Fading의 CPU/GPU 역할 분리(헤드리스에서는 데이터만 누적), 2.5D↔Octree 경계 EditMode 우선 검증. Job System 병렬 Raycast는 다중 로봇 대비 "향후 확장"으로 분리.

---

## 4. 통신 아키텍처 정리

- **관련 커밋:** `475cdc3` (FIX: 브릿지 3분리·페일세이프·버전관리·마이그레이션 명세 정리), `656614d` (MODIFY: 문서 수정. 시뮬레이션과 프로그램 간의 통신 방식)
- **주요 수정 파일:** `0_Document/ROBO-Path_Unity_Simulator_Architecture.md`

기존 문서에 브릿지 경로가 2개로 혼재되어 있던 것을 역할 기준 3개로 명확히 분리했다.

| 방향 | 역할 | 위치 | 방식 |
|---|---|---|---|
| 라즈베리파이 → Unity | 명령 하달(목적지, 시간배율, 날씨 등) | `src/presentation/ros2_bridge/bridge.py` | WebSocket 클라이언트 |
| Unity → Supabase | 경량 지표(L, S, E), 탐색 결과 | `src/infrastructure/bridge/bridge.py` | Python 서브프로세스 + SDK |
| Unity → 라즈베리파이 | 대용량 파일(로그 CSV, 복셀 데이터) | `src/infrastructure/storage/api.py` | HTTP POST → FastAPI |

- ROS2 + rosbridge_suite는 Isaac Sim 전제였으므로 제거. Unity 내장 WebSocket 서버(`WebSocketServer.cs`)로 대체.
- 외부 → Unity 명령은 Supabase Realtime을 중계로 활용하여 별도 서버 추가를 회피.

---

## 5. 페일세이프 및 버전 관리

- **관련 커밋:** `475cdc3` (FIX: 브릿지 3분리·페일세이프·버전관리·마이그레이션 명세 정리)
- **주요 수정 파일:** `0_Document/ROBO-Path_Unity_Simulator_Architecture.md`

- **페일세이프:** 시뮬레이터(Mac Mini) 오프라인 감지 시 Streamlit이 읽기 전용 모드로 자동 전환, 재구동 시 자동 복구. `simulator_status` 테이블 + 하트비트(10초 주기) 방식. 기존 rosbridge 핑 방식을 Unity 상태 기반으로 변경. (읽기 전용 모드는 인증과 무관하게 시뮬레이터 가동 여부에만 연동.)
- **지도 버전 관리:** 세맨틱 버전. 로봇이 탐험 후 BASE 복귀 시 신규 발견 노드/엣지가 있으면 마이너 버전 자동 상승(v1.0.0 → v1.1.0). 메이저는 맵 구조 변경 시 수동.

---

## 6. 인증 및 세션 관리 (설계 완료, 구현 보류)

- **관련 커밋:** `375c271` (ADD: Auth design doc and pending migration), `5a4973d` (ADD: Session management migration), `954e662` (MODIFY: Refactor session management to use snapshot archiving)
- **주요 수정 파일:** `0_Document/ROBO-Path_Auth_Design.md`, `supabase/migrations/20260613210000_add_user_id_to_logs.sql`, `supabase/migrations/20260613212500_add_session_management.sql`

### 6.1 인증
- Supabase Auth 활용(비밀번호 해싱/세션을 Supabase가 처리 — "편하고 확실한 방법").
- 아이디를 `{아이디}@robopath.app` 형식으로 내부 변환. `.local` 등 비표준 TLD는 Supabase가 거부할 수 있어 유효 형식 도메인 사용 + "Confirm email" 비활성화로 인증 메일 회피.
- 회원가입은 아이디 + 비밀번호 + **인증키**(사전 공유된 고정 가입 암호, 교수에게 메일 전달). 로그인 시 전원 운영자(단일 등급).

### 6.2 데이터 소유권
- **공용:** 지도/탐색/로봇/통계 — 여러 로봇의 탐색을 하나의 지도로 누적하여 집단 공간지능을 형성하는 것이 프로젝트 목적이므로 공유.
- **개인:** mission_logs, incidents — 본인 것만 열람(user_id 기반 RLS).

### 6.3 세션 관리 (스냅샷 아카이빙 방식)
- 세션 = "게임 세이브 슬롯". 맵 구조는 고정, 탐색 상태만 세션별로 관리. 데모 시 백지 상태부터 체험 가능하게 하는 것이 목적.
- **방식 전환 경과:** 초기에는 모든 세션 종속 테이블에 `session_id`를 추가하는 방식으로 설계했으나, (1) `discovered_nodes`의 PK 충돌(노드당 1행 제약), (2) `map_edges` 중복, (3) A*/Repository/build_graph 전반에 세션 필터가 침투하는 문제가 있었다. 이를 피하기 위해 **스냅샷 아카이빙 방식**으로 전환: 작업 테이블은 항상 현재 세션 데이터만 보유하고, 세션 전환 시 백엔드가 스냅샷 저장→초기화→복원을 수행. 기존 백엔드 코드는 세션을 인식할 필요가 없다.
- 동시성: 탭 열림=로그인, 닫힘=로그아웃(하트비트 핑). 다른 접속자 존재 시 세션 변경 차단 + 안내(비정상 종료 시 재접속 후 로그아웃 안내). 연구실 대면 사용 전제로 과도한 타임아웃 로직은 생략.
- **구현 시점:** Unity 시뮬레이터 완성 후.

---

## 7. 백엔드 안정화

- **관련 커밋:** `51b1708` (ADD: 백엔드 안정화 작업), `5a8c715` (FIX: 시뮬레이터 아키텍쳐 문서 efficiency 상한 부분 내용 구체화)
- **주요 수정 파일:** `tests/test_cost_calculator.py`, `src/utils/logging_config.py`, `src/infrastructure/repositories/supabase_repository.py`

초기 GitHub 평가에서 지적된 항목들을 시뮬레이터 착수 전 처리했다.

- **단위 테스트:** 도메인 알고리즘(a_star, cost_calculator, statistics)에 pytest 12종 추가, 전체 통과 확인.
- **에러 처리:** Repository의 `print` 기반 예외 처리를 `logging`으로 전환(연결/데이터 오류 구분, `exc_info`). `logging_config.py` 신설.
- **efficiency 상한:** 처음에 `le=1.0` 추가를 검토했으나, 내리막 등에서 예상보다 빠를 경우 E가 1.0을 초과할 수 있고 이때 페널티가 감소하여 비용이 낮아지는 것이 **의도된 설계**임을 확인. 상한 미설정 유지(DB·도메인 모델 모두). 문서의 "최대 1.0" 오기만 정정.
- **Use Case 계층:** `PathPlanningService`, `FeedbackAggregationService`가 이미 구현되어 있어 별도 작업 불필요함을 확인.

---

## 8. 맥미니 셋업 및 복구 전략

- **관련 커밋:** `9f8aeb3` (docs: Update simulator terminology and create Mac Mini setup guide)
- **주요 수정 파일:** `0_Document/ROBO-Path_MacMini_Simulator_Setup_Guide.md`

- 라즈베리파이 가이드에 준하는 수준의 Mac Mini 셋업 가이드 신설(디렉터리 구조, Unity 설치/모듈, Self-hosted Runner, 헤드리스/GUI 운영 모드, 환경변수).
- 평소 헤드리스(`-batchmode -nographics`) + SSH 원격 제어, 시연 시에만 모니터 연결하여 자유 카메라 확인(개발 PC와 모니터 공유 문제 회피).
- 저장 공간이 적으므로(512GB) 대용량 파일은 로컬에 영구 보관하지 않고 임시 버퍼만 두고 라즈베리파이로 전송.
- 물리 장치 복구 비용을 고려한 재난 복구 체크리스트 포함.

---

## 9. 미해결 / 보류 항목 (구현 단계에서 처리)

- **관련 커밋:** `50648c1` (docs: Add implementation prerequisites for auth and session)
- **주요 수정 파일:** `0_Document/ROBO-Path_Auth_Design.md`

- **RLS 경고:** `sessions`, `active_sessions` 테이블에 RLS 미적용 경고 발생. 빈 테이블이고 실서비스가 아니므로 현재는 방치, 인증/세션 구현 시 RLS 정책과 함께 처리.
- **마이그레이션 자동 배포 충돌:** `supabase-migrations.yml`이 `supabase/migrations/` 변경을 감지해 `supabase db push`로 전체 적용하므로, 파일 상단의 "적용 보류" 주석이 자동 배포를 막지 못함. 그 결과 user_id·세션 마이그레이션이 의도와 달리 DB에 적용됨. 롤백하지 않고 구현 단계에서 활성화 예정. 향후 진짜 보류가 필요하면 별도 폴더 분리 필요.
- **인증/세션 실제 구현:** 시뮬레이터 완성 후 진행.

---

## 10. 현재 상태 요약

- **완료:** 백엔드(클린 아키텍처, A*, 서비스 계층, 단위 테스트, logging), 라즈베리파이 인프라, 전체 설계 문서, 보류 마이그레이션 준비.
- **다음 단계:** Unity 시뮬레이터 구현 (Step 1 — 프로젝트 생성 및 GitHub 연동).
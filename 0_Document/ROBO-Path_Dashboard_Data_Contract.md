# ROBO-Path 관제 대시보드 데이터 계약서 (Dashboard Data Contract)

> 작성일: 2026-06-17
> 목적: 관제 대시보드(Streamlit) UI를 mock 데이터로 먼저 제작하고, 백엔드(Supabase 스키마 / Unity 갱신 로직)를 항목별로 점진적으로 연결하기 위한 데이터 규격 합의 문서.

---

## 1. 배경 및 작성 의도

대시보드 UI 제작과 백엔드 구현을 병행하기 위해, 화면이 필요로 하는 데이터의 **필드명·타입·enum 값**을 먼저 고정한다. UI는 이 문서에 정의된 모양 그대로 mock 데이터를 만들어 화면을 완성하고, 백엔드는 동일한 모양으로 실제 테이블/컬럼을 채운다. 양쪽이 같은 계약을 보고 작업하면, 추후 mock을 실제 쿼리로 교체할 때 화면 코드를 거의 수정하지 않아도 된다.

본 문서는 기존 확정 스키마(`supabase/migrations/`)를 기준으로 **이미 있는 필드**와 **신규로 추가해야 하는 필드/테이블**을 명확히 구분한다. 신규 항목은 🆕로 표시한다.

참고가 된 목업/명세서(별도 브랜치 `feature/dashboard-ui`에서 제작)는 전체적인 레이아웃과 컨셉(3분할 그리드, Fleet Status / 3D 맵 / Analytics & Logs) 참고용으로만 사용했으며, 그 문서에 적힌 세부 수치나 텍스트는 본 계약서의 근거가 아니다.

---

## 2. 좌측 사이드바 — 로봇 플릿 상태 (Fleet Status)

**데이터 소스:** `robots` 테이블 (기존 테이블에 컬럼 추가)

| 필드 | 타입 | 상태 | 설명 |
|---|---|---|---|
| `id` | UUID | 기존 | 로봇 식별자 |
| `name` | VARCHAR(100) | 기존 | 표시 이름 (예: `"Wheeled-01"`). 친근한 별도 ID(RP-01 등)는 도입하지 않으며, 종류+번호 조합으로 충분하다. |
| `platform` | VARCHAR(20) | 기존 | `wheeled` \| `legged` |
| `status` | VARCHAR(20) | 🆕 | 로봇 상태 enum (2.1 참조) |
| `battery_pct` | FLOAT | 🆕 | 0.0 ~ 100.0 (%) |
| `current_speed_mps` | FLOAT | 🆕 | 현재 주행 속도 (m/s) |
| `current_mission_id` | UUID, nullable | 🆕 | 진행 중인 임무 FK → `missions.id`. 없으면 NULL |

### 2.1 로봇 상태 enum (`robots.status`)

| 값 | 배지 색(참고) | 의미 |
|---|---|---|
| `Idle` | 회색 | 거점 내 대기, 임무 없음 |
| `Charging` | 녹색 | 충전소(Node_Station)에서 충전 중 |
| `Delivery` | 주황색 | Pickup → Destination 배달 주행 중 |
| `Exploring` | 하늘색 | Raycast 탐색 모드 주행 중 |
| `Returning` | 보라색 | 임무 완료 후 거점으로 복귀 중 |

> Unity가 이 컬럼들을 주기적으로 갱신해야 한다. 기존 Phase 4 피드백 경로(구간 완료 시 1회 보고)와는 별도로, 상태 변경 시점마다(또는 일정 주기로) 경량 갱신 경로가 필요하다. 대시보드는 Supabase에서 읽기만 한다.

---

## 3. 중앙 상단 툴바 — 선택 로봇 텔레메트리

**데이터 소스:** `robots` (2장에서 추가한 컬럼) + `missions` 테이블(🆕, 4.2 참조)

| 필드 | 소스 | 설명 |
|---|---|---|
| `battery_pct` | `robots.battery_pct` | 배터리 게이지 (%) |
| `current_speed_mps` | `robots.current_speed_mps` | 현재 속도 (m/s) |
| `mission_elapsed_sec` | `missions.started_at` 기준 경과 시간 | 화면에서 `now() - started_at`으로 계산 |
| `mission_cost` | `missions.accumulated_cost` | 누적 비용 |

맵 컨트롤 버튼(Clear Path, Zoom Fit, Map Visibility 토글)은 순수 프론트엔드 상태이며 백엔드 연동이 필요 없다. Refresh Voxels는 버튼 클릭 시 기존 조회 쿼리를 재실행하는 것으로 충분하다. Set Goal 버튼은 이번 범위에서 제외한다.

---

## 4. 중앙 — 3D 복셀 맵

### 4.1 정적 맵 구조 + 탐색 상태 (Fog of War)

**데이터 소스:** `scene_dump.json`(정적 지형 구조, 기존) + `nodes` / `discovered_nodes`(기존)

| 필드 | 소스 | 상태 | 설명 |
|---|---|---|---|
| `id` | `scene_dump.tiles[].id` | 기존 | 타일 식별자 |
| `tag` | `scene_dump.tiles[].tag` | 기존 | 지형 유형(`Path_Stair` 등 → 줄무늬 패턴 적용) |
| `position` | `scene_dump.tiles[].position` | 기존 | x, y, z 좌표 |
| `size` | `scene_dump.tiles[].size` | 기존 | 타일 크기 |
| `node_type` | `nodes.node_type` | 기존 | `BASE` \| `DISCOVERED` — Fog of War 표시 여부 판정에 사용 |
| `confidence_score` | `discovered_nodes.confidence_score` | 기존 | 탐색 신뢰도. Temporal Fading(오래된 탐색일수록 어둡게) 연출에 활용 |

> Fog of War(미탐색 영역 가림, 탐색한 만큼 점진 공개)는 `node_type`/`confidence_score`로 구현 가능하다. 단, 현재 `push_feedback.py`가 `DISCOVERY` 타입 페이로드를 처리하지 않고 무시하므로, 탐색 데이터가 `discovered_nodes`에 실제로 적재되도록 파이프라인을 먼저 연결해야 이 기능이 의미를 가진다.
>
> 목업이 언급한 "Octree 직렬화"는 `discovered_nodes.pcd_file_url`(기존 컬럼, 의미상 탐색 복셀 데이터 경로로 재정의됨)에 대응하는 후속 구현 과제이며, 본 계약서 범위에서는 다루지 않는다.

### 4.2 경로 오버레이

| 필드 | 소스 | 설명 |
|---|---|---|
| `path_node_ids` | A* 결과 (Python 계산, 매 요청 시 산출) | 현재 선택된 로봇의 최적 경로 노드 목록. 저장하지 않고 화면 요청 시점에 계산 |

> 화면에는 현재 추적 중인 로봇 1대의 경로만 표시한다(다중 차량 경로 중첩 표시 안 함).

### 4.3 로봇 위치 마커 (선택 사항)

맵 위에 로봇의 실시간 위치를 마커로 표시하려면 `robots` 테이블에 `position_x`, `position_y`, `position_z` 컬럼 추가가 필요하다. 이는 2장 상태 갱신 경로에 포함해 함께 설계한다.

---

## 5. 우측 사이드바 — 통계 및 미션 로그 (Analytics & Logs)

### 5.1 플릿 작업 비중 차트 (Fleet Task Breakdown)

**데이터 소스:** `robots.status` 집계

```text
SELECT status, COUNT(*) FROM robots GROUP BY status;
```

결과를 아래 형태의 딕셔너리로 받아 바 차트를 그린다.

```json
{ "Idle": 2, "Charging": 2, "Delivery": 2, "Exploring": 2, "Returning": 1 }
```

### 5.2 임무 테이블 — `missions` (🆕 신규 테이블)

기존 `mission_logs`는 "구간 이동 완료 후의 L/S/E 성적표"이며, 대시보드가 보여줄 "임무 진행 현황"과는 별개 개념이다. 신규 테이블 `missions`를 도입한다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | UUID | 임무 식별자 |
| `robot_id` | UUID, FK → `robots.id` | 수행 로봇 |
| `mission_type` | VARCHAR(20) | `Delivery` \| `Exploration` |
| `status` | VARCHAR(20) | 임무 상태 enum (5.3 참조) |
| `from_node_id` | UUID, FK → `nodes.id` | 출발 노드 |
| `to_node_id` | UUID, FK → `nodes.id`, nullable | 목적지 노드 (Exploration은 NULL 가능) |
| `accumulated_cost` | FLOAT | 누적 비용 |
| `started_at` | TIMESTAMPTZ | 시작 시각 |
| `completed_at` | TIMESTAMPTZ, nullable | 완료 시각 |
| `acknowledged` | BOOLEAN, DEFAULT FALSE | 실패 임무에 대한 운영자 확인 여부 (5.4 알림과 연동) |

`missions` 한 건은 하나 이상의 `mission_logs` 구간 기록을 포함할 수 있다. 로그 테이블은 `missions`를 1차로 보여주고, 상세 보기에서 해당 임무에 속한 `mission_logs`(L/S/E)를 펼쳐 보이는 구조를 권장한다.

### 5.3 임무 상태 enum (`missions.status`)

| 값 | 의미 |
|---|---|
| `Pending` | 대기 — 목적지 배정됨, 아직 출발 전 |
| `Active` | 주행 중 |
| `Completed` | 정상 완료 |
| `Failed` | 실패 (회수, 경로 없음 등) |

### 5.4 알림(Notification)

| 필드 | 소스 | 설명 |
|---|---|---|
| `unread_alert_count` | `SELECT COUNT(*) FROM missions WHERE status='Failed' AND acknowledged=false` | 미확인 실패 임무 수. 1 이상이면 알림 아이콘에 빨간 닷 표시 |

> 회수(Recall) 명령 자체(운영자가 누르는 버튼)는 아키텍처 설계상 "로봇/미션 시스템 구축 이후(Step 3 이후)" 구현 예정이며, 본 계약서는 그 결과로 쌓일 데이터의 모양만 정의한다.

---

## 6. 시뮬레이터 온라인 상태 (Failsafe Banner)

**데이터 소스:** `simulator_status` 테이블 (기존, 변경 없음)

| 필드 | 타입 | 설명 |
|---|---|---|
| `is_online` | BOOLEAN | 시뮬레이터 온라인 여부 |
| `last_heartbeat` | TIMESTAMPTZ | 마지막 갱신 시각 |

표시 로직: `is_online == false` 이거나 `now() - last_heartbeat > 30초` 이면 상단에 적색 배너를 띄우고, 명령성 버튼(맵 컨트롤 등)을 비활성화한다. 과거 데이터 조회(읽기)는 항시 허용한다.

---

## 7. 배터리 모델 (간이 설계)

`Design_Report.md` 원안에서 효율성 지수(E)는 배터리 소모 기반으로 정의되었으나, 이후 `Unity_Simulator_Architecture.md`에서 "예상 이동시간 대비 실제 소요 시간 비율"로 변경되어 현재 구현은 배터리를 실측하지 않는다. 새로운 물리 시뮬레이션을 추가하는 대신, 기존에 계산되는 L/S/E 지표를 근사값으로 재활용하는 간이 모델을 둔다.

| 파라미터 | 값(안) | 설명 |
|---|---|---|
| `max_battery` | 100.0 | 완충 상태 기준값 |
| `drain_per_meter` | 지형별 차등 (예: 평지 0.02, 경사 0.05, 계단 0.08) | 이동 거리 1m당 소모량. L(부하율) 지표와 연동해 산출 가능 |
| `charge_rate` | 5.0 / sec | `Node_Station`에 정차 중일 때 초당 충전량 |
| `low_battery_threshold` | 15.0 | 이하로 내려가면 자동 귀환 트리거 (후속 과제) |

> 구체적인 소모 공식(거리 × 지형별 drain, 혹은 L 지표 기반 가중)은 구현 단계에서 확정한다. 본 계약서는 `robots.battery_pct` 필드가 존재하고 주기적으로 갱신된다는 사실만 보장한다.

---

## 8. UI 제작용 Mock 데이터 예시

아래 구조 그대로 mock 데이터를 만들어 화면을 먼저 완성한다. 필드명과 enum 값은 본 문서의 정의와 1:1 대응하므로, 추후 실제 Supabase 쿼리 결과로 교체할 때 화면 코드 변경을 최소화한다.

```python
# 로봇 목록 (좌측 사이드바) — robots 테이블 대응
MOCK_ROBOTS = [
    {
        "id": "r1", "name": "Wheeled-01", "platform": "wheeled",
        "status": "Delivery", "battery_pct": 72.0, "current_speed_mps": 0.5,
        "current_mission_id": "m2",
    },
    {
        "id": "r2", "name": "Wheeled-02", "platform": "wheeled",
        "status": "Idle", "battery_pct": 100.0, "current_speed_mps": 0.0,
        "current_mission_id": None,
    },
    {
        "id": "r3", "name": "Legged-01", "platform": "legged",
        "status": "Exploring", "battery_pct": 45.0, "current_speed_mps": 0.3,
        "current_mission_id": "m4",
    },
    # ... 총 9대 (Wheeled 5 / Legged 4)
]

# 플릿 작업 비중 (우측 사이드바 차트) — robots.status 집계 대응
MOCK_FLEET_BREAKDOWN = {
    "Idle": 2, "Charging": 2, "Delivery": 2, "Exploring": 2, "Returning": 1
}

# 임무 로그 (우측 사이드바 테이블) — missions 테이블 대응
MOCK_MISSIONS = [
    {
        "id": "m1", "robot_name": "Wheeled-01", "mission_type": "Delivery",
        "status": "Completed", "started_at": "2026-06-17T10:30:00Z",
        "completed_at": "2026-06-17T10:45:00Z", "accumulated_cost": 350.0,
    },
    {
        "id": "m2", "robot_name": "Legged-01", "mission_type": "Exploration",
        "status": "Active", "started_at": "2026-06-17T11:00:00Z",
        "completed_at": None, "accumulated_cost": 120.0,
    },
    {
        "id": "m3", "robot_name": "Wheeled-03", "mission_type": "Delivery",
        "status": "Failed", "started_at": "2026-06-17T09:00:00Z",
        "completed_at": "2026-06-17T09:12:00Z", "accumulated_cost": 0.0,
    },
]

# 시뮬레이터 온라인 상태 (상단 배너) — simulator_status 테이블 대응
MOCK_SIMULATOR_STATUS = {
    "is_online": True, "last_heartbeat": "2026-06-17T12:00:00Z"
}
```

---

## 9. 신규 스키마 변경 요약

본 계약서를 실제로 구현할 때 필요한 DB 변경 사항을 모아 정리한다(실행 순서는 구현 단계에서 결정).

- `robots` 테이블에 컬럼 추가: `status`, `battery_pct`, `current_speed_mps`, `current_mission_id` (+ 선택: `position_x/y/z`)
- 신규 테이블 `missions` 생성 (5.2 스키마 참조)
- `discovered_nodes` 적재 파이프라인 연결 (`push_feedback.py`의 `DISCOVERY` 타입 처리 추가)
- 회수(Recall) 관련 `mission_logs.status` 필드 추가는 별도 과제(아키텍처 9.1절)로, 본 계약서의 `missions.status`와는 별개로 다룬다.

---

## 10. 범위 제외 항목 (참고 목업에서 제외 결정된 것)

- 로봇별 친근한 ID 체계(RP-01~09 같은 별도 코드 부여) — 종류+번호로 충분, 도입하지 않음
- Set Goal 버튼(웹에서 직접 목적지 클릭 지정) — 이번 범위에서 제외
- 동적 가변 해상도 Octree 복셀 압축, 실시간 보행 애니메이션, 바이너리 옥트리 스트리밍 — 후속 과제, 본 계약서 범위 아님

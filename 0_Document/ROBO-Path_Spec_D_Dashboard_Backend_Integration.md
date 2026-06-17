# [Spec D] 대시보드 백엔드 연결 명세서

> 작성일: 2026-06-17
> 선행 의존성: **Spec A, Spec B가 먼저 끝나 있어야 의미 있는 데이터가 보인다.**
> 목적: `src/presentation/dashboard/mock_data.py`의 4개 함수를 실제 Supabase 쿼리로 교체한다.

---

## 0. 선행 확인 사항 — 지금 실행하면 빈 화면이 나온다

`mock_data.py`를 직접 확인한 결과, 함수는 정확히 4개뿐이다.

```python
def get_robots(): return MOCK_ROBOTS
def get_fleet_breakdown(): return MOCK_FLEET_BREAKDOWN
def get_missions(): return MOCK_MISSIONS
def get_simulator_status(): return MOCK_SIMULATOR_STATUS
```

`app.py`는 이 함수들을 `from mock_data import get_robots, get_fleet_breakdown, get_missions, get_simulator_status`로 직접 import해 사용한다. 본 명세서는 이 4개 함수의 **내부 구현만** Supabase 쿼리로 바꾸고, `app.py`의 호출부는 건드리지 않는 것을 목표로 한다(애초에 이 교체가 쉽도록 설계되었음을 실제 코드로 확인했다).

**단, 다음이 선행되지 않으면 이 작업의 결과 화면이 비어 있거나 의미 없다.**
- `robots.status`/`battery_pct`/`current_speed_mps`/`current_mission_id` 컬럼 — Spec B 1단계
- `missions` 테이블 자체 — Spec A 4단계
- `robots` 테이블에 9개 row 시드 — Spec B 1단계

이 셋이 끝나기 전에 본 명세서를 실행하면, 쿼리는 정상 동작하지만 결과가 0행이거나 컬럼이 없어 에러가 난다. **Spec A, B 완료 후 진행한다.**

---

## 1. 단계 1 — `get_robots()` 교체

**대상 파일:** `src/presentation/dashboard/mock_data.py`

```python
def get_robots():
    from src.infrastructure.database.client import get_supabase_client
    client = get_supabase_client()
    response = client.table("robots").select(
        "id, name, platform, status, battery_pct, current_speed_mps, current_mission_id"
    ).execute()
    return response.data
```

- 읽기 전용 조회이므로 `get_supabase_client()`(publishable 키, 기존 RLS가 SELECT를 허용하는 클라이언트)를 사용한다. `get_supabase_admin_client()`(Phase 4에서 만든 service_role 클라이언트, 쓰기 전용 작업용)는 여기서 쓰지 않는다.
- 반환되는 딕셔너리의 키 이름이 `MOCK_ROBOTS`의 키(`id`, `name`, `platform`, `status`, `battery_pct`, `current_speed_mps`, `current_mission_id`)와 정확히 일치하는지 확인한다(Data Contract에서 이미 1:1 대응되도록 설계했으므로 컬럼명을 그대로 select하면 일치해야 한다).
- **검증:** Streamlit 앱을 실행해 좌측 Fleet Status에 실제 9대(Spec B에서 시드한 이름)가 표시되는지 직접 화면으로 확인하고 스크린샷 또는 설명으로 보고한다.

---

## 2. 단계 2 — `get_fleet_breakdown()` 교체

```python
def get_fleet_breakdown():
    from src.infrastructure.database.client import get_supabase_client
    client = get_supabase_client()
    response = client.table("robots").select("status").execute()
    counts = {}
    for row in response.data:
        s = row["status"]
        counts[s] = counts.get(s, 0) + 1
    return counts
```

- Supabase Python 클라이언트는 `GROUP BY`를 직접 지원하지 않으므로(PostgREST 제약), 전체 행을 가져와 Python에서 집계한다. 로봇 수가 9대로 적으므로 성능 문제는 없다.
- **검증:** 우측 Fleet Task Breakdown 차트가 실제 분포(예: 시드 직후라면 전부 Idle 9)로 그려지는지 확인한다.

---

## 3. 단계 3 — `get_missions()` 교체

```python
def get_missions():
    from src.infrastructure.database.client import get_supabase_client
    client = get_supabase_client()
    response = client.table("missions").select(
        "id, robot_id, mission_type, status, started_at, completed_at, accumulated_cost"
    ).order("started_at", desc=True).limit(50).execute()
    return response.data
```

- `MOCK_MISSIONS`는 `robot_name`(문자열) 키를 쓰는데, 실제 `missions` 테이블은 `robot_id`(UUID)만 가진다(Spec A 4단계 스키마 확인). 화면 코드(`app.py`)가 `m['robot_name']`을 참조하므로, 둘 중 하나로 처리한다.
  - (권장) Supabase 쿼리에서 `robots` 테이블과 조인해 이름을 가져온다: `.select("id, mission_type, status, started_at, completed_at, accumulated_cost, robots(name)")` 형태로 PostgREST의 foreign table 조회를 사용하고, 반환된 `row["robots"]["name"]`을 `robot_name` 키로 재매핑해서 돌려준다.
  - 조인이 여의치 않으면 `get_robots()` 결과로 `id→name` 매핑 딕셔너리를 만들어 후처리한다.
- **검증:** 우측 Mission Logs 리스트가 실제 데이터(Spec A 통합 검증에서 만든 임무 포함)로 표시되는지 확인한다.

---

## 4. 단계 4 — `get_simulator_status()` 교체

```python
def get_simulator_status():
    from src.infrastructure.database.client import get_supabase_client
    client = get_supabase_client()
    response = client.table("simulator_status").select("is_online, last_heartbeat").order("updated_at", desc=True).limit(1).execute()
    if response.data:
        return response.data[0]
    return {"is_online": False, "last_heartbeat": None}
```

- `simulator_status` 테이블은 기존 Heartbeat 페일세이프 설계(변경 없음, 직접 확인됨)를 그대로 쓴다.
- row가 비어 있을 경우(시뮬레이터가 한 번도 하트비트를 보낸 적 없음)를 대비해 기본값을 둔다.
- **검증:** Mac Mini의 시뮬레이터를 끈 상태/켠 상태 양쪽에서 상단 배너가 올바르게(`is_online` 값에 따라) 바뀌는지 직접 확인한다.

---

## 5. 통합 검증

1. Spec A, B, C가 모두 끝난 상태에서 Streamlit 앱을 실행한다.
2. 좌측에 9대의 실제 로봇이 보이고, 임무를 배정한 로봇이 `status="Delivery"`로 바뀌며 배터리가 줄어드는 것이 화면에 실시간(또는 새로고침 시)으로 반영되는지 확인한다.
3. 우측 Mission Logs에 실제 완료/진행 임무가 보이는지 확인한다.
4. `mock_data.py`라는 파일명이 더 이상 실제 동작과 맞지 않으므로, 이 시점에 파일명을 `data_access.py` 등으로 변경할지 여부를 결정한다(선택, 강제하지 않음 — 변경 시 `app.py`의 import 경로도 함께 수정).

---

## 부록 — 본 명세서가 손대지 않는 것

- `app.py`의 화면 레이아웃, 스크롤/토글 로직(이미 완성되어 검증됨) — 변경하지 않는다.
- 3D 맵 영역의 Mock Plotly 시각화를 실제 `scene_dump.json` 기반으로 바꾸는 작업, `is_discovered`(Spec C) 기반 Fog of War 렌더링 — 별도 후속 작업으로 분리한다(본 명세서는 좌/우 패널의 표 형태 데이터 연결까지만 다룬다).

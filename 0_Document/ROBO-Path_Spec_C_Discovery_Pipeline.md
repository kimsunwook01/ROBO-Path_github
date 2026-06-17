# [Spec C] Discovery 텔레메트리 파이프라인 복구 명세서

> 작성일: 2026-06-17
> 목적: 로봇의 Raycast 탐색 결과가 실제로 Supabase에 적재되도록 끊긴 경로를 연결한다.

---

## 0. 선행 확인 사항 — 단순 "분기 추가"로 끝나지 않는 두 가지 설계 문제

다음 두 가지는 실제 코드를 직접 읽고 확인한 사실이며, 이번 명세서가 해결해야 하는 핵심 문제다. 단순히 `push_feedback.py`에 `DISCOVERY` 분기 하나를 추가하는 것으로는 의미 있는 동작이 나오지 않는다.

### 0.1 `node_type` enum에 "미탐색" 상태가 없다

`src/domain/models/node.py`:
```python
node_type: str = Field(..., pattern="^(BASE|DISCOVERED)$")
```

`map_import_service.py`는 모든 일반 지형 타일을 **임포트 시점에 이미 `node_type="BASE"`**로 DB에 넣는다(`Node(..., node_type="BASE", ...)`, 71번 줄 근방). 즉 Fog of War(미탐색은 가려지고, 로봇이 보면 드러난다)를 구현하려는 의도와 달리, **모든 타일이 이미 "확정된 BASE 노드"로 존재하여 "발견 전/후" 상태 구분이 DB 단에서 표현되지 않는다.** `DISCOVERED`는 모델 주석상 "로봇이 자율적으로 발견한 탐험 노드"를 위한 별도 타입이지만, 기존 타일이 발견되어 `DISCOVERED`로 "전환"되는 것이 아니라 완전히 별개의 새 레코드(별개 테이블 `discovered_nodes`, 별개 `node_type`)로 설계되어 있다.

**해결 방향(이번 명세서가 채택하는 해석):** "타일을 BASE→DISCOVERED로 전환한다"는 `Unity_Simulator_Architecture.md` 3.1절의 표현을 글자 그대로 구현하지 않는다. 대신, 로봇이 Ray로 어떤 지점을 비추면 그 지점에 대응하는 **이미 존재하는 일반 타일(node_type="BASE")에 한해, 별도의 "탐색 여부" 신호를 덧붙이는 방식**으로 구현한다. 구체적으로는 1장에서 정의한다. (DB 스키마 변경 없이, `nodes` 테이블에 컬럼을 하나 추가하는 가장 단순한 방법을 택한다 — 새로운 `DISCOVERED` 타입의 중복 레코드를 만들지 않는다.)

### 0.2 `RaycastScanner`가 찾는 대상이 거점(이미 알려진 곳)이다

`Unity/.../Robot/RaycastScanner.cs`의 `PerformScan()`:
```csharp
if (col.gameObject.name.StartsWith("Node_") || col.CompareTag("Node_Station"))
{
    if (telemetrySink != null) telemetrySink.EmitDiscovery(col.transform.position);
}
```

이 조건은 거점(Station/Pickup/Destination) 오브젝트만 골라낸다. 그런데 사용자가 이미 확정한 바와 같이 거점은 "탐색 없이도 처음부터 주어지는 알려진 목적지"이므로, 이를 "발견"으로 처리하는 것은 설계 의도와 맞지 않는다. **정작 발견되어야 할 대상은 일반 지형 타일(`Terrain_Flat`, `Path_Stair` 등)이다.**

**해결 방향:** `PerformScan()`의 필터 조건을 거점이 아니라 **일반 지형 타일**을 잡도록 바꾼다(태그가 `Node_Station`/`Node_Pickup`/`Node_Destination`이 *아닌* 콜라이더). 1장에서 구체화한다.

---

## 1. 단계 1 — 데이터 모델 보강: `nodes.is_discovered` 컬럼

**대상 파일:** 신규 마이그레이션, `src/domain/models/node.py`

기존 `node_type` enum과 `discovered_nodes` 별도 테이블 구조를 건드리지 않고, `nodes` 테이블에 컬럼을 하나 추가하는 최소 변경으로 "탐색 여부"를 표현한다.

```sql
ALTER TABLE nodes ADD COLUMN is_discovered BOOLEAN DEFAULT FALSE;
ALTER TABLE nodes ADD COLUMN discovered_at TIMESTAMPTZ;
ALTER TABLE nodes ADD COLUMN discovery_confidence FLOAT DEFAULT 0.0 CHECK (discovery_confidence >= 0.0 AND discovery_confidence <= 1.0);
```

- `Node` Pydantic 모델(`node.py`)에 `is_discovered: bool = False`, `discovered_at: Optional[datetime] = None`, `discovery_confidence: float = 0.0` 필드를 추가한다.
- 거점(`BaseLocation`)은 임포트 시점에 `is_discovered=True`로 고정한다(처음부터 알려진 주소지이므로). 일반 타일(`Node`)은 임포트 시점에 `is_discovered=False`로 시작한다(아직 탐색되지 않음).
- 기존 `discovered_nodes` 테이블(`confidence_score`, `visit_count`, `is_verified`, `pcd_file_url`)은 그대로 두되, 이번 1차 구현에서는 사용하지 않는다(후속 과제 — 부록 참조).

**검증:** 마이그레이션 적용 후 `map_import_service.py`를 재실행해, `SELECT node_type, is_discovered, COUNT(*) FROM nodes GROUP BY node_type, is_discovered;` 결과가 "BASE(거점) → is_discovered=true 34건, BASE(일반 타일) → is_discovered=false 나머지 전부"로 나오는지 직접 확인한다.

---

## 2. 단계 2 — `RaycastScanner` 필터 조건 수정

**대상 파일:** `Unity/.../Robot/RaycastScanner.cs`

1. `PerformScan()`의 필터를 다음으로 바꾼다 — 거점 태그가 아닌 콜라이더를 발견 대상으로 잡는다.
   ```csharp
   bool isStationTag = col.CompareTag("Node_Station") || col.CompareTag("Node_Pickup") || col.CompareTag("Node_Destination");
   if (!isStationTag)
   {
       if (telemetrySink != null) telemetrySink.EmitDiscovery(col.transform.position);
   }
   ```
2. `EmitDiscovery(Vector3 nodePos)`만으로는 "어떤 타일인지"를 Python이 알 방법이 없다(좌표만 전달됨). 좌표 기반으로 기존 타일과 매칭해야 하므로, 좌표 정밀도를 보존하기 위해 `col.transform.position`(타일의 정확한 중심 좌표)을 그대로 쓰는 현재 방식을 유지한다(타일은 10m 그리드 고정 위치이므로 좌표 매칭이 가능하다 — 3장에서 처리).
3. **검증:** Unity 플레이 모드에서 로봇을 거점이 아닌 일반 타일 근처로 이동시키고, 콘솔에 `EmitDiscovery` 호출이 거점이 아닌 위치에서 발생하는지 직접 확인한다(`SubprocessTelemetrySink`가 호출하는 서브프로세스 실행 로그로 확인 가능).

---

## 3. 단계 3 — `push_feedback.py`에 DISCOVERY 분기 추가

**대상 파일:** `src/infrastructure/bridge/push_feedback.py`

현재 코드:
```python
if data.get("type") != "FEEDBACK":
    logger.info(f"Ignored non-feedback payload type: {data.get('type')}")
    sys.exit(0)
```

이 부분을 분기 처리로 바꾼다.

1. `type == "DISCOVERY"`이면 `data`에서 `x`, `y`, `z`를 읽는다.
2. **좌표 매칭:** `NodeRepository`에 좌표 기반 조회 메서드가 없으므로(`get_node_by_id`/`get_all_nodes`/`upsert_nodes`만 존재, 직접 확인됨) 추가가 필요하다. 가장 단순한 방법은 `get_all_nodes()`로 전체를 가져와 파이썬에서 유클리드 거리 최소값을 찾는 것이지만, 노드가 수천 개(기존 확인: 3194개)라 매 Discovery 호출마다 전체 스캔은 비효율적이다. `NodeRepository`에 `get_node_near(x, y, z, tolerance) -> Optional[Node]` 메서드를 추가하고, Supabase 쿼리로 좌표 범위(`x BETWEEN ... AND ...`) 필터를 거는 방식을 권장한다(타일이 10m 그리드라 tolerance는 1m 이내로 충분히 좁게 잡을 수 있다).
3. 매칭된 노드를 찾으면 `is_discovered=False`였던 경우에만 `is_discovered=True`, `discovered_at=now()`, `discovery_confidence`를 갱신한다(초기 발견 시 낮은 값, 예: 0.6 — 정확한 공식은 명세서 범위 밖이며 구현 시 단순 고정값으로 시작해도 된다).
4. 매칭되는 노드가 없으면(좌표가 어긋난 경우) 에러 없이 로그만 남기고 종료한다(기존 엣지 매칭 실패 시 폴백 패턴과 동일하게).
5. **검증:** 합성 좌표로 `push_feedback.py`를 직접 실행해(Phase 4 검증 때와 동일한 방식), `type=DISCOVERY` 페이로드가 실제로 `nodes.is_discovered`를 갱신하는지 Supabase 조회로 확인한다. 좌표가 기존 타일과 멀리 떨어진 경우(매칭 실패)도 별도로 실행해, 에러 없이 종료되는지 확인한다.

---

## 4. 통합 검증

1. Unity 플레이 모드에서 탐색(Exploring) 중인 로봇이 일반 타일 근처를 지나가게 한다.
2. 일정 시간 후 Supabase에서 `SELECT COUNT(*) FROM nodes WHERE is_discovered = true AND node_type = 'BASE';`를 실행해, 거점 34개보다 많은 수(일반 타일도 발견되어 포함)가 나오는지 확인한다.
3. 로봇이 가지 않은 영역의 타일은 여전히 `is_discovered = false`로 남아있는지 함께 확인한다(이게 Fog of War의 핵심 — 다녀온 곳만 true가 되어야 한다).

---

## 부록 — 이번 범위에서 제외한 것

- `discovered_nodes` 테이블(`confidence_score`/`visit_count`/`is_verified`/`pcd_file_url`)을 활용한 정교한 신뢰도 누적 모델: 후속 과제.
- Octree 직렬화(`pcd_file_url`)를 통한 복셀 압축 저장: 후속 과제(Migration Decision Report 3.2절에 이미 "향후 구현"으로 명시되어 있음).
- 대시보드에서 `is_discovered`를 Fog of War 렌더링에 실제로 사용하는 작업은 Spec D에서 다룬다.

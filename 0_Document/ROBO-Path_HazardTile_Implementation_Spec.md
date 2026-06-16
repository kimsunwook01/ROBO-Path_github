# Phase 3c: HazardTileController 구현 명세서

> 작성일: 2026-06-17  
> 대상 파일: `Assets/Scripts/Tile/HazardTileController.cs`  
> 관련 문서: `ROBO-Path_Map_Design_Specification.md § 3.6`

---

## 1. 목적

`Tile_Hazard` 프리팹에 활성/비활성 상태 전환 기능을 부여한다.
- **비활성(기본):** MeshRenderer 꺼짐 → 맵에서 보이지 않음
- **활성:** MeshRenderer 켜짐 → 형광색 타일 시각화, 향후 A* 비용 증가 연동

Phase 4 WebSocket 서버 구현 시 `SetHazardActive(bool)` API 한 줄 호출로 바로 연결되도록 설계한다.

---

## 2. 사전 검증 (프로젝트 현황 대조)

| 검증 항목 | 확인 결과 |
|-----------|-----------|
| `Tile_Hazard.prefab` 컴포넌트 구성 | Transform + MeshFilter + MeshRenderer + BoxCollider. MonoBehaviour 없음 → 스크립트 부착 필요 |
| `Assets/Scripts/Tile/` 폴더 존재 여부 | **없음** → 신규 생성 필요 |
| 기존 asmdef (`ROBOPath.Robot.asmdef`) | `autoReferenced: true` → 같은 어셈블리에 넣으면 별도 asmdef 불필요 |
| EditMode 테스트 asmdef | `ROBOPath.Robot` 참조 중 → Tile 스크립트를 Robot asmdef에 포함하면 EditMode 테스트에서 즉시 사용 가능 |
| PlayMode asmdef | `ROBOPath.Robot` 참조 중 → 동일 |
| NavMesh 재베이크 필요 여부 | MeshRenderer만 토글하므로 **불필요** |
| Collider 유지 여부 | BoxCollider `m_Enabled: 1` → 코드에서 건드리지 않음으로써 유지 |

> **결론:** `Assets/Scripts/Tile/` 폴더를 새로 만들고 그 안에 스크립트를 작성한다.  
> asmdef는 신규 생성하지 않고, `ROBOPath.Robot`의 `autoReferenced: true` 속성을 활용한다 (Tile 폴더는 Robot asmdef 범위 밖이므로 별도 asmdef가 필요하다 — 3단계 참조).

---

## 3. 구현 단계 (세분화)

총 **6단계**. AI 수행과 사용자(Unity 에디터) 수행 구분 명시.

---

### STEP 1 — `HazardTileController.cs` 작성 ✏️ **[AI 수행]**

**경로:** `Assets/Scripts/Tile/HazardTileController.cs`  
**내용:** 아래 스펙 그대로 작성.

```csharp
using UnityEngine;

namespace ROBOPath.Tile
{
    /// <summary>
    /// Tile_Hazard 프리팹의 활성/비활성 상태를 제어한다.
    /// 비활성 시 MeshRenderer를 꺼서 맵에서 보이지 않게 하고,
    /// Collider는 유지하여 NavMesh 통행 및 RaycastScanner 감지를 보존한다.
    /// 외부(WebSocket, 타이머)에서 SetHazardActive(bool)을 호출하여 제어한다.
    /// </summary>
    public class HazardTileController : MonoBehaviour
    {
        [Header("Initial State")]
        [Tooltip("Play 시작 시 활성화 여부. 기본값 false(비표시).")]
        public bool startActive = false;

        private MeshRenderer meshRenderer;
        private bool isActive;

        void Awake()
        {
            meshRenderer = GetComponent<MeshRenderer>();
        }

        void Start()
        {
            SetHazardActive(startActive);
        }

        /// <summary>
        /// 장애물 타일의 활성/비활성 상태를 전환한다.
        /// Phase 4 WebSocket 수신 시 이 메서드를 호출한다.
        /// </summary>
        public void SetHazardActive(bool active)
        {
            isActive = active;
            if (meshRenderer != null)
                meshRenderer.enabled = active;
        }

        /// <summary>현재 활성 상태를 반환한다.</summary>
        public bool IsActive => isActive;
    }
}
```

**검증 포인트:**
- `GetComponent<MeshRenderer>()` — 프리팹에 MeshRenderer 확인 완료 (line 46)
- `BoxCollider`는 코드에서 참조하지 않으므로 항상 유지됨
- namespace `ROBOPath.Tile` — 기존 `ROBOPath.Robot`과 구분

---

### STEP 2 — asmdef 작성 ✏️ **[AI 수행]**

**경로:** `Assets/Scripts/Tile/ROBOPath.Tile.asmdef`

`Tile` 폴더는 `Robot` asmdef의 루트(`Assets/Scripts/Robot/`) 밖에 있으므로 별도 asmdef 필요.  
EditMode 테스트에서 참조할 수 있도록 `autoReferenced: true` 설정.

```json
{
    "name": "ROBOPath.Tile",
    "rootNamespace": "",
    "references": [],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": true,
    "defineConstraints": [],
    "versionDefines": [],
    "noEngineReferences": false
}
```

---

### STEP 3 — EditMode asmdef에 참조 추가 ✏️ **[AI 수행]**

**경로:** `Assets/Scripts/Tests/EditMode/ROBOPath.Tests.EditMode.asmdef`

`ROBOPath.Tile` 어셈블리를 테스트에서 사용할 수 있도록 참조 추가.

```json
"references": [
    "UnityEngine.TestRunner",
    "UnityEditor.TestRunner",
    "ROBOPath.Robot",
    "ROBOPath.Tile"
]
```

---

### STEP 4 — EditMode 테스트 작성 ✏️ **[AI 수행]**

**경로:** `Assets/Scripts/Tests/EditMode/HazardTileControllerTests.cs`

```csharp
// 검증 대상: startActive=false 시 MeshRenderer.enabled==false
// 검증 대상: SetHazardActive(true) 후 MeshRenderer.enabled==true
// 검증 대상: SetHazardActive(false) 후 MeshRenderer.enabled==false
// 검증 대상: IsActive 프로퍼티가 상태와 일치
```

---

### STEP 5 — 프리팹에 컴포넌트 부착 🖱️ **[사용자 수행 — Unity 에디터]**

> **이 단계는 Unity 에디터 GUI에서 직접 수행하는 것이 정확하고 빠릅니다.**

**수행 절차:**

1. Unity 에디터 실행 → STEP 1~4 스크립트 컴파일 완료 대기 (Console 오류 없음 확인)
2. `Project` 창 → `Assets/Prefabs/Tile_Hazard.prefab` 더블클릭 (Prefab 편집 모드 진입)
3. `Inspector` 창 → `Add Component` 버튼 클릭
4. 검색창에 `HazardTileController` 입력 → 선택
5. 추가된 컴포넌트의 `Start Active` 체크박스가 **꺼져 있음(false)** 확인
6. 상단 `Save` 버튼(또는 Ctrl+S)으로 프리팹 저장
7. Prefab 편집 모드 종료

**확인 방법:**
- 씬에 배치된 `Tile_Hazard` 오브젝트를 Play하면 MeshRenderer가 꺼져 보이지 않아야 한다.

---

### STEP 6 — 테스트 실행 및 커밋 ✏️ **[AI 수행]**

1. Unity Test Runner (Window → General → Test Runner) 열기
2. `EditMode` 탭 → `HazardTileControllerTests` 포함 전체 Run All → **Failed 0** 확인
3. `git add -A` → `git commit`

---

## 4. 파일 변경 요약

| 파일 | 변경 유형 | 수행 주체 |
|------|-----------|-----------|
| `Assets/Scripts/Tile/HazardTileController.cs` | **신규** | AI |
| `Assets/Scripts/Tile/ROBOPath.Tile.asmdef` | **신규** | AI |
| `Assets/Scripts/Tests/EditMode/ROBOPath.Tests.EditMode.asmdef` | **수정** (참조 추가) | AI |
| `Assets/Scripts/Tests/EditMode/HazardTileControllerTests.cs` | **신규** | AI |
| `Assets/Prefabs/Tile_Hazard.prefab` | **수정** (컴포넌트 부착) | **사용자 (Unity GUI)** |

---

## 5. 제약 및 금지 사항

- `BoxCollider` 활성화 상태 변경 **금지** (NavMesh 및 RaycastScanner 기능 유지 필수)
- NavMesh **재베이크 불필요** (물리 영역 변경 없음)
- 기존 13개 테스트 **Failed 0 유지** 필수
- A* 비용 연동 로직은 **Phase 4에서 구현** (이번 단계 범위 외)
- 씬 파일(`.unity`) 직접 수정 **금지**

---

## 6. 향후 연동 지점 (Phase 4)

```
WebSocket 수신 메시지: { "type": "hazard", "id": "Tile_Hazard_x3_z-5", "active": true }
    → 씬에서 해당 오브젝트를 FindObjectsByTag("Tile_Hazard")로 탐색
    → GetComponent<HazardTileController>().SetHazardActive(true) 호출
```

이 단계에서 `HazardTileController`는 수정 없이 그대로 사용된다.

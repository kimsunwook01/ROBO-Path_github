# ROBO-Path 맵 에디터 도구 구현 상세 설계 (Map Editor Implementation Specification)

## 1. 구조 설계 (Architecture Design)

### 1.1 도구 기본
- **타입:** Unity 에디터 확장 툴 (런타임 게임 아님). `EditorWindow` 상속
- **메뉴 경로:** `[MenuItem("ROBO-Path/Map Editor")]`
- **관리 루트:** 배치된 모든 블록은 `MapRoot` (없으면 자동 생성) 아래에 위치한다.
- **기존 파일 무수정 원칙:** 본 툴을 위해 기존 `SceneDumpExporter`, 프리팹, 기존 씬 등을 절대 수정하지 않는다. (오직 신규 파일 추가)

### 1.2 블록 프리팹 (확장성 핵심)
- **프리팹 로드 방식:** `Assets/Prefabs/` 폴더를 스캔(`AssetDatabase.FindAssets`)하여 프리팹 목록을 동적으로 구성한다. 프리팹 이름, 개수, 태그를 코드에 절대 하드코딩하지 않는다.
- **새로고침 기능:** 툴 창의 '새로고침' 버튼 클릭 시 폴더를 다시 스캔하여 팔레트와 필터를 갱신한다. (새로운 프리팹이 추가될 경우 코드 수정 없이 즉각 반영됨)
- **블록 규격:** Footprint 10m × 10m 고정. 프리팹 이름에 포함된 숫자(2/4/6/8/10)가 윗면의 높이가 된다. 기준점(Origin)은 밑면 `y=0` (이미 프리팹이 그렇게 제작되어 있음).

### 1.3 씬 데이터 소스화 (적층 높이 계산)
- 별도의 자료구조(배열 등)로 맵 상태를 캐싱/저장하지 않는다.
- **씬을 진실의 원천(Single Source of Truth)으로** 삼아, `MapRoot` 하위 블록들을 직접 순회하며 동일한 `(gx, gz)` 격자에 있는 블록들의 윗면 높이 최댓값을 실시간으로 찾는다.
- 블록 높이는 `Renderer.bounds.max.y` 또는 프리팹 이름의 숫자를 기반으로 추출한다.

### 1.4 중력 없는 마인크래프트 방식
- **공중 배치 지원:** 하위 블록을 삭제해도 위의 블록은 추락하지 않는다 (중력/Rigidbody 미사용).
- 순수 허공 배치 전용 툴은 제공하지 않고, 하단부터 적층 후 필요없는 하단 블록을 우클릭으로 지우는 방식으로 공중 구조물을 만든다.

### 1.5 태그 및 덤프 연계
- 태그 자동 부여: `PrefabUtility.InstantiatePrefab` 사용 시 원본 프리팹의 태그가 그대로 복제되므로 별도의 태그 부여 로직이 필요 없다.
- 기존 덤프 도구(`SceneDumpExporter`)와 완벽 호환되며, 덤프 도구의 인접 판정, 높이, 회전 정보 추출이 그대로 작동한다.

---

## 2. 클래스 및 주요 메서드 구현 계획

### 2.1 파일: `Assets/Scripts/Debug/Editor/MapEditorWindow.cs`
- **역할:** 맵 에디터 UI 및 코어 배치 로직 관리
- **주요 필드:**
  - `List<GameObject> loadedPrefabs`: 스캔된 프리팹 목록
  - `GameObject selectedPrefab`: 팔레트에서 현재 선택된 블록
  - `int currentRotationIndex`: 블록 회전 상태 (0=0도, 1=90도, 2=180도, 3=270도)
  - `bool isSelectMode`: 배치 모드 / 선택 모드 토글 상태
  - `HashSet<string> activeTagFilters`: 동적 태그 필터 상태 (체크된 태그들)
  
- **주요 메서드:**
  - `OnEnable()`: 윈도우 팝업 시 `RefreshPrefabs()` 실행 및 `SceneView.duringSceneGui += OnSceneGUI` 이벤트 구독.
  - `OnDisable()`: `SceneView.duringSceneGui -= OnSceneGUI` 이벤트 구독 해제.
  - `RefreshPrefabs()`: `AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/Prefabs" })`를 사용하여 프리팹 로드. 프리팹에 할당된 모든 태그를 수집하여 필터용 태그 세트를 동적 갱신.
  - `OnGUI()`:
    - 모드 토글 버튼 (배치 / 선택).
    - 프리팹 스캔 새로고침 버튼.
    - 수집된 태그 기반의 동적 필터 체크박스 생성 (하드코딩 금지).
    - 필터링된 프리팹 목록을 팔레트로 표시 (이름 순 정렬, `AssetPreview.GetAssetPreview`를 활용한 썸네일 렌더링).
  - `OnSceneGUI(SceneView sceneView)`: 마우스 레이캐스팅, 격자 스냅 처리, Handles 미리보기 렌더링, 키보드/마우스 클릭 이벤트 처리.
  - `HandlePlacement(Vector3 gridPos)`:
    - 동일 격자의 최상단 높이를 찾아 `y`값 계산.
    - `PrefabUtility.InstantiatePrefab`을 통해 블록 생성 (`MapRoot` 하위).
    - `Undo.RegisterCreatedObjectUndo`로 생성 동작의 Undo 지원.
  - `HandleDeletion(Vector3 gridPos)`:
    - 레이캐스트에 맞은 블록(혹은 해당 칸의 최상단 블록) 탐색 후 `Undo.DestroyObjectImmediate` 실행.

---

## 3. 씬 뷰 입력 처리 구체화 (Scene GUI)

- **레이캐스트 및 격자 스냅:**
  - 마우스 위치에서 Ray를 발사하여 `y=0`의 수학적 평면(Plane)과 교차시킨다 (또는 기존 블록이 있다면 그 윗면).
  - 계산된 월드 X, Z를 `Mathf.Round(val / 10f) * 10f` 로 10단위 격자 스냅(`gx, gz`) 처리한다.
- **배치 모드 시각화:**
  - `Handles.DrawWireCube` 또는 반투명 머티리얼 박스를 사용하여 현재 마우스가 가리키는 위치에 선택된 블록의 크기와 회전 상태를 미리보기로 렌더링한다.
- **입력 이벤트 처리 (`Event.current`):**
  - **R 키 누름 (KeyDown):** `currentRotationIndex` 증가 (90도 회전). 미리보기 즉시 반영. `Event.current.Use()` 로 이벤트 소비.
  - **좌클릭 (MouseDown, button 0):** 빈 공간이면 `y=0`에 배치, 기존 블록이 있는 칸이면 그 칸의 기존 최고 높이에 맞춰 적층 배치.
  - **우클릭 (MouseDown, button 1):** 클릭한 지점의 해당 격자 칸 최상단 블록 1개 삭제.
- **선택 모드:**
  - 좌클릭 시 해당 블록을 `Selection.activeGameObject`로 지정하여 Unity 기본 트랜스폼 핸들이 나오게 한다.
  - 위치 이동은 Unity의 기본 격자 스냅(Edit -> Grid and Snap)을 10단위로 설정하여 사용하도록 한다. 에디터 툴 내부에서 Y(높이)는 재계산하지 않고 유지한다.

---

## 4. 구현 후 자체 점검 항목 (Checklist)

- [ ] **확장성:** `Assets/Prefabs/` 폴더에 새로운 태그를 가진 새 프리팹을 추가하고 '새로고침'했을 때, 코드 수정 없이 팔레트 목록과 태그 필터 체크박스가 자동 갱신되는가?
- [ ] **기존 유지:** 기존 파일(SceneDumpExporter, 씬, 프리팹)이 전혀 수정되지 않고 신규 스크립트만 추가되었는가?
- [ ] **스냅 및 적층:** 10×10 격자에 정확히 스냅되며, 같은 칸에 클릭 시 기존 블록 위로 정확히 윗면에 맞춰 쌓이는가?
- [ ] **회전 및 삭제:** R키로 90도 회전이 적용되며, 우클릭 시 아래 블록은 유지된 채 최상단 블록만 하나씩 삭제되는가?
- [ ] **Undo 지원:** 블록 배치 및 삭제를 `Ctrl+Z`로 완벽히 되돌릴 수 있는가?
- [ ] **선택 모드:** 배치 모드와 선택 모드 간의 토글이 정상 작동하며, 선택 모드에서 기존 블록을 클릭하여 선택 및 이동할 수 있는가?

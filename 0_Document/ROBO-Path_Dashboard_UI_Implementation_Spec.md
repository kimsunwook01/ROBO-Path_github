# ROBO-Path 대시보드 UI 설계 및 구현 명세 (Dashboard UI Implementation Spec)

본 문서는 `ROBO-Path` 프로젝트의 프레젠테이션 계층(Streamlit 대시보드)에 대한 전반적인 UI 아키텍처, 구현된 핵심 기능, 그리고 3D 시각화 모듈에 대한 상세 설계 명세이다. 
특히 프론트엔드 목업 단계에서 향후 백엔드(Supabase, FastAPI) 연동으로 넘어갈 때 **구조적 변경을 최소화하고 완벽한 호환성을 보장**하기 위한 단일 기준점(Single Source of Truth) 역할을 수행한다.

---

## 1. 개요 및 아키텍처 (Overview & Architecture)

### 1.1 기술 스택
- **프레임워크:** Streamlit (v1.35 이상 권장, `on_select` 양방향 통신 지원)
- **시각화:** Plotly (`plotly.graph_objects`)
- **스타일링:** 커스텀 CSS (Glassmorphism, Dark Theme 강제) 및 `.streamlit/config.toml` 환경설정

### 1.2 디렉토리 구조
- `src/presentation/dashboard/app.py`: 메인 엔트리 포인트 및 글로벌 설정, 라우팅 관리
- `src/presentation/dashboard/pages/`: 각 도메인별 기능 페이지 (Auth, Home, Path Planning, Map Data, Robots, Settings)
- `src/presentation/dashboard/components/`: 재사용 가능한 UI 컴포넌트 모듈 (3D Viewer 등)
- `src/presentation/dashboard/i18n.py`: 다국어(한국어/영어) 지원 모듈

### 1.3 시뮬레이터 맵 (Simulation Map)
![Simulation Map Top-view](../src/presentation/dashboard/assets/campus_map_topview.png)
*실제 시뮬레이터 맵의 Top-view. 해당 이미지는 2D 경로 탐색 지도의 배경으로 활용된다.*

---

## 2. 기 구현 기능 세부 명세 (Completed Features)

이전에 진행된 작업들은 향후 백엔드 연동을 대비하여 기능별로 철저히 모듈화되었다.

### 2.1 통합 테마 및 CSS 격리 시스템
- **동작 방식:** `app.py` 최상단에서 글로벌 CSS를 주입하여 Streamlit의 기본 흰색 테마를 무력화하고, `radial-gradient`와 `backdrop-filter(blur)`를 활용한 사이버펑크 스타일의 다크 글래스모피즘 룩을 강제한다.
- **백엔드 호환성:** UI 컴포넌트 시각화 계층이 분리되어 있으므로, 데이터 렌더링 로직(Dataframe, Metric)만 백엔드 데이터로 교체하면 디자인이 그대로 유지된다.
- **환경 설정:** `.streamlit/config.toml`을 통해 Streamlit 네이티브 메뉴(햄버거 버튼)와 Toolbar를 강제로 숨겨(`toolbarMode="viewer"`) 비인가 사용자의 테마 임의 변경을 원천 차단했다.

### 2.2 인증 및 세션 파이프라인 (Auth & Session Pipeline)
- **참고 문서:** `ROBO-Path_Auth_Design.md`
- **현재 목업 상태 로직:** `auth.py`에서 인증키(Secret Key) 검증 시 `st.session_state.logged_in = True` 처리와 함께 `st.query_params["logged_in"] = "true"`를 세팅하여 새로고침(F5) 시 세션 초기화를 방지한다.
- **백엔드 연동 시 전환 절차:**
  1. `st.query_params` 기반 임시 세션 유지 코드를 삭제.
  2. FastAPI Auth 라우터를 호출하여 발급받은 JWT(또는 Session ID)를 브라우저의 HTTP-Only 보안 쿠키(세션 쿠키)에 저장.
  3. 쿠키 기반 세션 처리를 통해 탭/브라우저 종료 시 완벽한 자동 로그아웃이 이루어지도록 변경.

### 2.3 다중 페이지 구조 (Multipage Navigation)
- **설계 로직:** `st.navigation` 객체를 사용하여 인증 상태에 따라 라우팅 트리를 동적으로 구성한다. 
- 미인증 시 `[로그인]` 페이지만 노출되며, 인증 시 `[메인 대시보드]`, `[데이터 관리]` 계층의 메뉴가 렌더링된다.

### 2.4 다국어 지원 (I18n)
- **설계 로직:** 화면에 하드코딩되는 문자열을 모두 제거하고 `i18n.py`의 `get_text(key)` 함수를 통해 호출한다. 세션 상태(`st.session_state.lang`)에 따라 한국어/영어가 실시간 전환된다.

---

## 3. 3D 탐색 영역 시각화 명세 (3D Map Visualization Spec)

본 모듈은 `2_path_planning.py` (2D 지도)와 연동되어, 사용자가 클릭한 구역의 로컬 3D 지형을 구글 어스와 같은 형태로 조감하는 기능이다. 

### 3.1 호환성 및 데이터 모델 (Critical)
이 모듈은 단순히 임의의 3D 형태를 그리는 것이 아니라, 향후 **실제 Unity 시뮬레이터에서 덤프될 데이터(`scene_dump.json`) 구조와 100% 호환**되도록 설계된다.
- **참고 문서:** `ROBO-Path_Scene_Dump_Specification.md` (3. 필드 스키마)
- **입력 데이터 구조:** 3D 뷰어 컴포넌트는 반드시 아래 형태의 딕셔너리 배열을 입력 인자(Arguments)로 받아야 한다.
  ```json
  [
    {
      "id": "Flat_10_x1_z2_y5_r0",
      "tag": "Terrain_Flat",
      "position": {"x": 10, "y": 5, "z": 20},
      "size": {"x": 10, "y": 10, "z": 10}
    }
  ]
  ```
- **목업 단계 구현:** 실제 백엔드가 없으므로 위 명세를 정확히 따르는 **가상 지형 생성기(Mock Terrain Generator)** 모듈을 파이썬으로 구현하여 3D 뷰어 컴포넌트에 데이터를 주입한다. 향후 백엔드 연결 시 이 '제너레이터'만 API 호출 코드로 교체하면 시각화 뷰어는 수정 없이 완벽하게 동작한다.

### 3.2 단계별 작업 흐름 (Implementation Workflow)

#### Step 1: Mock 3D 데이터 제너레이터 구현 (`map_3d_viewer.py`)
- **역할:** 특정 기준 좌표(X, Z)를 입력받으면 반경 내의 3D 지형 블록 데이터 배열 생성.
- **동작:** Perlin Noise 또는 수학적 함수를 사용하여 평지(`Terrain_Flat`), 경사/계단(`Terrain_Slope`) 정보를 담은 배열 반환. 스키마는 `scene_dump.json` 명세를 강제 적용.

#### Step 2: Plotly 기반 3D 렌더링 로직 구현 (`map_3d_viewer.py`)
- **시각화 도구:** 호환성이 높고 가벼운 `plotly.graph_objects.Scatter3d` 사용.
- **렌더링 방식:** 각 지형 블록(크기 10x10)을 3D Scatter 큐브 마커(Marker)로 표현.
- **미적 요소:** `tag` 에 따라 색상을 다르게 적용(예: 평지는 짙은 파랑, 계단은 밝은 보라색)하여 가독성과 미래지향적 컨셉 부각. 조명 효과 최적화.

#### Step 3: 2D 이벤트 캡처 및 UI 통합 (`2_path_planning.py`)
- 2D Plotly 차트의 `st.plotly_chart` 에 `on_select="rerun"` 추가.
- 클릭 이벤트 발생 시 선택된 노드의 좌표를 추출.
- 화면 레이아웃을 분할하여(상하 또는 좌우) 선택된 구역의 정보를 담은 3D 렌더링 모듈(Step 2)을 즉각 표출.

---

## 4. 백엔드 전환 시 체크리스트 (Future Backend Integration)
- [ ] `auth.py`: 하드코딩된 비밀번호 체계를 FastAPI JWT 로그인 라우터로 변경 및 세션 쿠키 제어기 연결.
- [ ] `app.py`: 초기 실행 시 DB Connection 확인 및 데이터 동기화 파이프라인 활성화.
- [ ] `map_3d_viewer.py`: `generate_mock_scene_dump()` 함수를 `fetch_scene_dump_from_api()` 로 교체.

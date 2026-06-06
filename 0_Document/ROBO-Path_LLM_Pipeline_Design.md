# LLM 기반 피드백 지식화 파이프라인 설계 명세서

이 문서는 작업자나 관리자가 남긴 비정형 자연어 피드백을 구조화된 JSON 데이터로 변환하여 시스템에 반영하는 LLM 파이프라인(`src/infrastructure/llm/`)의 설계 및 예외 처리 지침을 정의합니다.

## 1. 아키텍처 개요 및 기술 스택
- **목표:** 자연어 피드백(예: "모래사장 구간이라 바퀴가 자꾸 헛돕니다")을 분석하여 이슈 유형, 심각도, 그리고 엣지에 가해질 페널티 수치로 정량화 및 구조화합니다.
- **LLM 제공자:** Google Gemini API (`google-genai` 최신 공식 SDK 사용)
- **사용 모델:** `gemini-1.5-flash` (또는 최신 flash 모델)
- **티어:** Google AI Studio 무료 플랜 (성능보다는 기능 구현과 구조화 메커니즘 구축에 의의를 둠)

## 2. 하네스 엔지니어링 (Constrained Decoding) 활용
단순한 프롬프트 엔지니어링의 한계를 극복하기 위해, 모델이 출력하는 결과물 자체를 파이썬의 **Pydantic 모델 스키마로 강제(Constrained Decoding)** 합니다.
- `google-genai` 클라이언트 설정에서 `response_schema` 파라미터에 미리 정의된 Pydantic 모델을 전달합니다.
- 이를 통해 Gemini 모델은 생성 과정에서 해당 JSON 스키마 구조(Key 이름, Value의 타입 등)를 벗어나는 토큰 자체를 생성하지 못하게 통제되므로, 파싱 에러(Parsing Error) 없는 100% 구조화된 데이터를 보장합니다.

## 3. 구조화 데이터 스키마 설계
Pydantic으로 강제할 출력 스키마 구조는 다음과 같습니다.

### 3.1 이슈 유형 (Issue Types)
현장 주행에서 겪을 수 있는 예기치 못한 이슈들을 분류하기 위해, 초기 모델은 아래 유형을 포함합니다.
- `OBSTACLE`: 정적/동적 장애물에 의한 진로 방해
- `SURFACE_ISSUE`: 미끄럼, 파임, 물웅덩이 등 노면 상태 불량
- `INCLINE_ISSUE`: 스펙 상 통과 가능하나 실제로는 버거운 단차나 급경사
- `NARROW_PATH`: 통로가 좁아 충돌/끼임이 발생
- `MECHANICAL_LOAD`: 모터 과열, 바퀴 헛돔 등 특정 기종의 구동계 부하 발생
- `OTHER`: 위 항목에 속하지 않는 기타 상황

> **[확장성 설계]** 
> 실제 현장에서는 예측하지 못한 유형이 빈번하게 발생합니다. 따라서 데이터베이스(Supabase) 측에서는 이 컬럼을 엄격한 `ENUM` 대신 유연한 `TEXT/VARCHAR`로 관리합니다. 파이썬 코드 레벨에서는 `Literal` 타입으로 기본 풀을 유지하되, 리스트를 분리하여 언제든 신규 유형을 코드 한 줄로 추가할 수 있도록 설계합니다. 또한, 프롬프트를 통해 "가장 적합한 것이 없다면 가장 유사한 단어로 응답하라"는 지침을 추가하여 유연성을 확보합니다.

### 3.2 응답 JSON 모델 (Pydantic)
```python
class FeedbackAnalysis(BaseModel):
    issue_type: str  # 위에서 정의한 유형 중 하나
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    summary: str     # 피드백 내용 50자 이내 요약
    suggested_penalty: float  # 추가 페널티 가중치 (0.0 ~ 1.0)
```

## 4. 예외 처리 전략 (Rate Limiting & Quota Exceeded)
무료 API 플랜의 특성상 분당 요청(RPM) 또는 일일 요청(RPD) 한도를 초과할 가능성을 반드시 고려해야 합니다.

- **에러 핸들링:** 
  LLM 호출부(`gemini_client.py`)에서 API 호출 시 발생하는 `google.genai.errors.APIError` (특히 HTTP Status 429 Too Many Requests)를 `try-except` 구문으로 명시적으로 포착(Catch)합니다.
- **Graceful Degradation:**
  서버 크래시를 방지하기 위해 예외 발생 시 서비스 레이어에 규격화된 실패 응답(Status: Error)과 한도 도달 메시지를 반환합니다.
- **UI 피드백 (Streamlit):**
  관제 대시보드에서는 이 응답을 받아 "현재 AI 분석 서버의 무료 요청 한도가 소진되었습니다. 일정 시간 후 다시 시도해 주세요." 등의 경고(Warning/Toast) 메시지를 띄우고, 임시로 분석 관련 UI 기능을 막아 사용자 경험(UX) 훼손을 방지합니다.

import os
import logging
from typing import Dict, Any, Literal, Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.application.interfaces.llm_client import LLMClient

logger = logging.getLogger(__name__)

class FeedbackAnalysis(BaseModel):
    """
    Gemini가 생성할 구조화된 JSON의 Pydantic 스키마 정의 (Constrained Decoding용).
    """
    issue_type: Literal[
        "OBSTACLE", 
        "SURFACE_ISSUE", 
        "INCLINE_ISSUE", 
        "NARROW_PATH", 
        "MECHANICAL_LOAD", 
        "OTHER"
    ] = Field(description="이슈의 유형. 적합한 것이 없다면 OTHER를 선택하세요.")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="이슈의 심각도를 나타냅니다.")
    summary: str = Field(description="자연어 피드백 내용을 50자 이내로 요약해 주세요.")
    suggested_penalty: float = Field(
        description="해당 이슈로 인해 경로(엣지)에 부여해야 할 추가 페널티 가중치 (0.0 ~ 1.0)",
        ge=0.0, le=1.0
    )

class GeminiClient(LLMClient):
    """
    Google Gemini API를 활용하여 피드백을 구조화된 지식으로 변환하는 인프라 구현체입니다.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY 환경변수가 설정되지 않았습니다. API 호출 시 에러가 발생할 수 있습니다.")
            
        # 최신 google-genai 클라이언트 초기화
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def analyze_feedback(self, raw_feedback: str) -> Dict[str, Any]:
        """
        자연어 피드백을 받아 Gemini API를 통해 Pydantic 스키마(FeedbackAnalysis)에 맞춘 
        딕셔너리 형태로 파싱하여 반환합니다.
        무료 티어 API 토큰 소진 시 예외를 캡처하여 안전한 fallback 응답을 반환합니다.
        """
        prompt = f"""
당신은 로봇 주행 환경을 분석하는 전문 AI입니다. 
작업자나 로봇 관리자가 남긴 다음 현장 피드백을 분석하여 요구된 JSON 스키마에 맞춰 응답하세요.
만약 명시된 issue_type 중 적합한 것이 없다면 반드시 'OTHER'로 분류해야 합니다.

[피드백 내용]
{raw_feedback}
"""

        try:
            # response_schema 파라미터를 통해 출력 구조를 기계적으로 강제(Constrained Decoding)합니다.
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=FeedbackAnalysis,
                    temperature=0.0  # 구조화된 데이터 추출의 결정론성 향상
                )
            )
            
            # Gemini가 생성한 JSON 형태의 문자열을 Pydantic 모델로 변환 및 검증
            if not response.text:
                raise ValueError("Gemini API로부터 빈 응답이 반환되었습니다.")
                
            parsed_model = FeedbackAnalysis.model_validate_json(response.text)
            
            # 클린 아키텍처 원칙에 따라 애플리케이션 계층에는 Pydantic 종속성이 없는 기본 Dict를 반환
            return parsed_model.model_dump()

        except APIError as e:
            # 상태 코드가 429(Too Many Requests)인지 확인하여 API 한도 초과 예외 처리
            if getattr(e, 'code', None) == 429 or "429" in str(e):
                logger.error(f"Gemini API 한도 초과: {e}")
                return {
                    "status": "error",
                    "message": "현재 AI 분석 서버의 일일/분당 요청 한도가 초과되었습니다. 잠시 후 다시 시도해 주세요.",
                    "fallback_data": None
                }
            logger.error(f"Gemini API 호출 중 서버 통신 오류 발생: {e}")
            raise e
        except Exception as e:
            logger.error(f"피드백 구조화 파싱 및 처리 중 오류 발생: {e}")
            raise e

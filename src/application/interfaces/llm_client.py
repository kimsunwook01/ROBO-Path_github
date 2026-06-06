from typing import Protocol, Dict, Any

class LLMClient(Protocol):
    """
    LLM API 통합을 위한 외부 인프라 인터페이스 규약 (Clean Architecture).
    애플리케이션 계층은 특정 벤더(Google, OpenAI 등)에 종속되지 않고 이 인터페이스를 참조합니다.
    """
    def analyze_feedback(self, raw_feedback: str) -> Dict[str, Any]:
        """
        비정형 자연어 피드백을 구조화된 딕셔너리로 변환하여 반환합니다.
        
        Args:
            raw_feedback: 현장 작업자나 로봇이 남긴 자연어 형태의 피드백 문자열.
            
        Returns:
            Dict[str, Any]: 구조화된 JSON 데이터 (스키마 준수)
        """
        ...

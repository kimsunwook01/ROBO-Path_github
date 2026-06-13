import logging
import sys

def setup_logging(level=logging.INFO):
    """
    애플리케이션 진입점에서 호출하여 로깅 기본 설정을 구성합니다.
    (포맷: 시각, 레벨, 모듈명, 메시지 포함)
    라즈베리파이 운영 환경에서 콘솔 및 파일로 출력되도록 구성할 수 있습니다.
    """
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(module)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 (기본 출력)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    
    # 핸들러 중복 추가 방지
    if not root_logger.handlers:
        root_logger.setLevel(level)
        root_logger.addHandler(console_handler)

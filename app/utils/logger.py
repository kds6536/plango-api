"""로깅 유틸리티"""

import logging
import sys
from pathlib import Path
from typing import Optional
from app.config import settings


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """로거를 설정합니다"""
    
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정된 경우 중복 방지
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    log_level = getattr(logging, (level or settings.LOG_LEVEL).upper())
    logger.setLevel(log_level)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (로그 파일이 설정된 경우)
    if settings.LOG_FILE:
        try:
            # 로그 디렉토리 생성
            log_path = Path(settings.LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # 파일 핸들러 설정 실패 시 콘솔에만 로그
            logger.warning(f"파일 로거 설정 실패: {e}")
    
    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """로거를 가져옵니다"""
    return setup_logger(name)


# 전역 로거
app_logger = get_logger("plango-api") 
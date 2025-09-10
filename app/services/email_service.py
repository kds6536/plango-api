"""
이메일 발송 서비스
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("MAIL_SERVER")
        self.smtp_port = int(os.getenv("MAIL_PORT", "587"))
        self.username = os.getenv("MAIL_USERNAME")
        self.password = os.getenv("MAIL_PASSWORD")
        self.from_email = os.getenv("MAIL_FROM")
        self.admin_email = os.getenv("ADMIN_EMAIL")
        
        logger.info(f"📧 [EMAIL_SERVICE] 초기화 완료")
        logger.info(f"  - SMTP Server: {self.smtp_server}")
        logger.info(f"  - SMTP Port: {self.smtp_port}")
        logger.info(f"  - From Email: {self.from_email}")
        logger.info(f"  - Admin Email: {self.admin_email}")
        
    async def send_admin_notification(self, subject: str, error_type: str, error_details: str, user_request: dict):
        """
        관리자에게 이메일 알림을 발송합니다.
        """
        try:
            if not all([self.smtp_server, self.username, self.password, self.from_email, self.admin_email]):
                logger.error("❌ [EMAIL_CONFIG_MISSING] 이메일 설정이 완전하지 않습니다")
                logger.error(f"  - SMTP Server: {'있음' if self.smtp_server else '없음'}")
                logger.error(f"  - Username: {'있음' if self.username else '없음'}")
                logger.error(f"  - Password: {'있음' if self.password else '없음'}")
                logger.error(f"  - From Email: {'있음' if self.from_email else '없음'}")
                logger.error(f"  - Admin Email: {'있음' if self.admin_email else '없음'}")
                return False
            
            logger.info(f"📧 [EMAIL_SEND_START] 관리자 이메일 발송 시작: {subject}")
            
            # 이메일 내용 구성
            from datetime import datetime
            import json
            
            email_body = f"""
Plango 시스템 알림

발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
오류 유형: {error_type}
오류 상세: {error_details}

사용자 요청 정보:
{json.dumps(user_request, indent=2, ensure_ascii=False)}

이 알림은 자동으로 발송되었습니다.
시스템 상태를 확인해주세요.

---
Plango API 시스템
"""
            
            # MIME 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = self.admin_email
            msg['Subject'] = subject
            
            # 본문 추가
            msg.attach(MIMEText(email_body, 'plain', 'utf-8'))
            
            # SMTP 서버 연결 및 발송
            logger.info(f"📧 [SMTP_CONNECT] SMTP 서버 연결 시도: {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # TLS 암호화 시작
                logger.info("🔐 [SMTP_TLS] TLS 연결 성공")
                
                server.login(self.username, self.password)
                logger.info("🔑 [SMTP_LOGIN] SMTP 로그인 성공")
                
                text = msg.as_string()
                server.sendmail(self.from_email, self.admin_email, text)
                logger.info("✅ [EMAIL_SENT] 이메일 발송 성공")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ [EMAIL_SEND_ERROR] 이메일 발송 실패: {e}", exc_info=True)
            return False
    
    async def test_email_connection(self):
        """
        이메일 연결 테스트
        """
        try:
            logger.info("🧪 [EMAIL_TEST] 이메일 연결 테스트 시작")
            
            if not all([self.smtp_server, self.username, self.password]):
                return {
                    "success": False,
                    "error": "이메일 설정이 완전하지 않습니다"
                }
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                
            logger.info("✅ [EMAIL_TEST_SUCCESS] 이메일 연결 테스트 성공")
            return {
                "success": True,
                "message": "이메일 서버 연결 성공"
            }
            
        except Exception as e:
            logger.error(f"❌ [EMAIL_TEST_ERROR] 이메일 연결 테스트 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 전역 인스턴스
email_service = EmailService()
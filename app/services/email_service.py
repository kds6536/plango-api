"""
이메일 발송 서비스 - SendGrid 기반
"""

import logging
import os
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # SendGrid 설정
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("MAIL_FROM", "noreply@plango.app")
        self.admin_email = os.getenv("ADMIN_EMAIL")
        
        logger.info(f"📧 [EMAIL_SERVICE] SendGrid 초기화 완료")
        logger.info(f"  - SendGrid API Key: {'있음' if self.sendgrid_api_key else '없음'}")
        logger.info(f"  - From Email: {self.from_email}")
        logger.info(f"  - Admin Email: {self.admin_email}")
        
        if self.sendgrid_api_key:
            try:
                self.sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
                logger.info("✅ SendGrid 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 SendGrid 클라이언트 초기화 실패: {e}")
                self.sg = None
        else:
            logger.warning("⚠️ SendGrid API 키가 없습니다.")
            self.sg = None
        
    async def send_admin_notification(self, subject: str, error_type: str, error_details: str, user_request: dict):
        """
        관리자에게 이메일 알림을 발송합니다. (SendGrid 사용)
        """
        try:
            if not all([self.sg, self.from_email, self.admin_email]):
                logger.error("❌ [EMAIL_CONFIG_MISSING] SendGrid 설정이 완전하지 않습니다")
                logger.error(f"  - SendGrid Client: {'있음' if self.sg else '없음'}")
                logger.error(f"  - From Email: {'있음' if self.from_email else '없음'}")
                logger.error(f"  - Admin Email: {'있음' if self.admin_email else '없음'}")
                return False
            
            logger.info(f"📧 [EMAIL_SEND_START] SendGrid 이메일 발송 시작: {subject}")
            
            # 이메일 내용 구성
            from datetime import datetime
            import json
            
            email_body = f"""
<h2>🚨 Plango 시스템 알림</h2>

<p><strong>발생 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><strong>오류 유형:</strong> {error_type}</p>
<p><strong>오류 상세:</strong> {error_details}</p>

<h3>사용자 요청 정보:</h3>
<pre>{json.dumps(user_request, indent=2, ensure_ascii=False)}</pre>

<hr>
<p><em>이 알림은 자동으로 발송되었습니다. 시스템 상태를 확인해주세요.</em></p>
<p><strong>Plango API 시스템</strong></p>
"""
            
            # SendGrid 메시지 생성
            message = Mail(
                from_email=self.from_email,
                to_emails=self.admin_email,
                subject=f"[PLANGO 알림] {subject}",
                html_content=email_body
            )
            
            # SendGrid API로 발송
            logger.info(f"📧 [SENDGRID_SEND] SendGrid API 발송 시도")
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ [EMAIL_SENT] SendGrid 이메일 발송 성공: {response.status_code}")
                return True
            else:
                logger.error(f"❌ [EMAIL_FAIL] SendGrid 발송 실패: {response.status_code}")
                logger.error(f"응답 본문: {response.body}")
                return False
            
        except Exception as e:
            logger.error(f"❌ [EMAIL_SEND_ERROR] 이메일 발송 실패: {e}", exc_info=True)
            return False
    
    async def test_email_connection(self):
        """
        SendGrid 연결 테스트
        """
        try:
            logger.info("🧪 [EMAIL_TEST] SendGrid 연결 테스트 시작")
            
            if not all([self.sg, self.from_email, self.admin_email]):
                return {
                    "success": False,
                    "error": "SendGrid 설정이 완전하지 않습니다"
                }
            
            # 테스트 메시지 발송
            test_message = Mail(
                from_email=self.from_email,
                to_emails=self.admin_email,
                subject="[PLANGO] SendGrid 연결 테스트",
                html_content="<p>SendGrid 이메일 서비스가 정상적으로 작동합니다.</p>"
            )
            
            response = self.sg.send(test_message)
            
            if response.status_code in [200, 201, 202]:
                logger.info("✅ [EMAIL_TEST_SUCCESS] SendGrid 연결 테스트 성공")
                return {
                    "success": True,
                    "message": f"SendGrid 연결 성공 (상태: {response.status_code})"
                }
            else:
                logger.error(f"❌ [EMAIL_TEST_FAIL] SendGrid 테스트 실패: {response.status_code}")
                return {
                    "success": False,
                    "error": f"SendGrid API 오류: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"❌ [EMAIL_TEST_ERROR] SendGrid 연결 테스트 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 전역 인스턴스
email_service = EmailService()
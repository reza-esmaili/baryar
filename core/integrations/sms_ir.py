import logging
import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class SMSIRException(Exception):
    pass


class SMSIRProvider:
    VERIFY_ENDPOINT = "https://api.sms.ir/v1/send/verify"

    def __init__(self):
        self.api_key = getattr(settings, "SMSIR_API_KEY", "")
        self.verify_endpoint = getattr(
            settings,
            "SMSIR_VERIFY_BASE_URL",
            self.VERIFY_ENDPOINT,
        )

    def send_verify(self, mobile, template_id, parameters):
        if not self.api_key:
            raise SMSIRException("SMSIR_API_KEY در settings.py تنظیم نشده است.")

        if not template_id:
            raise SMSIRException("شناسه قالب پیامک تنظیم نشده است.")

        payload = {
            "mobile": mobile,
            "templateId": int(template_id),
            "parameters": parameters,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            response = requests.post(
                self.verify_endpoint,
                json=payload,
                headers=headers,
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.exception("SMS.ir connection error")
            raise SMSIRException("خطا در اتصال به سرویس پیامک.") from exc

        response_text = response.text

        if response.status_code < 200 or response.status_code >= 300:
            logger.error(
                "SMS.ir failed. status=%s response=%s",
                response.status_code,
                response_text,
            )
            raise SMSIRException(
                f"خطا در ارسال پیامک. status={response.status_code}, response={response_text}"
            )

        try:
            return response.json()
        except ValueError:
            return {"raw": response_text}

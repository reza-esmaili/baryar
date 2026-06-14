from django.conf import settings
from django.utils import timezone

from accounts.models import OTPCode
from core.integrations.sms_ir import SMSIRException
from core.services.notifications.sms import SmsNotificationService


def send_smsir_verify_code(mobile, code):
    sms_service = SmsNotificationService()
    return sms_service.send_otp(mobile=mobile, code=code)


def check_otp_security(mobile, purpose):
    mobile = OTPCode.normalize_mobile(mobile)

    otp = OTPCode.objects.filter(
        mobile=mobile,
        purpose=purpose,
        is_used=False,
    ).order_by("-created_at").first()

    if otp and otp.requires_captcha():
        return True, otp.attempts

    return False, otp.attempts if otp else 0


def request_otp(mobile, purpose):
    mobile = OTPCode.normalize_mobile(mobile)

    if not OTPCode.is_valid_mobile(mobile):
        raise ValueError("شماره موبایل معتبر نیست.")

    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60))

    last_otp = OTPCode.objects.filter(
        mobile=mobile,
        purpose=purpose,
        is_used=False,
    ).order_by("-created_at").first()

    if last_otp:
        passed = (timezone.now() - last_otp.last_sent_at).total_seconds()

        if passed < cooldown:
            remaining = int(cooldown - passed)
            raise ValueError(f"لطفاً {remaining} ثانیه دیگر دوباره تلاش کنید.")

    otp, code = OTPCode.create_otp(mobile=mobile, purpose=purpose)

    send_smsir_verify_code(mobile=mobile, code=code)

    return {
        "message": "کد تایید ارسال شد.",
        "mobile": mobile,
        "expires_in": OTPCode.get_expire_seconds(),
    }

def verify_otp(mobile, purpose, code):
    mobile = OTPCode.normalize_mobile(mobile)

    # ۱. پیدا کردن آخرین کد ارسال شده برای این موبایل
    otp = OTPCode.objects.filter(
        mobile=mobile,
        purpose=purpose,
        is_used=False
    ).order_by("-created_at").first()

    if not otp:
        return False

    # ۲. بررسی انقضا بر اساس فیلد expires_at مدل
    if otp.is_expired():
        return False

    # ۳. استفاده از متد خود مدل برای چک کردن هش
    # این متد در models.py تو تعریف شده و کد خام را هش کرده و مقایسه می‌کند
    return otp.verify(code)

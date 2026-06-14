from accounts.services import SMSIRException, send_smsir_verify_code


def send_otp_sms(mobile, code):
    try:
        send_smsir_verify_code(mobile=mobile, code=code)
        return True
    except SMSIRException:
        return False
    
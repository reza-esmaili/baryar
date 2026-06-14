from core.integrations.sms_ir import SMSIRException, SMSIRProvider
from core.services.notifications.templates import SmsTemplateRegistry


class SmsNotificationService:
    def __init__(self, provider=None):
        self.provider = provider or SMSIRProvider()

    def send_template(self, mobile, template_key, context):
        template = SmsTemplateRegistry.get_template(
            template_key=template_key,
            context=context,
        )

        return self.provider.send_verify(
            mobile=mobile,
            template_id=template["template_id"],
            parameters=template["parameters"],
        )

    def send_otp(self, mobile, code):
        return self.send_template(
            mobile=mobile,
            template_key="otp",
            context={
                "code": code,
            },
        )

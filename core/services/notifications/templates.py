from django.conf import settings


class SmsTemplateRegistry:
    @staticmethod
    def get_template(template_key, context):
        sms_templates = getattr(settings, "SMS_TEMPLATES", {})

        if template_key not in sms_templates:
            raise ValueError(f"قالب پیامک '{template_key}' تعریف نشده است.")

        template_config = sms_templates[template_key]
        template_id = template_config.get("template_id")
        parameter_mapping = template_config.get("parameters", {})

        if not template_id:
            raise ValueError(f"شناسه قالب پیامک '{template_key}' تنظیم نشده است.")

        parameters = []

        for context_key, smsir_parameter_name in parameter_mapping.items():
            if context_key not in context:
                raise ValueError(
                    f"پارامتر '{context_key}' برای قالب پیامک '{template_key}' ارسال نشده است."
                )

            parameters.append(
                {
                    "name": smsir_parameter_name,
                    "value": str(context[context_key]),
                }
            )

        return {
            "template_id": template_id,
            "parameters": parameters,
        }

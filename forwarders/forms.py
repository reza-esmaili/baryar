# forwarders/forms.py
from django import forms
from forwarders.models import ForwarderCompany
from accounts.models import CompanyType

class ForwarderVerificationForm(forms.Form):
    # نقش کاربر ثبت‌نام کننده
    user_role_in_company = forms.ChoiceField(
        choices=[('ceo', 'مدیر عامل'), ('representative', 'نماینده شرکت')],
        widget=forms.HiddenInput(),
        initial='ceo'
    )
    
    # اطلاعات شرکت
    company_name = forms.CharField(max_length=255, label="نام شرکت")
    company_type = forms.ChoiceField(choices=CompanyType.choices, label="نوع شرکت")
    national_id = forms.CharField(max_length=11, label="شناسه ملی شرکت")
    registration_number = forms.CharField(max_length=20, label="شماره ثبت")
    phone = forms.CharField(max_length=15, label="تلفن شرکت")
    email = forms.EmailField(label="ایمیل شرکت")
    postal_code = forms.CharField(max_length=10, label="کد پستی")
    address = forms.CharField(widget=forms.Textarea, label="آدرس شرکت")
    
    # اطلاعات مدیرعامل (اختیاری در صورتی که کاربر خود مدیرعامل باشد)
    ceo_first_name = forms.CharField(max_length=100, required=False, label="نام مدیر عامل")
    ceo_last_name = forms.CharField(max_length=100, required=False, label="نام خانوادگی مدیر عامل")
    ceo_national_code = forms.CharField(max_length=10, required=False, label="کد ملی مدیر عامل")
    ceo_mobile = forms.CharField(max_length=15, required=False, label="شماره موبایل مدیر عامل")

    # آپلود فایل‌ها (مستندات)
    establishment_notice = forms.FileField(label="آگهی تاسیس")
    articles_of_association = forms.FileField(label="اساسنامه")
    latest_changes = forms.FileField(label="آخرین تغییرات روزنامه رسمی")
    ceo_national_card = forms.FileField(label="کارت ملی مدیر عامل")
    representative_national_card = forms.FileField(required=False, label="کارت ملی نماینده")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("user_role_in_company")
        
        # اگر کاربر نماینده شرکت بود، پر کردن فیلدهای مدیرعامل اجباری می‌شود
        if role == 'representative':
            required_ceo_fields = ['ceo_first_name', 'ceo_last_name', 'ceo_national_code', 'ceo_mobile', 'representative_national_card']
            for field in required_ceo_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "این فیلد برای نقش نماینده شرکت الزامی است.")
        return cleaned_data

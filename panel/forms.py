from django import forms
from django.db import models, transaction
from django.forms import inlineformset_factory

from accounts.models import CompanyType, User
from forwarders.models import ForwarderBranch, ForwarderCompany, ForwarderStaff
from locations.models import City
from rates.models import CargoType, Rate, RateTier


class RateForm(forms.ModelForm):
    class Meta:
        model = Rate
        fields = [
            "transport_mode",
            "origin_province",
            "origin_city",
            "destination_country",
            "destination_city",
            "destination_port",
            "valid_until",
            "cargo_types",
            "shipping_procedure",
        ]
        widgets = {
            "transport_mode": forms.Select(attrs={"class": "form-select"}),
            "origin_province": forms.Select(attrs={"class": "form-select"}),
            "origin_city": forms.Select(attrs={"class": "form-select"}),
            "destination_country": forms.Select(attrs={"class": "form-select"}),
            "destination_city": forms.Select(attrs={"class": "form-select"}),
            "destination_port": forms.Select(attrs={"class": "form-select"}),
            "valid_until": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cargo_types": forms.CheckboxSelectMultiple(),
            "shipping_procedure": forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cargo_types"].queryset = CargoType.objects.all()
        self.fields["cargo_types"].widget.choices = [
            (cargo_type.id, cargo_type.name)
            for cargo_type in CargoType.objects.all()
        ]


class RateTierForm(forms.ModelForm):
    class Meta:
        model = RateTier
        fields = [
            "weight_from",
            "weight_to",
            "pricing_unit",
            "price",
            "container_size",
            "container_type",
        ]
        widgets = {
            "weight_from": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "از وزن (KG)"}
            ),
            "weight_to": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "تا وزن (KG)"}
            ),
            "pricing_unit": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "placeholder": "مبلغ"}),
            "container_size": forms.Select(attrs={"class": "form-select"}),
            "container_type": forms.Select(attrs={"class": "form-select"}),
        }


RateTierFormSet = inlineformset_factory(
    Rate,
    RateTier,
    form=RateTierForm,
    extra=1,
    can_delete=True,
)


class BranchForm(forms.ModelForm):
    class Meta:
        model = ForwarderBranch
        fields = [
            "name",
            "representative_first_name",
            "representative_last_name",
            "representative_mobile",
            "province",
            "city",
            "address",
            "is_active",
        ]
        labels = {
            "name": "نام شعبه",
            "representative_first_name": "نام مدیر / نماینده",
            "representative_last_name": "نام خانوادگی",
            "representative_mobile": "شماره موبایل",
            "province": "استان",
            "city": "شهر",
            "address": "آدرس کامل",
            "is_active": "شعبه فعال است؟",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "مثال: شعبه تهران"}
            ),
            "representative_first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام"}
            ),
            "representative_last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام خانوادگی"}
            ),
            "representative_mobile": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "0912..."}
            ),
            "province": forms.Select(attrs={"class": "form-select"}),
            "city": forms.Select(attrs={"class": "form-select"}),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "آدرس دقیق را وارد کنید...",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["city"].queryset = City.objects.none()

        if "province" in self.data:
            try:
                province_id = int(self.data.get("province"))
                self.fields["city"].queryset = City.objects.filter(
                    province_id=province_id
                ).order_by("name")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.province:
            self.fields["city"].queryset = self.instance.province.city_set.order_by("name")

    @transaction.atomic
    def save(self, forwarder_company, commit=True):
        branch = super().save(commit=False)
        branch.company = forwarder_company

        if not branch.pk:
            user = User.objects.create_user(
                mobile=self.cleaned_data["representative_mobile"],
                first_name=self.cleaned_data["representative_first_name"],
                last_name=self.cleaned_data["representative_last_name"],
                password=self.cleaned_data["representative_mobile"],
            )
            branch.branch_user = user
        else:
            user = branch.branch_user
            user.first_name = self.cleaned_data["representative_first_name"]
            user.last_name = self.cleaned_data["representative_last_name"]
            user.mobile = self.cleaned_data["representative_mobile"]
            user.save()

        if commit:
            branch.save()

        return branch


class StaffForm(forms.ModelForm):
    mobile = forms.CharField(max_length=15, label="شماره موبایل")
    first_name = forms.CharField(max_length=100, label="نام")
    last_name = forms.CharField(max_length=100, label="نام خانوادگی")
    role = forms.ChoiceField(
        choices=[
            ("expert", "کارشناس فورواردر"),
            ("finance", "کارمند مالی فورواردر"),
        ],
        label="نقش",
    )

    class Meta:
        model = ForwarderStaff
        fields = []

    @transaction.atomic
    def save(self, forwarder_company, commit=True):
        staff = super().save(commit=False)
        staff.company = forwarder_company

        if not staff.pk:
            user = User.objects.create_user(
                mobile=self.cleaned_data["mobile"],
                first_name=self.cleaned_data["first_name"],
                last_name=self.cleaned_data["last_name"],
                password=self.cleaned_data["mobile"],
                role=self.cleaned_data["role"],
            )
            staff.user = user

        if commit:
            staff.save()

        return staff


class ForwarderDocumentsForm(forms.Form):
    class ApplicantRole(models.TextChoices):
        CEO = "ceo", "مدیرعامل"
        REPRESENTATIVE = "representative", "نماینده شرکت"

    applicant_role = forms.ChoiceField(
        label="نقش فرد ثبت‌نام‌کننده",
        choices=ApplicantRole.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    company_name = forms.CharField(
        label="نام شرکت",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    company_type = forms.ChoiceField(
        label="نوع شرکت",
        choices=CompanyType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    national_id = forms.CharField(
        label="شناسه ملی شرکت",
        max_length=11,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    registration_number = forms.CharField(
        label="شماره ثبت",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    phone = forms.CharField(
        label="تلفن شرکت",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    email = forms.EmailField(
        label="ایمیل شرکت",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    postal_code = forms.CharField(
        label="کد پستی",
        max_length=10,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    address = forms.CharField(
        label="آدرس شرکت",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    ceo_first_name = forms.CharField(
        label="نام مدیرعامل",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    ceo_last_name = forms.CharField(
        label="نام خانوادگی مدیرعامل",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    ceo_mobile = forms.CharField(
        label="موبایل مدیرعامل",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    ceo_national_code = forms.CharField(
        label="کد ملی مدیرعامل",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    articles_of_association = forms.FileField(
        label="اساسنامه",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    establishment_notice = forms.FileField(
        label="آگهی تاسیس",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    latest_changes = forms.FileField(
        label="آخرین تغییرات",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    ceo_national_card = forms.FileField(
        label="کارت ملی مدیرعامل",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, user=None, company=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        self.company = company

        if company:
            self.fields["company_name"].initial = company.company_name
            self.fields["company_type"].initial = company.company_type
            self.fields["national_id"].initial = company.national_id
            self.fields["registration_number"].initial = company.registration_number
            self.fields["phone"].initial = company.phone
            self.fields["email"].initial = company.email
            self.fields["postal_code"].initial = company.postal_code
            self.fields["address"].initial = company.address
            self.fields["ceo_first_name"].initial = company.ceo_first_name
            self.fields["ceo_last_name"].initial = company.ceo_last_name
            if hasattr(company, "ceo_mobile"):
                self.fields["ceo_mobile"].initial = company.ceo_mobile

            self.fields["ceo_national_code"].initial = company.ceo_national_code

            self.fields["articles_of_association"].required = False
            self.fields["establishment_notice"].required = False
            self.fields["latest_changes"].required = False
            self.fields["ceo_national_card"].required = False

    def clean_national_id(self):
        national_id = self.cleaned_data.get("national_id")

        if not national_id:
            return national_id

        if not national_id.isdigit() or len(national_id) != 11:
            raise forms.ValidationError("شناسه ملی باید ۱۱ رقم باشد.")

        queryset = ForwarderCompany.objects.filter(national_id=national_id)

        if self.company:
            queryset = queryset.exclude(pk=self.company.pk)

        if queryset.exists():
            raise forms.ValidationError("این شناسه ملی قبلاً ثبت شده است.")

        return national_id

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get("postal_code")

        if not postal_code:
            return postal_code

        if not postal_code.isdigit() or len(postal_code) != 10:
            raise forms.ValidationError("کد پستی باید ۱۰ رقم باشد.")

        return postal_code

    def clean_ceo_national_code(self):
        national_code = self.cleaned_data.get("ceo_national_code")

        if national_code and (
            not national_code.isdigit() or len(national_code) != 10
        ):
            raise forms.ValidationError("کد ملی باید ۱۰ رقم باشد.")

        return national_code

    def clean_ceo_mobile(self):
        mobile = self.cleaned_data.get("ceo_mobile")

        if mobile and not mobile.isdigit():
            raise forms.ValidationError("شماره موبایل فقط باید شامل عدد باشد.")

        return mobile

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("applicant_role")

        if role == self.ApplicantRole.REPRESENTATIVE:
            required_fields = [
                "ceo_first_name",
                "ceo_last_name",
                "ceo_mobile",
                "ceo_national_code",
            ]

            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "این فیلد الزامی است.")

        return cleaned_data

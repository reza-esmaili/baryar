from django import forms
from django.forms import inlineformset_factory
from rates.models import Rate, RateTier , CargoType
from django.db import transaction
from forwarders.models import ForwarderBranch, ForwarderStaff
from accounts.models import User
from locations.models import City


class RateForm(forms.ModelForm):
    class Meta:
        model = Rate
        # فیلدها باید دقیقاً با مدل Rate مطابقت داشته باشند
        fields = [
            'transport_mode',  # <--- transport_method به transport_mode تغییر کرد
            'origin_province', 'origin_city', 
            'destination_country', 'destination_city', 'destination_port','valid_until',
            'cargo_types'
        ]
        # برای جلوگیری از خطا، لیست فیلدها را در ویجت نیز به‌روزرسانی می‌کنیم
        widgets = {
            'transport_mode': forms.Select(attrs={'class': 'form-select'}),
            'origin_province': forms.Select(attrs={'class': 'form-select'}),
            'origin_city': forms.Select(attrs={'class': 'form-select'}),
            'destination_country': forms.Select(attrs={'class': 'form-select'}),
            'destination_city': forms.Select(attrs={'class': 'form-select'}),
            'destination_port': forms.Select(attrs={'class': 'form-select'}),
            'valid_until': forms.DateInput(attrs={'type': 'date','class': 'form-control'}),
            'cargo_types': forms.CheckboxSelectMultiple(),
        }
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # اضافه کردن دیتا اتریبیوت برای جاوااسکریپت
            self.fields['cargo_types'].queryset = CargoType.objects.all()
            # برای اینکه جاوااسکریپت بداند هر چک‌باکس مربوط به کدام روش حمل است:
            self.fields['cargo_types'].widget.choices = [
                (c.id, c.name) for c in CargoType.objects.all()
            ]   

class RateTierForm(forms.ModelForm):
    class Meta:
        model = RateTier
        # فیلدها را با مدل RateTier هماهنگ کنید
        fields = ['weight_from', 'weight_to', 'pricing_unit', 'price', 'container_size', 'container_type']
        widgets = {
            'weight_from': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'از وزن (KG)'}),
            'weight_to': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تا وزن (KG)'}),
            'pricing_unit': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'مبلغ'}),
            'container_size': forms.Select(attrs={'class': 'form-select'}),
            'container_type': forms.Select(attrs={'class': 'form-select'}),
        }

# ساخت FormSet برای پلکان‌های قیمتی
RateTierFormSet = inlineformset_factory(
    Rate, RateTier,
    form=RateTierForm,
    extra=1, # تعداد ردیف خالی پیش‌فرض
    can_delete=True # امکان حذف ردیف
)
class BranchForm(forms.ModelForm):
    class Meta:
        model = ForwarderBranch
        fields = [
            'name', 'representative_first_name', 'representative_last_name', 
            'representative_mobile', 'province', 'city', 'address', 'is_active'
        ]
        labels = {
            'name': 'نام شعبه',
            'representative_first_name': 'نام مدیر / نماینده',
            'representative_last_name': 'نام خانوادگی',
            'representative_mobile': 'شماره موبایل',
            'province': 'استان',
            'city': 'شهر',
            'address': 'آدرس کامل',
            'is_active': 'شعبه فعال است؟',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: شعبه تهران'}),
            'representative_first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'representative_last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'representative_mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0912...'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'آدرس دقیق را وارد کنید...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # خالی کردن شهرها در ابتدا برای اتصال AJAX
        self.fields['city'].queryset = City.objects.none()
        
        if 'province' in self.data:
            try:
                province_id = int(self.data.get('province'))
                self.fields['city'].queryset = City.objects.filter(province_id=province_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.province:
            self.fields['city'].queryset = self.instance.province.city_set.order_by('name')

    @transaction.atomic
    def save(self, forwarder_company, commit=True):
        branch = super().save(commit=False)
        branch.company = forwarder_company
        
        if not branch.pk:
            user = User.objects.create_user(
                mobile=self.cleaned_data['representative_mobile'],
                first_name=self.cleaned_data['representative_first_name'],
                last_name=self.cleaned_data['representative_last_name'],
                password=self.cleaned_data['representative_mobile'],
            )
            branch.branch_user = user
        else:
            user = branch.branch_user
            user.first_name = self.cleaned_data['representative_first_name']
            user.last_name = self.cleaned_data['representative_last_name']
            user.mobile = self.cleaned_data['representative_mobile']
            user.save()

        if commit:
            branch.save()
        return branch


class StaffForm(forms.ModelForm):
    mobile = forms.CharField(max_length=15, label="شماره موبایل")
    first_name = forms.CharField(max_length=100, label="نام")
    last_name = forms.CharField(max_length=100, label="نام خانوادگی")
    # نقش‌ها را بر اساس مدل User خود تنظیم کنید
    role = forms.ChoiceField(choices=[
        ('expert', 'کارشناس فورواردر'), 
        ('finance', 'کارمند مالی فورواردر')
    ], label="نقش")

    class Meta:
        model = ForwarderStaff
        fields = [] # فیلدهای اصلی از User گرفته می‌شود

    @transaction.atomic
    def save(self, forwarder_company, commit=True):
        staff = super().save(commit=False)
        staff.company = forwarder_company
        
        if not staff.pk:
            user = User.objects.create_user(
                mobile=self.cleaned_data['mobile'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                password=self.cleaned_data['mobile'],
                role=self.cleaned_data['role']
            )
            staff.user = user
        
        if commit:
            staff.save()
        return staff
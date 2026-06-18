from django import forms
from django.forms import inlineformset_factory
from .models import CargoRequest, CargoDimension
from locations.models import Province, City, Country, DestinationCity, Port
from rates.models import ContainerSize, ContainerType, CargoSubCategory

class CargoRequestForm(forms.ModelForm):
    container_size = forms.ChoiceField(
        choices=ContainerSize.choices,
        required=False,
        label="ابعاد کانتینر"
    )

    container_type = forms.ChoiceField(
        choices=ContainerType.choices,
        required=False,
        label="نوع کانتینر"
    )

    container_count = forms.IntegerField(
        min_value=1,
        required=False,
        label="تعداد کانتینر",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثال: 2'
        })
    )

    origin_country = forms.ModelChoiceField(
        queryset=Country.objects.filter(is_active=True),
        label="کشور مبدا",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            # ظاهر فیلد قابل تغییر نیست، ولی چون disabled نیست در POST ارسال می‌شود
            'style': 'pointer-events: none; background-color: #e9ecef;',
            'tabindex': '-1'
        })
    )

    origin_province = forms.ModelChoiceField(
        queryset=Province.objects.none(),
        label="استان مبدا",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    destination_country = forms.ModelChoiceField(
        queryset=Country.objects.filter(is_active=True),
        label="کشور مقصد",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    destination_city = forms.ModelChoiceField(
        queryset=DestinationCity.objects.none(),
        label="شهر مقصد",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    needs_packaging = forms.BooleanField(
        required=False,
        label="نیاز به بسته‌بندی دارم"
    )
    needs_doorstep_packaging = forms.BooleanField(
        required=False,
        label="نیاز به حمل و بسته‌بندی در محل دارم"
    )

    actual_weight = forms.DecimalField(
        required=False,
        label="وزن واقعی (kg)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثال: 150'
        })
    )

    class Meta:
        model = CargoRequest
        fields = [
            'origin_country',
            'origin_province',
            'origin_city',
            'destination_country',
            'destination_city',
            'transport_mode',
            'destination_port',
            'cargo_type',
            'actual_weight',
            'shipping_procedure',
            'needs_packaging',
        ]

        widgets = {
            'origin_city': forms.Select(attrs={'class': 'form-select'}),
            'destination_port': forms.Select(attrs={'class': 'form-select'}),
            'shipping_procedure': forms.Select(attrs={'class': 'form-select'}),
            'transport_mode': forms.Select(attrs={'class': 'form-select'}),
            'cargo_type': forms.Select(attrs={'class': 'form-select'}),
            'actual_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: 150'
            }),
            'needs_packaging': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        iran = Country.objects.filter(code='IRN', is_active=True).first()

        if iran:
            self.fields['origin_country'].initial = iran

        self.fields['origin_city'].queryset = City.objects.none()
        self.fields['destination_port'].queryset = Port.objects.none()

        # کشور مبدا
        origin_country_id = None

        if self.data.get('origin_country'):
            try:
                origin_country_id = int(self.data.get('origin_country'))
            except (ValueError, TypeError):
                origin_country_id = iran.id if iran else None
        elif self.instance and getattr(self.instance, 'origin_country_id', None):
            origin_country_id = self.instance.origin_country_id
        elif iran:
            origin_country_id = iran.id

        # استان‌های مبدا بر اساس کشور مبدا
        if origin_country_id:
            self.fields['origin_province'].queryset = Province.objects.filter(
                country_id=origin_country_id,
                is_active=True
            )
        else:
            self.fields['origin_province'].queryset = Province.objects.filter(
                is_active=True
            )

        # شهرهای مبدا بر اساس استان مبدا
        if 'origin_province' in self.data:
            try:
                province_id = int(self.data.get('origin_province'))
                self.fields['origin_city'].queryset = City.objects.filter(
                    province_id=province_id,
                    is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.instance and getattr(self.instance, 'origin_province_id', None):
            self.fields['origin_city'].queryset = City.objects.filter(
                province_id=self.instance.origin_province_id,
                is_active=True
            )

        # شهرهای مقصد بر اساس کشور مقصد
        if 'destination_country' in self.data:
            try:
                country_id = int(self.data.get('destination_country'))
                self.fields['destination_city'].queryset = DestinationCity.objects.filter(
                    country_id=country_id
                )
            except (ValueError, TypeError):
                pass
        elif self.instance and getattr(self.instance, 'destination_country_id', None):
            self.fields['destination_city'].queryset = DestinationCity.objects.filter(
                country_id=self.instance.destination_country_id
            )

        # پورت مقصد بر اساس شهر مقصد و روش حمل
        if 'destination_city' in self.data:
            try:
                city_id = int(self.data.get('destination_city'))
                transport_mode = self.data.get('transport_mode')
                ports = Port.objects.filter(city_id=city_id)

                if transport_mode:
                    if 'sea' in transport_mode.lower():
                        ports = ports.filter(port_type='sea')
                    elif 'air' in transport_mode.lower():
                        ports = ports.filter(port_type='air')
                    elif 'land' in transport_mode.lower():
                        ports = ports.filter(port_type='land')

                self.fields['destination_port'].queryset = ports

            except (ValueError, TypeError):
                pass
        elif self.instance and getattr(self.instance, 'destination_city_id', None):
            self.fields['destination_port'].queryset = Port.objects.filter(
                city_id=self.instance.destination_city_id
            )

    def clean_origin_country(self):
        """
        کشور مبدا در فرم مشتری فعلاً باید ایران باشد.
        حتی اگر کاربر از DevTools مقدار را تغییر دهد، اینجا دوباره ایران ست می‌شود.
        """

        iran = Country.objects.filter(code='IRN', is_active=True).first()

        if iran:
            return iran

        return self.cleaned_data.get('origin_country')

    def clean(self):
        cleaned_data = super().clean()

        transport_mode = cleaned_data.get('transport_mode')
        actual_weight = cleaned_data.get('actual_weight')

        if transport_mode in ['sea_fcl', 'FCL']:
            if not cleaned_data.get('container_type'):
                self.add_error('container_type', 'برای حمل FCL، انتخاب نوع کانتینر الزامی است.')

            if not cleaned_data.get('container_count'):
                self.add_error('container_count', 'برای حمل FCL، تعیین تعداد کانتینر الزامی است.')

            if actual_weight is None:
                cleaned_data['actual_weight'] = 0

        else:
            if actual_weight is None:
                self.add_error('actual_weight', 'وارد کردن وزن واقعی برای این روش حمل الزامی است.')

        return cleaned_data


class CargoDimensionForm(forms.ModelForm):
    class Meta:
        model = CargoDimension
        fields = ['length', 'width', 'height', 'quantity']
        widgets = {
            'length': forms.NumberInput(attrs={'class': 'form-control dimension-input', 'placeholder': 'طول (cm)'}),
            'width': forms.NumberInput(attrs={'class': 'form-control dimension-input', 'placeholder': 'عرض (cm)'}),
            'height': forms.NumberInput(attrs={'class': 'form-control dimension-input', 'placeholder': 'ارتفاع (cm)'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'value': 1}),
        }

CargoDimensionFormSet = inlineformset_factory(
    CargoRequest, CargoDimension, form=CargoDimensionForm,
    extra=1, can_delete=True
)

class OrderCompletionForm(forms.ModelForm):
    is_for_other = forms.BooleanField(
        required=False, 
        label="ثبت سفارش برای فرد دیگری است",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is_for_other_checkbox'})
    )

    class Meta:
        model = CargoRequest
        fields = [
            'sender_name',
            'sender_national_id',
            'sender_phone',
            'sender_province', 
            'sender_city', 
            'sender_address', 
            'cargo_subcategories', 
            'other_cargo_details'
        ]
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # مقداردهی فقط زمانی که فرم POST نشده (یعنی درخواست GET است)
        if self.user and not self.data:
            self.initial['sender_name'] = f"{self.user.first_name} {self.user.last_name}".strip()
            self.initial['sender_phone'] = getattr(self.user, 'mobile', '')
            
            national_id = ''
            if hasattr(self.user, 'customer_profile') and self.user.customer_profile:
                national_id = self.user.customer_profile.national_code
            elif hasattr(self.user, 'customer_company_profile') and self.user.customer_company_profile:
                national_id = self.user.customer_company_profile.national_id
            self.initial['sender_national_id'] = national_id

        # مقداردهی و قفل کردن استان و شهر مبدا
        if self.instance and self.instance.origin_city:
            self.initial['sender_city'] = self.instance.origin_city
            if hasattr(self.instance.origin_city, 'province'):
                self.initial['sender_province'] = self.instance.origin_city.province
            
            # قفل کردن فیلدها در فرانت‌اند
            self.fields['sender_city'].disabled = True
            self.fields['sender_province'].disabled = True

        if self.instance and self.instance.cargo_type:
            self.fields['cargo_subcategories'].queryset = CargoSubCategory.objects.filter(
                category=self.instance.cargo_type
            )
        
        self.fields['cargo_subcategories'].widget.attrs.update({'class': 'select2-multiple'})
        self.fields['sender_address'].widget.attrs.update({'rows': 3})
        
        self.fields['sender_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['sender_national_id'].widget.attrs.update({'class': 'form-control'})
        self.fields['sender_phone'].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        
        # برگرداندن مقادیر استان و شهر (چون در حالت disabled سمت سرور ارسال نمی‌شوند)
        if self.instance and self.instance.origin_city:
            cleaned_data['sender_city'] = self.instance.origin_city
            if hasattr(self.instance.origin_city, 'province'):
                cleaned_data['sender_province'] = self.instance.origin_city.province
                
        # اعتبارسنجی فیلدهای هویتی
        if not cleaned_data.get('sender_name'):
            self.add_error('sender_name', 'نام و نام خانوادگی فرستنده الزامی است.')
        if not cleaned_data.get('sender_national_id'):
            self.add_error('sender_national_id', 'کد ملی فرستنده الزامی است.')
        if not cleaned_data.get('sender_phone'):
            self.add_error('sender_phone', 'شماره تماس فرستنده الزامی است.')
            
        return cleaned_data

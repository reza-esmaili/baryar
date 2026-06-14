from django import forms
from accounts.models import User,CustomerProfile, CustomerCompanyProfile, IdentityDocument

class LoginForm(forms.Form):
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره موبایل'}), label='شماره موبایل')
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'}), label='رمز عبور')

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'}), label='رمز عبور')
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'mobile', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره موبایل'}),
        }
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'mobile': 'شماره موبایل',
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # فیلد mobile را از اینجا حذف کردیم تا خطای Duplicate ندهد
        fields = [
            "first_name",
            "last_name",
            "email",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
        labels = {
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "email": "ایمیل (اختیاری)",
        }


class CustomerProfileForm(forms.ModelForm):

    class Meta:
        model = CustomerProfile

        fields = [
            "national_code",
            "address"
        ]

        widgets = {
            "national_code": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            })
        }


class CompanyProfileForm(forms.ModelForm):

    class Meta:
        model = CustomerCompanyProfile

        exclude = ["user"]


class IdentityDocumentForm(forms.ModelForm):

    class Meta:
        model = IdentityDocument

        fields = [
            "doc_type",
            "file"
        ]

        widgets = {
            "doc_type": forms.Select(attrs={
                "class": "form-select"
            }),

            "file": forms.FileInput(attrs={
                "class": "form-control"
            })
        }
from django import forms

from .models import (
    OrderDocument,
    AdditionalDocumentUpload,
)


class OrderDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = OrderDocument
        fields = [
            "file",
            "customer_note",
        ]

        widgets = {
            "file": forms.FileInput(attrs={
                "class": "form-control",
            }),
            "customer_note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "در صورت نیاز توضیحی برای این مدرک وارد کنید..."
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")

        if file:
            self.instance.file = file
            self.instance.validate_file()

        return file


class AdditionalDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = AdditionalDocumentUpload
        fields = [
            "file",
            "customer_note",
        ]

        widgets = {
            "file": forms.FileInput(attrs={
                "class": "form-control",
            }),
            "customer_note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "توضیحات خود را وارد کنید..."
            }),
        }

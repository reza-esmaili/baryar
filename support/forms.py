from django import forms
from .models import Ticket, TicketMessage, TicketTransfer, TicketTopic, SupportDepartment


class TicketCreateForm(forms.ModelForm):
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 5,
            "placeholder": "متن درخواست خود را بنویسید"
        })
    )

    attachment = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control"
        })
    )

    class Meta:
        model = Ticket
        fields = ["department", "topic", "subject"]
        widgets = {
            "department": forms.Select(attrs={
                "class": "form-select",
                "id": "id_department"
            }),
            "topic": forms.Select(attrs={
                "class": "form-select",
                "id": "id_topic"
            }),
            "priority": forms.Select(attrs={
                "class": "form-select"
            }),
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "عنوان تیکت"
            }),
        }

    def __init__(self, *args, **kwargs):
        panel_type = kwargs.pop("panel_type", None)
        super().__init__(*args, **kwargs)

        # فیلتر واحدها بر اساس نوع پنل
        department_qs = SupportDepartment.objects.filter(is_active=True)

        if panel_type:
            department_qs = department_qs.filter(panel_type=panel_type)

        self.fields["department"].queryset = department_qs

        # در حالت پیش‌فرض تا قبل از انتخاب واحد، موضوع‌ها خالی باشند
        self.fields["topic"].queryset = TicketTopic.objects.none()

        # اگر فرم POST شده و department ارسال شده
        if "department" in self.data:
            try:
                department_id = int(self.data.get("department"))
                self.fields["topic"].queryset = TicketTopic.objects.filter(
                    department_id=department_id,
                    department__is_active=True,
                    is_active=True
                )

                if panel_type:
                    self.fields["topic"].queryset = self.fields["topic"].queryset.filter(
                        department__panel_type=panel_type
                    )

            except (ValueError, TypeError):
                pass

        # اگر فرم روی instance موجود لود شده
        elif self.instance.pk and self.instance.department:
            topic_qs = self.instance.department.topics.filter(is_active=True)

            if panel_type:
                topic_qs = topic_qs.filter(department__panel_type=panel_type)

            self.fields["topic"].queryset = topic_qs


class TicketReplyForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ["message", "attachment"]
        widgets = {
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "پاسخ خود را بنویسید"
            }),
            "attachment": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }


class TicketTransferForm(forms.ModelForm):
    class Meta:
        model = TicketTransfer
        fields = ["to_department", "note"]
        widgets = {
            "to_department": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "توضیح ارجاع"
            }),
        }

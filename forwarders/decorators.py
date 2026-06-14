# forwarders/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from forwarders.models import ForwarderCompany

def forwarder_verified_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        # بررسی اینکه آیا کاربر ادمین فورواردر است
        if request.user.is_authenticated and request.user.role == request.user.Role.FORWARDER_ADMIN:
            try:
                company = request.user.forwarder_company
                if not company.is_verified:
                    # اگر شرکت ثبت شده ولی هنوز تایید نشده است
                    messages.warning(request, "حساب کاربری شما در انتظار تایید مدارک توسط کارشناس است.")
                    return redirect("forwarder_panel:documents_upload")
            except ForwarderCompany.DoesNotExist:
                # اگر هنوز اطلاعات شرکت را وارد نکرده است
                messages.warning(request, "لطفاً ابتدا مدارک و اطلاعات شرکت خود را جهت احراز هویت تکمیل کنید.")
                return redirect("forwarder_panel:documents_upload")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# panel/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from accounts.models import User
from forwarders.models import ForwarderCompany


def forwarder_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("customer:login")

        allowed_roles = [
            User.Role.FORWARDER_ADMIN,
            User.Role.FORWARDER_EXPERT,
            User.Role.FORWARDER_FINANCE,
        ]

        if request.user.role not in allowed_roles:
            return HttpResponseForbidden("شما دسترسی مشاهده این صفحه را ندارید.")

        # نام URL جاری
        current_url_name = getattr(request.resolver_match, "url_name", "")

        # صفحه مدارک باید همیشه برای ادمین فورواردر باز باشد
        allowed_without_verification = [
            "documents",
        ]

        if current_url_name in allowed_without_verification:
            return view_func(request, *args, **kwargs)

        # محدودیت فقط برای ادمین اصلی فورواردر اعمال شود
        # چون کارمند/مالی اصولاً وقتی معنی دارد که شرکت ساخته شده و تایید شده باشد.
        if request.user.role == User.Role.FORWARDER_ADMIN:
            try:
                company = request.user.forwarder_company
            except ForwarderCompany.DoesNotExist:
                messages.warning(
                    request,
                    "برای استفاده از پنل، ابتدا اطلاعات شرکت و مدارک خود را تکمیل کنید."
                )
                return redirect("forwarder_panel:documents")

            if not company.is_verified or not company.is_active:
                messages.warning(
                    request,
                    "حساب فورواردر شما هنوز توسط کارشناس تایید نشده است."
                )
                return redirect("forwarder_panel:documents")

        else:
            # برای نقش‌های کارشناس و مالی، شرکت از طریق ForwarderStaff قابل شناسایی است.
            # اگر بخواهید سخت‌گیرانه‌تر باشید، اینجا هم وضعیت شرکت را چک کنید.
            staff_profile = getattr(request.user, "forwarder_staff", None)
            if staff_profile and (
                not staff_profile.company.is_verified or not staff_profile.company.is_active
            ):
                messages.warning(
                    request,
                    "حساب شرکت فورواردر هنوز فعال یا تایید نشده است."
                )
                return redirect("forwarder_panel:documents")

        return view_func(request, *args, **kwargs)

    return _wrapped_view

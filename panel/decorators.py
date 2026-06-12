# panel/decorators.py (یا مستقیماً در panel/views.py)
from django.http import HttpResponseForbidden
from functools import wraps
from accounts.models import User

def forwarder_required(view_func):
    """
    بررسی می‌کند که آیا کاربر دارای یکی از نقش‌های مجاز پنل فورواردر هست یا خیر.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # بررسی نقش‌های مجاز (می‌توانید اگر نقش شعبه هم دارید اینجا اضافه کنید)
        allowed_roles = [
            User.Role.FORWARDER_ADMIN, 
            User.Role.FORWARDER_EXPERT, 
            User.Role.FORWARDER_FINANCE
        ]
        
        # اگر کاربر احراز هویت شده و نقشش مجاز بود، ادامه بده
        if request.user.is_authenticated and request.user.role in allowed_roles:
            return view_func(request, *args, **kwargs)
        
        # در غیر این صورت، پیغام خطای عدم دسترسی بده
        return HttpResponseForbidden("شما دسترسی مشاهده این صفحه رو ندارید.")
        
    return _wrapped_view

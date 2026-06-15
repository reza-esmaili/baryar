from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from locations.models import City, DestinationCity

from accounts.models import User, CustomerProfile, OTPCode
from accounts.services import request_otp, verify_otp, SMSIRException

from orders.models import CargoRequest

from documents.models import (
    AdditionalDocumentRequest,
    AdditionalDocumentUpload,
)

from .forms import (
    LoginForm,
    RegisterForm,
    UserProfileForm,
    CustomerProfileForm,
    IdentityDocumentForm,
)


# =============================================================================
# Role Based Redirect Helpers
# =============================================================================

def redirect_based_on_role(user):
    """
    هدایت کاربر بعد از ورود یا ثبت‌نام بر اساس نقش.

    - کاربران مرتبط با فورواردر به پنل فورواردر منتقل می‌شوند.
    - سایر کاربران، از جمله مشتری، به صفحه اصلی سایت منتقل می‌شوند.

    این تابع به صورت مرکزی استفاده می‌شود تا منطق redirect در چند View تکرار نشود.
    """

    panel_roles = [
        User.Role.FORWARDER_ADMIN,
        User.Role.FORWARDER_EXPERT,
        User.Role.FORWARDER_FINANCE,
    ]

    if user.role in panel_roles:
        return redirect("forwarder_panel:dashboard")

    return redirect("/")


# =============================================================================
# Authentication Views - Login / Logout
# =============================================================================

def login_view(request):
    """
    ورود کاربر با شماره موبایل و رمز عبور.

    اگر کاربر از قبل لاگین کرده باشد، بر اساس نقش به پنل مناسب هدایت می‌شود.
    """

    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    form = LoginForm()

    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            mobile = OTPCode.normalize_mobile(form.cleaned_data.get("mobile"))
            password = form.cleaned_data.get("password")

            user = authenticate(request, mobile=mobile, password=password)

            if user is not None:
                login(request, user)
                return redirect_based_on_role(user)

            form.add_error(None, "شماره موبایل یا رمز عبور اشتباه است.")

    return render(
        request,
        "login_page/login.html",
        {
            "form": form,
        },
    )


@login_required
@require_POST
def logout_view(request):
    """
    خروج کاربر از حساب کاربری.

    این View فقط با POST کار می‌کند تا خروج ناخواسته با GET اتفاق نیفتد.
    """

    logout(request)
    messages.success(request, "با موفقیت از حساب کاربری خارج شدید.")
    return redirect("/")


# =============================================================================
# Registration Views - Customer / Forwarder Register Pages
# =============================================================================

def customer_register_view(request):
    """
    نمایش صفحه ثبت‌نام مشتری.

    فرآیند ثبت‌نام واقعی از طریق AJAX و OTP انجام می‌شود.
    """

    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    form = RegisterForm()

    return render(
        request,
        "login_page/customer_register.html",
        {
            "form": form,
            "register_role": User.Role.CUSTOMER,
            "register_title": "ثبت‌نام مشتری",
            "register_subtitle": "ایجاد حساب کاربری مشتری",
        },
    )


def forwarder_register_view(request):
    """
    نمایش صفحه ثبت‌نام فورواردر.

    فرآیند ثبت‌نام واقعی از طریق AJAX و OTP انجام می‌شود.
    """

    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    form = RegisterForm()

    return render(
        request,
        "login_page/forwarder_register.html",
        {
            "form": form,
            "register_role": User.Role.FORWARDER_ADMIN,
            "register_title": "ثبت‌نام فورواردر",
            "register_subtitle": "ایجاد حساب شرکت حمل‌ونقل",
        },
    )


# =============================================================================
# OTP Login APIs
# =============================================================================

@require_POST
def web_login_request_otp(request):
    """
    درخواست ارسال کد OTP برای ورود.

    ورودی:
        - mobile

    خروجی:
        JsonResponse شامل وضعیت عملیات.

    نکته امنیتی:
        فقط برای کاربر فعال موجود، OTP ارسال می‌شود.
    """

    mobile = request.POST.get("mobile")
    mobile = OTPCode.normalize_mobile(mobile)

    if not User.objects.filter(mobile=mobile, is_active=True).exists():
        return JsonResponse(
            {"ok": False, "message": "کاربری با این شماره موبایل وجود ندارد."},
            status=400,
        )

    try:
        result = request_otp(mobile=mobile, purpose=OTPCode.Purpose.LOGIN)
        return JsonResponse({"ok": True, **result})

    except ValueError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=429)

    except SMSIRException as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=502)


@require_POST
def web_login_verify_otp(request):
    """
    تایید کد OTP ورود.

    در صورت صحت کد:
        - کاربر لاگین می‌شود.
        - redirect_url مناسب بر اساس نقش کاربر برگردانده می‌شود.
    """

    mobile = OTPCode.normalize_mobile(request.POST.get("mobile"))
    code = request.POST.get("code", "")

    if verify_otp(mobile=mobile, purpose=OTPCode.Purpose.LOGIN, code=code):
        try:
            user = User.objects.get(mobile=mobile, is_active=True)

        except User.DoesNotExist:
            return JsonResponse(
                {"ok": False, "message": "کاربر یافت نشد."},
                status=404,
            )

        login(request, user)

        redirect_url = "/"
        if user.role in [
            User.Role.FORWARDER_ADMIN,
            User.Role.FORWARDER_EXPERT,
            User.Role.FORWARDER_FINANCE,
        ]:
            redirect_url = "/forwarder-panel/"

        return JsonResponse(
            {
                "ok": True,
                "message": "ورود با موفقیت انجام شد.",
                "redirect_url": redirect_url,
            }
        )

    return JsonResponse(
        {"ok": False, "message": "کد وارد شده اشتباه یا منقضی شده است."},
        status=400,
    )


# =============================================================================
# OTP Register APIs
# =============================================================================

@require_POST
def web_register_request_otp(request):
    """
    درخواست ارسال OTP برای ثبت‌نام.

    اطلاعات اولیه ثبت‌نام در session نگهداری می‌شود تا بعد از تایید OTP،
    حساب کاربری ساخته شود.
    """

    mobile = OTPCode.normalize_mobile(request.POST.get("mobile"))
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    password = request.POST.get("password", "")
    role = request.POST.get("role", User.Role.CUSTOMER)

    if role not in [User.Role.CUSTOMER, User.Role.FORWARDER_ADMIN]:
        return JsonResponse(
            {"ok": False, "message": "نوع ثبت‌نام معتبر نیست."},
            status=400,
        )

    if not first_name or not last_name or not mobile or not password:
        return JsonResponse(
            {"ok": False, "message": "لطفاً همه فیلدهای ضروری را وارد کنید."},
            status=400,
        )

    if not OTPCode.is_valid_mobile(mobile):
        return JsonResponse(
            {"ok": False, "message": "شماره موبایل معتبر نیست."},
            status=400,
        )

    if User.objects.filter(mobile=mobile).exists():
        return JsonResponse(
            {"ok": False, "message": "این شماره موبایل قبلاً ثبت شده است."},
            status=400,
        )

    request.session["pending_register"] = {
        "first_name": first_name,
        "last_name": last_name,
        "mobile": mobile,
        "password": password,
        "role": role,
    }

    try:
        result = request_otp(mobile=mobile, purpose=OTPCode.Purpose.REGISTER)
        return JsonResponse({"ok": True, **result})

    except ValueError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=429)

    except SMSIRException as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=502)


@require_POST
def web_register_verify_otp(request):
    """
    تایید OTP ثبت‌نام و ساخت حساب کاربری.

    بعد از ساخت کاربر:
        - اطلاعات session پاک می‌شود.
        - کاربر لاگین می‌شود.
        - redirect_url مناسب برگردانده می‌شود.
    """

    pending = request.session.get("pending_register")

    if not pending:
        return JsonResponse(
            {
                "ok": False,
                "message": "اطلاعات ثبت‌نام یافت نشد. لطفاً دوباره تلاش کنید.",
            },
            status=400,
        )

    mobile = OTPCode.normalize_mobile(pending.get("mobile"))
    code = request.POST.get("code", "")

    if User.objects.filter(mobile=mobile).exists():
        request.session.pop("pending_register", None)

        return JsonResponse(
            {"ok": False, "message": "این شماره موبایل قبلاً ثبت شده است."},
            status=400,
        )

    if not verify_otp(mobile=mobile, purpose=OTPCode.Purpose.REGISTER, code=code):
        return JsonResponse(
            {"ok": False, "message": "کد وارد شده اشتباه یا منقضی شده است."},
            status=400,
        )

    user = User.objects.create_user(
        mobile=mobile,
        password=pending["password"],
        first_name=pending["first_name"],
        last_name=pending["last_name"],
        role=pending["role"],
    )

    request.session.pop("pending_register", None)

    login(request, user)

    if user.role == User.Role.FORWARDER_ADMIN:
        redirect_url = "/panel/"
    else:
        redirect_url = "/"

    return JsonResponse(
        {
            "ok": True,
            "message": "ثبت‌نام با موفقیت انجام شد.",
            "redirect_url": redirect_url,
        }
    )


@require_POST
def web_register_cancel(request):
    """
    لغو فرآیند ثبت‌نام و پاک کردن داده‌های موقت از session.
    """

    request.session.pop("pending_register", None)

    return JsonResponse(
        {
            "ok": True,
            "message": "فرآیند ثبت‌نام لغو شد.",
        }
    )


# =============================================================================
# Customer Profile Views
# =============================================================================

@login_required
def profile_view(request):
    """
    صفحه یکپارچه مشاهده و ویرایش پروفایل مشتری.

    این View:
        - اطلاعات کاربر و پروفایل مشتری را نمایش می‌دهد.
        - فرم ویرایش اطلاعات کاربر و پروفایل مشتری را مدیریت می‌کند.
        - چند آمار خلاصه برای داشبورد پروفایل آماده می‌کند.
    """

    user = request.user

    customer_profile, created = CustomerProfile.objects.get_or_create(user=user)

    company_profile = getattr(user, "customer_company_profile", None)
    business_info = getattr(user, "business_info", None)

    documents = user.documents.all()
    orders = user.cargo_requests.order_by("-created_at")[:5]

    if request.method == "POST":
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = CustomerProfileForm(request.POST, instance=customer_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            messages.success(request, "اطلاعات پروفایل با موفقیت به‌روزرسانی شد.")
            return redirect("customer:profile")

        messages.error(request, "خطایی در فرم رخ داده است. لطفاً فیلدها را بررسی کنید.")

    else:
        user_form = UserProfileForm(instance=user)
        profile_form = CustomerProfileForm(instance=customer_profile)

    context = {
        "customer_profile": customer_profile,
        "company_profile": company_profile,
        "business_info": business_info,
        "user_form": user_form,
        "profile_form": profile_form,
        "documents": documents,
        "recent_orders": orders,
        "orders_count": user.cargo_requests.count(),
        "pending_orders": user.cargo_requests.filter(status="pending").count(),
        "completed_orders": user.cargo_requests.filter(status="completed").count(),
        "documents_count": documents.count(),
    }

    return render(
        request,
        "customer_panel/profile/profile.html",
        context,
    )


@login_required
def edit_profile(request):
    """
    مسیر سازگارکننده برای لینک‌های قدیمی ویرایش پروفایل.

    چون مشاهده و ویرایش پروفایل اکنون در profile.html ادغام شده است،
    همه درخواست‌ها به صفحه اصلی پروفایل منتقل می‌شوند.
    """

    return redirect("customer:profile")


@login_required
def profile_dashboard(request):
    """
    داشبورد خلاصه پروفایل مشتری.

    این View آمار کلی حساب کاربر را نمایش می‌دهد.
    """

    context = {
        "orders_count": request.user.cargo_requests.count(),
        "pending_orders": request.user.cargo_requests.filter(status="pending").count(),
        "documents_count": request.user.documents.count(),
    }

    return render(
        request,
        "customer_panel/profile/dashboard.html",
        context,
    )


# =============================================================================
# Customer Orders Query Helpers
# =============================================================================

def get_customer_orders_queryset(user):
    """
    Queryset پایه سفارش‌های مشتری.

    هدف:
        - جلوگیری از N+1 Query
        - آماده کردن داده‌های لازم برای لیست سفارش‌ها و فیلتر Ajax

    ساختار مدل‌های location در پروژه:

    مبدا:
        CargoRequest.origin_city -> City -> Province

    مقصد:
        CargoRequest.destination_port -> Port -> DestinationCity -> Country
    """

    return CargoRequest.objects.filter(
        customer=user,
    ).select_related(
        "cargo_type",
        "origin_city",
        "origin_city__province",
        "destination_port",
        "destination_port__city",
        "destination_port__city__country",
        "selected_rate",
    ).order_by("-created_at")


# =============================================================================
# Customer Orders Views
# =============================================================================

@login_required
def order_list(request):
    """
    نمایش لیست سفارش‌های مشتری.

    همراه با:
        - لیست شهرهای مبدا موجود در سفارش‌های همین مشتری
        - لیست شهرهای مقصد موجود در سفارش‌های همین مشتری
        - داده‌های لازم برای فیلتر کردن سفارش‌ها
    """

    orders = get_customer_orders_queryset(request.user)

    origin_city_ids = orders.exclude(
        origin_city_id__isnull=True,
    ).values_list(
        "origin_city_id",
        flat=True,
    ).distinct()

    origin_cities = City.objects.filter(
        id__in=origin_city_ids,
        is_active=True,
    ).select_related(
        "province",
    ).order_by(
        "province__name",
        "name",
    )

    destination_city_ids = orders.exclude(
        destination_port__city_id__isnull=True,
    ).values_list(
        "destination_port__city_id",
        flat=True,
    ).distinct()

    destination_cities = DestinationCity.objects.filter(
        id__in=destination_city_ids,
        is_active=True,
    ).select_related(
        "country",
    ).order_by(
        "country__name",
        "name",
    )

    context = {
        "orders": orders,
        "origin_cities": origin_cities,
        "destination_cities": destination_cities,
    }

    return render(
        request,
        "customer_panel/profile/order_list.html",
        context,
    )


@login_required
def order_detail(request, pk):
    """
    نمایش جزئیات سفارش برای مشتری.

    این صفحه علاوه بر اطلاعات اصلی سفارش، دو گروه مدرک را نمایش می‌دهد:

    1. مدارک اصلی سفارش:
        از طریق related_name مدل OrderDocument، یعنی:
            order.required_documents.all

    2. مدارک تکمیلی درخواست‌شده توسط فورواردر:
        از طریق مدل AdditionalDocumentRequest

    نکته امنیتی:
        سفارش فقط در صورتی نمایش داده می‌شود که متعلق به request.user باشد.
    """

    order = get_object_or_404(
        CargoRequest.objects.select_related(
            "cargo_type",
            "origin_city",
            "origin_city__province",
            "destination_port",
            "destination_port__city",
            "destination_port__city__country",
            "selected_rate",
        ).prefetch_related(
            "cargo_subcategories",
            "dimensions",
            "required_documents",
            "required_documents__document_type",
        ),
        pk=pk,
        customer=request.user,
    )

    additional_document_requests = (
        AdditionalDocumentRequest.objects
        .filter(order=order)
        .prefetch_related("uploads")
        .order_by("-created_at")
    )

    context = {
        "order": order,
        "additional_document_requests": additional_document_requests,
    }

    return render(
        request,
        "customer_panel/profile/order_detail.html",
        context,
    )


@login_required
def filter_orders(request):
    """
    فیلتر Ajax سفارش‌ها.

    پارامترهای GET:
        - origin: شناسه City برای مبدا
        - destination: شناسه DestinationCity برای مقصد
        - transport: نوع حمل
        - date: تاریخ ایجاد سفارش با فرمت YYYY-MM-DD
        - shipping_procedure: رویه ارسال / حمل

    خروجی:
        رندر partial مخصوص ردیف‌های جدول سفارش‌ها.
    """

    origin_id = request.GET.get("origin")
    destination_id = request.GET.get("destination")
    transport = request.GET.get("transport")
    date_str = request.GET.get("date")
    shipping_procedure = request.GET.get("shipping_procedure")

    orders = get_customer_orders_queryset(request.user)

    if shipping_procedure:
        orders = orders.filter(shipping_procedure=shipping_procedure)

    if origin_id:
        orders = orders.filter(origin_city_id=origin_id)

    if destination_id:
        orders = orders.filter(destination_port__city_id=destination_id)

    if transport:
        orders = orders.filter(transport_mode=transport)

    if date_str:
        orders = orders.filter(created_at__date=date_str)

    return render(
        request,
        "customer_panel/profile/partials/orders_table_rows.html",
        {
            "orders": orders,
        },
    )


# =============================================================================
# Customer Identity Documents Views
# =============================================================================

@login_required
def document_list(request):
    """
    نمایش لیست مدارک هویتی/عمومی کاربر.

    این بخش مستقل از مدارک سفارش است.
    مدارک سفارش از طریق order_detail نمایش داده می‌شوند.
    """

    documents = request.user.documents.all()

    return render(
        request,
        "customer_panel/profile/documents.html",
        {
            "documents": documents,
        },
    )


@login_required
def upload_document(request):
    """
    آپلود مدارک هویتی/عمومی کاربر.

    این View مربوط به مدارک عمومی حساب کاربری است،
    نه مدارک اختصاصی سفارش.
    """

    if request.method == "POST":
        form = IdentityDocumentForm(request.POST, request.FILES)

        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.save()

            messages.success(request, "مدرک با موفقیت بارگذاری شد.")
            return redirect("customer:documents")

        messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")

    else:
        form = IdentityDocumentForm()

    return render(
        request,
        "customer_panel/profile/upload_document.html",
        {
            "form": form,
        },
    )


# =============================================================================
# Additional Document Requests - Customer Upload
# =============================================================================

@login_required
@require_POST
def upload_additional_document(request, request_id):
    """
    آپلود فایل برای مدرک تکمیلی درخواست‌شده توسط فورواردر.

    سناریو:
        - فورواردر برای یک سفارش، مدرک جدیدی درخواست می‌کند.
        - مشتری در صفحه جزئیات سفارش، درخواست را مشاهده می‌کند.
        - مشتری فایل را از طریق همین View آپلود می‌کند.

    نکات امنیتی:
        - مشتری فقط می‌تواند برای سفارش خودش فایل آپلود کند.
        - درخواست باید متعلق به سفارشی باشد که customer آن request.user است.
        - اگر درخواست بسته/لغوشده/تکمیل‌شده باشد، آپلود جدید پذیرفته نمی‌شود.

    نکته:
        در این نسخه پس از اولین آپلود، وضعیت درخواست به completed تغییر می‌کند.
        اگر می‌خواهی مشتری بتواند چند فایل برای یک درخواست آپلود کند،
        بخش تغییر status به completed را حذف یا شرطی کن.
    """

    additional_request = get_object_or_404(
        AdditionalDocumentRequest.objects.select_related(
            "order",
            "order__customer",
        ),
        pk=request_id,
        order__customer=request.user,
    )

    # فقط درخواست‌های باز اجازه آپلود دارند.
    # این شرط با مقدار string نوشته شده تا حتی اگر TextChoices جداگانه نداشته باشی، کار کند.
    if additional_request.status != "open":
        messages.error(
            request,
            "امکان آپلود برای این درخواست وجود ندارد؛ وضعیت درخواست باز نیست.",
        )
        return redirect(
            "customer:order_detail",
            pk=additional_request.order.pk,
        )

    uploaded_file = request.FILES.get("file")
    customer_note = request.POST.get("customer_note", "").strip()

    if not uploaded_file:
        messages.error(request, "لطفاً یک فایل برای بارگذاری انتخاب کنید.")

        return redirect(
            "customer:order_detail",
            pk=additional_request.order.pk,
        )

    with transaction.atomic():
        AdditionalDocumentUpload.objects.create(
            request=additional_request,
            file=uploaded_file,
            uploaded_by=request.user,
            customer_note=customer_note,
        )

        # بعد از آپلود موفق، درخواست را تکمیل‌شده می‌کنیم.
        # اگر منطق شما اجازه چند آپلود برای یک درخواست می‌دهد، این دو خط را حذف کن.
        additional_request.status = "completed"
        additional_request.save(update_fields=["status"])

    messages.success(request, "فایل مدرک تکمیلی با موفقیت بارگذاری شد.")

    return redirect(
        "customer:order_detail",
        pk=additional_request.order.pk,
    )

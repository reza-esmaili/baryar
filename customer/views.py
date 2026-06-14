from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from locations.models import City, DestinationCity

from accounts.models import User, CustomerProfile, OTPCode
from accounts.services import request_otp, verify_otp, SMSIRException
from orders.models import CargoRequest

from .forms import (
    LoginForm,
    RegisterForm,
    UserProfileForm,
    CustomerProfileForm,
    IdentityDocumentForm,
)


def redirect_based_on_role(user):
    panel_roles = [
        User.Role.FORWARDER_ADMIN,
        User.Role.FORWARDER_EXPERT,
        User.Role.FORWARDER_FINANCE,
    ]

    if user.role in panel_roles:
        return redirect("forwarder_panel:dashboard")

    return redirect("/")


def login_view(request):
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


def customer_register_view(request):
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


@require_POST
def web_login_request_otp(request):
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


@require_POST
def web_register_request_otp(request):
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


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "با موفقیت از حساب کاربری خارج شدید.")
    return redirect("/")


@require_POST
def web_register_cancel(request):
    request.session.pop("pending_register", None)
    return JsonResponse({"ok": True, "message": "فرآیند ثبت‌نام لغو شد."})


@login_required
def profile_view(request):
    """
    صفحه یکپارچه مشاهده و ویرایش پروفایل کاربر.

    این View هم اطلاعات نمایشی را به profile.html می‌فرستد
    و هم فرم‌های ویرایش را با instance صحیح مقداردهی می‌کند.
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
        else:
            print("--- User Form Errors ---", user_form.errors)
            print("--- Profile Form Errors ---", profile_form.errors)

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

    return render(request, "customer_panel/profile/profile.html", context)


@login_required
def edit_profile(request):
    """
    این View قبلاً برای صفحه جداگانه ویرایش استفاده می‌شد.

    چون حالا مشاهده و ویرایش داخل profile.html ادغام شده،
    بهتر است هر درخواستی به edit_profile به صفحه اصلی پروفایل منتقل شود.

    اگر در urls.py هنوز مسیر customer:profile_edit وجود دارد،
    این تابع باعث می‌شود لینک‌های قبلی خراب نشوند.
    """

    return redirect("customer:profile")


@login_required
def profile_dashboard(request):
    context = {
        "orders_count": request.user.cargo_requests.count(),
        "pending_orders": request.user.cargo_requests.filter(status="pending").count(),
        "documents_count": request.user.documents.count(),
    }

    return render(request, "customer_panel/profile/dashboard.html", context)


@login_required
def order_detail(request, pk):
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
        ),
        pk=pk,
        customer=request.user,
    )

    return render(
        request,
        "customer_panel/profile/order_detail.html",
        {
            "order": order,
        },
    )


def get_customer_orders_queryset(user):
    """
    Queryset پایه سفارش‌های مشتری با select_related های لازم
    برای جلوگیری از N+1 Query.

    ساختار صحیح مدل‌های location در پروژه:

    مبدا:
        CargoRequest.origin_city -> City -> Province

    مقصد:
        CargoRequest.destination_port -> Port -> DestinationCity -> Country
    """

    return CargoRequest.objects.filter(
        customer=user
    ).select_related(
        "cargo_type",
        "origin_city",
        "origin_city__province",
        "destination_port",
        "destination_port__city",
        "destination_port__city__country",
        "selected_rate",
    ).order_by("-created_at")


@login_required
def order_list(request):
    """
    لیست سفارش‌های مشتری.

    نکته مهم:
    - origin_city از مدل City می‌آید و به Province وصل است.
    - destination_port.city از مدل DestinationCity می‌آید و به Country وصل است.

    بنابراین:
    - برای شهرهای مبدا باید از City + province استفاده شود.
    - برای شهرهای مقصد باید از DestinationCity + country استفاده شود.
    """

    orders = get_customer_orders_queryset(request.user)

    origin_city_ids = orders.exclude(
        origin_city_id__isnull=True
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
        destination_port__city_id__isnull=True
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
def document_list(request):
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


@login_required
def filter_orders(request):
    """
    فیلتر Ajax سفارش‌ها.

    پارامترهای GET:
    - origin: شناسه City برای مبدا
    - destination: شناسه DestinationCity برای مقصد
    - transport: نوع حمل
    - date: تاریخ ایجاد سفارش با فرمت YYYY-MM-DD
    """

    origin_id = request.GET.get("origin")
    destination_id = request.GET.get("destination")
    transport = request.GET.get("transport")
    date_str = request.GET.get("date")

    orders = get_customer_orders_queryset(request.user)

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

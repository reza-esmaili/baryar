from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User, IdentityDocument, CustomerProfile, OTPCode
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
        return redirect("forwarder_panel:branch_list")

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
            return JsonResponse({"ok": False, "message": "کاربر یافت نشد."}, status=404)

        login(request, user)

        redirect_url = "/"
        if user.role in [
            User.Role.FORWARDER_ADMIN,
            User.Role.FORWARDER_EXPERT,
            User.Role.FORWARDER_FINANCE,
        ]:
            redirect_url = "/forwarder-panel/"

        return JsonResponse({
            "ok": True,
            "message": "ورود با موفقیت انجام شد.",
            "redirect_url": redirect_url,
        })

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
        return JsonResponse({"ok": False, "message": "نوع ثبت‌نام معتبر نیست."}, status=400)

    if not first_name or not last_name or not mobile or not password:
        return JsonResponse({"ok": False, "message": "لطفاً همه فیلدهای ضروری را وارد کنید."}, status=400)

    if not OTPCode.is_valid_mobile(mobile):
        return JsonResponse({"ok": False, "message": "شماره موبایل معتبر نیست."}, status=400)

    if User.objects.filter(mobile=mobile).exists():
        return JsonResponse({"ok": False, "message": "این شماره موبایل قبلاً ثبت شده است."}, status=400)

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
            {"ok": False, "message": "اطلاعات ثبت‌نام یافت نشد. لطفاً دوباره تلاش کنید."},
            status=400,
        )

    mobile = OTPCode.normalize_mobile(pending.get("mobile"))
    code = request.POST.get("code", "")

    if User.objects.filter(mobile=mobile).exists():
        request.session.pop("pending_register", None)
        return JsonResponse({"ok": False, "message": "این شماره موبایل قبلاً ثبت شده است."}, status=400)

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
        redirect_url = "/forwarder-panel/"
    else:
        redirect_url = "/"

    return JsonResponse({
        "ok": True,
        "message": "ثبت‌نام با موفقیت انجام شد.",
        "redirect_url": redirect_url,
    })


@require_POST
def web_register_cancel(request):
    request.session.pop("pending_register", None)
    return JsonResponse({"ok": True, "message": "فرآیند ثبت‌نام لغو شد."})


@login_required
def profile_view(request):
    user = request.user

    customer_profile = getattr(user, "customer_profile", None)
    company_profile = getattr(user, "customer_company_profile", None)
    business_info = getattr(user, "business_info", None)
    documents = user.documents.all()

    orders = user.cargo_requests.order_by("-created_at")[:5]

    context = {
        "customer_profile": customer_profile,
        "company_profile": company_profile,
        "business_info": business_info,
        "documents": documents,
        "recent_orders": orders,
        "orders_count": user.cargo_requests.count(),
        "pending_orders": user.cargo_requests.filter(status="pending").count(),
        "completed_orders": user.cargo_requests.filter(status="completed").count(),
        "documents_count": documents.count(),
    }

    return render(request, "customer_panel/profile.html", context)


@login_required
def profile_dashboard(request):
    context = {
        "orders_count": request.user.cargo_requests.count(),
        "pending_orders": request.user.cargo_requests.filter(status="pending").count(),
        "documents_count": request.user.documents.count(),
    }

    return render(request, "customer_panel/profile/dashboard.html", context)


@login_required
def edit_profile(request):
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = CustomerProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("customer:profile")

    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = CustomerProfileForm(instance=profile)

    return render(
        request,
        "customer_panel/profile/edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )


@login_required
def order_detail(request, pk):
    order = get_object_or_404(CargoRequest, pk=pk, customer=request.user)

    return render(
        request,
        "customer_panel/profile/order_detail.html",
        {
            "order": order,
        },
    )


@login_required
def order_list(request):
    orders = request.user.cargo_requests.select_related(
        "cargo_type",
        "destination_port",
    ).order_by("-created_at")

    return render(
        request,
        "customer_panel/profile/order_list.html",
        {
            "orders": orders,
        },
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

            return redirect("customer:documents")

    else:
        form = IdentityDocumentForm()

    return render(
        request,
        "customer_panel/profile/upload_document.html",
        {
            "form": form,
        },
    )

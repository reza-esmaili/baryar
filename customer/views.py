from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import login, authenticate
from .forms import LoginForm, RegisterForm , UserProfileForm , CustomerProfileForm ,IdentityDocumentForm
from accounts.models import User , IdentityDocument , CustomerCompanyProfile , CustomerProfile
from django.contrib.auth.decorators import login_required
from orders.models import CargoRequest

def login_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile')
            password = form.cleaned_data.get('password')
            user = authenticate(request, mobile=mobile, password=password)
            if user is not None:
                login(request, user)
                return redirect_based_on_role(user)
            else:
                form.add_error(None, 'شماره موبایل یا رمز عبور اشتباه است.')
    else:
        form = LoginForm()
    return render(request, 'login_page/login.html', {'form': form})

def redirect_based_on_role(user):
    panel_roles = [
        User.Role.FORWARDER_ADMIN, 
        User.Role.FORWARDER_EXPERT, 
        User.Role.FORWARDER_FINANCE
    ]
    if user.role in panel_roles:
        return redirect('forwarder_panel:branch_list') # به مسیر داشبورد یا صفحه اصلی پنل تغییر دهید
    return redirect('/') # مسیر صفحه اصلی سایت

def customer_register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.CUSTOMER
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('/')
    else:
        form = RegisterForm()
    return render(request, 'login_page/customer_register.html', {'form': form})

def forwarder_register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.FORWARDER_ADMIN
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('forwarder_panel:branch_list')
    else:
        form = RegisterForm()
    return render(request, 'login_page/forwarder_register.html', {'form': form})
@login_required
def profile_view(request):

    user = request.user

    customer_profile = getattr(user, "customer_profile", None)
    company_profile = getattr(user, "customer_company_profile", None)
    business_info = getattr(user, "business_info", None)

    documents = user.documents.all()

    orders = user.cargo_requests.order_by(
        "-created_at"
    )[:5]

    context = {
        "customer_profile": customer_profile,
        "company_profile": company_profile,
        "business_info": business_info,
        "documents": documents,
        "recent_orders": orders,

        "orders_count": user.cargo_requests.count(),

        "pending_orders": user.cargo_requests.filter(
            status="pending"
        ).count(),

        "completed_orders": user.cargo_requests.filter(
            status="completed"
        ).count(),

        "documents_count": documents.count(),
    }

    return render(
        request,
        "customer_panel/profile.html",
        context
    )

@login_required
def profile_dashboard(request):

    orders_count = request.user.cargo_requests.count()

    pending_orders = request.user.cargo_requests.filter(
        status="pending"
    ).count()

    documents_count = request.user.documents.count()

    context = {
        "orders_count": orders_count,
        "pending_orders": pending_orders,
        "documents_count": documents_count,
    }

    return render(
        request,
        "customer_panel/profile/dashboard.html",
        context
    )

@login_required
def edit_profile(request):

    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        user_form = UserProfileForm(
            request.POST,
            instance=request.user
        )

        profile_form = CustomerProfileForm(
            request.POST,
            instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():

            user_form.save()
            profile_form.save()

            return redirect("customer:profile")

    else:

        user_form = UserProfileForm(
            instance=request.user
        )

        profile_form = CustomerProfileForm(
            instance=profile
        )

    return render(
        request,
        "customer_panel/profile/edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form
        }
    )

@login_required
def order_detail(request, pk):

    order = get_object_or_404(
        CargoRequest,
        pk=pk,
        customer=request.user
    )

    return render(
        request,
        "customer_panel/profile/order_detail.html",
        {
            "order": order
        }
    )
@login_required
def order_list(request):

    orders = request.user.cargo_requests.select_related(
        "cargo_type",
        "destination_port"
    ).order_by("-created_at")

    return render(
        request,
        "customer_panel/profile/order_list.html",
        {
            "orders": orders
        }
    )

@login_required
def document_list(request):

    documents = request.user.documents.all()

    return render(
        request,
        "customer_panel/profile/documents.html",
        {
            "documents": documents
        }
    )

@login_required
def upload_document(request):

    if request.method == "POST":

        form = IdentityDocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            doc = form.save(commit=False)

            doc.user = request.user

            doc.save()

            return redirect(
                "customer:documents"
            )

    else:

        form = IdentityDocumentForm()

    return render(
        request,
        "customer_panel/profile/upload_document.html",
        {
            "form": form
        }
    )
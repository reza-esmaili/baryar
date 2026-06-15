from django.urls import include, path

from . import views


app_name = "customer"


urlpatterns = [
    # =========================================================================
    # Authentication
    # =========================================================================

    path("login/",views.login_view,name="login",),

    path("logout/",views.logout_view,name="logout",),

    # =========================================================================
    # Registration Pages
    # =========================================================================

    path(
        "register/",
        views.customer_register_view,
        name="customer_register",
    ),

    path(
        "register/forwarder/",
        views.forwarder_register_view,
        name="forwarder_register",
    ),

    # =========================================================================
    # Web OTP - Login
    # =========================================================================

    path(
        "auth/login/request-otp/",
        views.web_login_request_otp,
        name="web_login_request_otp",
    ),

    path(
        "auth/login/verify-otp/",
        views.web_login_verify_otp,
        name="web_login_verify_otp",
    ),

    # =========================================================================
    # Web OTP - Register
    # =========================================================================

    path(
        "auth/register/request-otp/",
        views.web_register_request_otp,
        name="web_register_request_otp",
    ),

    path(
        "auth/register/verify-otp/",
        views.web_register_verify_otp,
        name="web_register_verify_otp",
    ),

    path(
        "auth/register/cancel/",
        views.web_register_cancel,
        name="web_register_cancel",
    ),

    # =========================================================================
    # Customer Profile
    # =========================================================================

    path(
        "profile/",
        views.profile_view,
        name="profile",
    ),

    path(
        "profile/dashboard/",
        views.profile_dashboard,
        name="profile_dashboard",
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile",
    ),

    # =========================================================================
    # Customer Orders
    # =========================================================================

    path(
        "profile/orders/",
        views.order_list,
        name="order_list",
    ),

    path(
        "profile/orders/filter/",
        views.filter_orders,
        name="filter_orders",
    ),

    path(
        "profile/orders/<int:pk>/",
        views.order_detail,
        name="order_detail",
    ),

    # =========================================================================
    # Customer Identity Documents
    # =========================================================================

    path(
        "profile/documents/",
        views.document_list,
        name="documents",
    ),

    path(
        "profile/documents/upload/",
        views.upload_document,
        name="upload_document",
    ),

    # =========================================================================
    # Additional Documents Requested By Forwarder
    # =========================================================================
    # این مسیر برای آپلود مدارک تکمیلی است که فورواردر برای یک سفارش درخواست می‌کند.
    # فرم مربوط به این مسیر داخل صفحه جزئیات سفارش مشتری قرار می‌گیرد.
    # دقت کن که نام این URL در template باید دقیقاً همین باشد:
    # customer:upload_additional_document

    path(
        "profile/additional-documents/<int:request_id>/upload/",
        views.upload_additional_document,
        name="upload_additional_document",
    ),

    # =========================================================================
    # Support
    # =========================================================================

    path(
        "profile/support/",
        include(("support.urls", "support"), namespace="customer_support"),
    ),
]

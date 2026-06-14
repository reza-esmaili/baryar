from django.urls import path
from django.urls import path, include

from . import views

app_name = "customer"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.customer_register_view, name="customer_register"),
    path("register/forwarder/", views.forwarder_register_view, name="forwarder_register"),

    # Web OTP AJAX
    path("auth/login/request-otp/", views.web_login_request_otp, name="web_login_request_otp"),
    path("auth/login/verify-otp/", views.web_login_verify_otp, name="web_login_verify_otp"),

    path("auth/register/request-otp/", views.web_register_request_otp, name="web_register_request_otp"),
    path("auth/register/verify-otp/", views.web_register_verify_otp, name="web_register_verify_otp"),
    path("auth/register/cancel/", views.web_register_cancel, name="web_register_cancel"),

    path("profile/", views.profile_view, name="profile"),
    path("profile/dashboard/", views.profile_dashboard, name="profile_dashboard"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),

    path("profile/orders/", views.order_list, name="order_list"),
    path("profile/orders/<int:pk>/", views.order_detail, name="order_detail"),

    path("profile/documents/", views.document_list, name="documents"),
    path("profile/documents/upload/", views.upload_document, name="upload_document"),
    path("profile/support/", include(('support.urls', 'support'), namespace='customer_support')),

]

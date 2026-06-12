from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.customer_register_view, name='customer_register'),
    path('register/forwarder/', views.forwarder_register_view, name='forwarder_register'),
    path("profile/",views.profile_view,name="profile"),
    path("profile/", views.profile_dashboard, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),

    path("profile/orders/", views.order_list, name="order_list"),
    path("profile/orders/<int:pk>/", views.order_detail, name="order_detail"),

    path("profile/documents/", views.document_list, name="documents"),
    path("profile/documents/upload/", views.upload_document, name="upload_document"),
]

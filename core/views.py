from django.shortcuts import render

from accounts.models import User
from orders.models import CargoRequest


def home(request):

    orders_count = CargoRequest.objects.count()

    customers_count = User.objects.filter(
        role=User.Role.CUSTOMER
    ).count()

    forwarders_count = User.objects.filter(
        role__in=[
            User.Role.FORWARDER_ADMIN,
            User.Role.FORWARDER_EXPERT,
            User.Role.FORWARDER_FINANCE,
        ]
    ).count()

    context = {
        "orders_count": orders_count,
        "customers_count": customers_count,
        "forwarders_count": forwarders_count,
    }

    return render(
        request,
        "home.html",
        context
    )
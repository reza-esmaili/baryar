from rest_framework.permissions import BasePermission
from accounts.models import User

class IsForwarderUser(BasePermission):
    """بررسی دسترسی فورواردر (ادمین، کارشناس، مالی)"""
    def has_permission(self, request, view):
        allowed_roles = [
            User.Role.FORWARDER_ADMIN, 
            User.Role.FORWARDER_EXPERT, 
            User.Role.FORWARDER_FINANCE
        ]
        return bool(request.user and request.user.is_authenticated and request.user.role in allowed_roles)

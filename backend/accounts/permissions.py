"""Role-based permission classes. Frontend route guards are only UX; these
classes are the real security boundary."""
from rest_framework.permissions import BasePermission


class _RolePermission(BasePermission):
    role = None
    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role == self.role)


class IsCustomer(_RolePermission):
    role = 'customer'
    message = 'Only customers can do this.'


class IsFarmer(_RolePermission):
    role = 'farmer'
    message = 'Only farmers can do this.'


class IsAdminRole(_RolePermission):
    role = 'admin'
    message = 'Only administrators can do this.'


class IsApprovedFarmer(BasePermission):
    """A farmer whose KYC has been approved by an admin."""
    message = 'Your farmer account must pass KYC verification before you can do this.'

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated and u.is_active and u.role == 'farmer'):
            return False
        farm = getattr(u, 'farm', None)
        return bool(farm and farm.is_verified)

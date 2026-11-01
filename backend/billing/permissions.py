from rest_framework.permissions import BasePermission

from accounts.models import Role


class IsBeneficiary(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.BENEFICIARY)


class CanReadPayments(BasePermission):
    """Beneficiário vê os próprios pagamentos; Admin e Bispo veem todos (só leitura)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in (Role.ADMIN, Role.BISHOP, Role.BENEFICIARY)
        )
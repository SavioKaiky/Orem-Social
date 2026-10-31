from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Role

READ_ROLES = (Role.ADMIN, Role.BISHOP, Role.WORKER, Role.BENEFICIARY)
WRITE_ROLES = (Role.ADMIN, Role.BENEFICIARY)


class MemberDataAccess(BasePermission):
    """
    Leitura: Admin, Bispo, Obreiro e Beneficiário (cada um só vê o seu recorte,
    definido no queryset). Escrita: só Admin e o próprio Beneficiário.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated) or user.role not in READ_ROLES:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in WRITE_ROLES


class CanViewReports(BasePermission):
    """Relatórios agregados: Admin, Bispo e Obreiro (este só com os seus números)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in (Role.ADMIN, Role.BISHOP, Role.WORKER)
        )
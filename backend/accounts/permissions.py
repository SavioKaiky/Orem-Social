from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


class IsAdmin(BasePermission):
    """Somente o Admin (acesso total, leitura e escrita)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.ADMIN)


class IsAdminOrBishopReadOnly(BasePermission):
    """Admin faz tudo; o Bispo só consulta (GET/HEAD/OPTIONS)."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role == Role.ADMIN:
            return True
        return user.role == Role.BISHOP and request.method in SAFE_METHODS


class CanManageWorkers(BasePermission):
    """Admin e Bispo gerenciam obreiros (o Bispo cadastra e edita, conforme o relatório)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in (Role.ADMIN, Role.BISHOP))
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import Charge, PixEvent, PixProvider
from .fake import FakePixProvider

__all__ = ["Charge", "PixEvent", "PixProvider", "FakePixProvider", "get_provider"]


def get_provider() -> PixProvider:
    """Escolhe o provedor pelo .env. O adaptador do Banco do Brasil entra com as credenciais."""
    if settings.PIX_PROVIDER == "fake":
        return FakePixProvider()
    raise ImproperlyConfigured(f"Provedor PIX '{settings.PIX_PROVIDER}' ainda não implementado.")
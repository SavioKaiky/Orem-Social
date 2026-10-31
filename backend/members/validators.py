from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_not_future(value):
    """Datas de nascimento não podem estar no futuro."""
    if value > timezone.localdate():
        raise ValidationError("A data não pode ser futura.", code="future_date")
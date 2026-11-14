import re

from django.core.exceptions import ValidationError


def only_digits(value: str) -> str:
    """Remove pontos, traços e espaços, deixando só os números."""
    return re.sub(r"\D", "", value or "")


def normalize_phone(value: str) -> str:
    """Guarda telefones brasileiros apenas com DDD e número, sem o código +55."""
    digits = only_digits(value)
    if digits.startswith("55") and len(digits) in (12, 13):
        return digits[2:]
    return digits


def validate_phone(value: str) -> None:
    """Exige telefone brasileiro com DDD e 10 ou 11 dígitos."""
    phone = normalize_phone(value)
    if len(phone) not in (10, 11):
        raise ValidationError("Informe um telefone com DDD.", code="invalid_phone")


def _check_digit(digits: str) -> str:
    """Dígito verificador do CPF (módulo 11) para a sequência recebida."""
    weight = len(digits) + 1
    total = sum(int(d) * w for d, w in zip(digits, range(weight, 1, -1)))
    return str((total * 10) % 11 % 10)


def validate_cpf(value: str) -> None:
    """Valida o CPF pelos dígitos verificadores; aceita com ou sem máscara."""
    cpf = only_digits(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.", code="invalid_cpf")
    first = _check_digit(cpf[:9])
    second = _check_digit(cpf[:9] + first)
    if cpf[9:] != first + second:
        raise ValidationError("CPF inválido.", code="invalid_cpf")
import pytest
from django.core.exceptions import ValidationError

from accounts.validators import only_digits, validate_cpf


def test_only_digits_removes_mask():
    assert only_digits("529.982.247-25") == "52998224725"


@pytest.mark.parametrize("cpf", ["52998224725", "529.982.247-25"])
def test_valid_cpf(cpf):
    validate_cpf(cpf)


@pytest.mark.parametrize("cpf", ["11111111111", "12345678900", "123", "", "5299822472a"])
def test_invalid_cpf(cpf):
    with pytest.raises(ValidationError):
        validate_cpf(cpf)
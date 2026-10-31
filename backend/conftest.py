import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import Role, User, WorkerProfile
from accounts.tests.helpers import generate_cpf


@pytest.fixture(autouse=True)
def clear_cache():
    """Zera os contadores de limite de tentativas entre os testes."""
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    """Fábrica de usuários com CPF válido; cria o perfil de obreiro quando preciso."""
    counter = {"n": 0}

    def _make(role=Role.BENEFICIARY, password="Senha@12345", **extra):
        counter["n"] += 1
        user = User.objects.create_user(
            cpf=generate_cpf(f"{counter['n']:09d}"),
            password=password,
            full_name=f"Usuário {counter['n']}",
            role=role,
            **extra,
        )
        if role == Role.WORKER:
            WorkerProfile.objects.create(user=user)
        return user

    return _make
import pytest

from accounts.models import Role, User


def _mask(cpf):
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


@pytest.mark.django_db
def test_create_user_normalizes_cpf():
    user = User.objects.create_user(cpf="529.982.247-25", password="Senha@12345", full_name="Maria")
    assert user.cpf == "52998224725"
    assert user.role == Role.BENEFICIARY


@pytest.mark.django_db
def test_superuser_is_admin():
    user = User.objects.create_superuser(cpf="52998224725", password="Senha@12345", full_name="Admin")
    assert user.role == Role.ADMIN
    assert user.is_staff and user.is_superuser


def test_login_with_masked_cpf(api_client, make_user):
    user = make_user(Role.WORKER)
    response = api_client.post(
        "/api/auth/login/", {"cpf": _mask(user.cpf), "password": "Senha@12345"}, format="json"
    )
    assert response.status_code == 200
    assert {"access", "refresh", "user"} <= set(response.data)
    assert response.data["user"]["role"] == Role.WORKER
    assert response.data["user"]["worker_code"].startswith("OBR-")


def test_login_by_phone(api_client, make_user):
    user = make_user(phone="(62) 99999-0000")
    response = api_client.post(
        "/api/auth/login/", {"identifier": "+55 (62) 99999-0000", "password": "Senha@12345"}, format="json"
    )
    assert response.status_code == 200, response.data
    assert response.data["user"]["id"] == user.id
    assert user.phone == "62999990000"


def test_login_wrong_password(api_client, make_user):
    user = make_user()
    response = api_client.post("/api/auth/login/", {"cpf": user.cpf, "password": "errada"}, format="json")
    assert response.status_code == 401


def test_me_requires_login(api_client):
    assert api_client.get("/api/auth/me/").status_code == 401


def test_me_returns_current_user(api_client, make_user):
    user = make_user(Role.BISHOP)
    api_client.force_authenticate(user)
    response = api_client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["cpf"] == user.cpf
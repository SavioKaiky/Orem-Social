import pytest

from accounts.models import Role, User

PAYLOAD = {
    "cpf": "529.982.247-25",
    "full_name": "João Obreiro",
    "phone": "62999990000",
    "password": "Senha@12345",
}


def test_worker_code_is_generated(make_user):
    profile = make_user(Role.WORKER).worker_profile
    assert profile.code == f"OBR-{profile.pk:02d}"


@pytest.mark.parametrize("role", [Role.BISHOP, Role.ADMIN])
def test_bishop_and_admin_create_worker(api_client, make_user, role):
    api_client.force_authenticate(make_user(role))
    response = api_client.post("/api/workers/", PAYLOAD, format="json")
    assert response.status_code == 201
    assert response.data["code"].startswith("OBR-")
    assert response.data["cpf"] == "52998224725"
    assert "password" not in response.data
    user = User.objects.get(cpf="52998224725")
    assert user.role == Role.WORKER
    assert user.check_password("Senha@12345")


def test_duplicate_cpf_is_rejected(api_client, make_user):
    api_client.force_authenticate(make_user(Role.ADMIN))
    assert api_client.post("/api/workers/", PAYLOAD, format="json").status_code == 201
    assert api_client.post("/api/workers/", PAYLOAD, format="json").status_code == 400


def test_invalid_cpf_is_rejected(api_client, make_user):
    api_client.force_authenticate(make_user(Role.ADMIN))
    response = api_client.post("/api/workers/", {**PAYLOAD, "cpf": "11111111111"}, format="json")
    assert response.status_code == 400


def test_password_required_on_create(api_client, make_user):
    api_client.force_authenticate(make_user(Role.ADMIN))
    payload = {k: v for k, v in PAYLOAD.items() if k != "password"}
    assert api_client.post("/api/workers/", payload, format="json").status_code == 400


@pytest.mark.parametrize("role", [Role.WORKER, Role.BENEFICIARY, Role.PROVIDER])
def test_other_roles_cannot_access_workers(api_client, make_user, role):
    api_client.force_authenticate(make_user(role))
    assert api_client.get("/api/workers/").status_code == 403


def test_anonymous_cannot_access_workers(api_client):
    assert api_client.get("/api/workers/").status_code == 401


def test_admin_deactivates_worker(api_client, make_user):
    worker = make_user(Role.WORKER)
    api_client.force_authenticate(make_user(Role.ADMIN))
    response = api_client.patch(f"/api/workers/{worker.worker_profile.pk}/", {"is_active": False}, format="json")
    assert response.status_code == 200
    worker.refresh_from_db()
    assert worker.is_active is False


def test_delete_is_not_allowed(api_client, make_user):
    worker = make_user(Role.WORKER)
    api_client.force_authenticate(make_user(Role.ADMIN))
    assert api_client.delete(f"/api/workers/{worker.worker_profile.pk}/").status_code == 405
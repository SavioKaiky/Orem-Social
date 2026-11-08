import datetime

import pytest

from accounts.models import Role
from accounts.tests.helpers import generate_cpf
from members.models import Dependent

URL = "/api/dependents/"
BODY = {
    "full_name": "Pedro",
    "birth_date": "2012-03-04",
    "relationship": "child",
    "cpf": generate_cpf("777888999"),
    "email": "pedro@example.com",
}


def _make_dependent(beneficiary, **extra):
    data = {"full_name": "Dep", "birth_date": datetime.date(2010, 1, 1), "relationship": "child"}
    data.update(extra)
    return Dependent.objects.create(beneficiary=beneficiary, **data)


def test_beneficiary_creates_dependent_in_own_profile(api_client, make_beneficiary):
    mine = make_beneficiary()
    other = make_beneficiary()
    api_client.force_authenticate(mine.user)
    # Mesmo informando outro titular no corpo, o vínculo é sempre com o próprio perfil
    response = api_client.post(URL, {**BODY, "beneficiary": other.pk}, format="json")
    assert response.status_code == 201
    assert Dependent.objects.get(pk=response.data["id"]).beneficiary == mine


@pytest.mark.parametrize("field", ["cpf", "email"])
def test_dependent_requires_cpf_and_email(api_client, make_beneficiary, field):
    api_client.force_authenticate(make_beneficiary().user)
    body = BODY.copy()
    del body[field]
    response = api_client.post(URL, body, format="json")
    assert response.status_code == 400
    assert field in response.data


def test_invalid_relationship_is_rejected(api_client, make_beneficiary):
    api_client.force_authenticate(make_beneficiary().user)
    assert api_client.post(URL, {**BODY, "relationship": "amigo"}, format="json").status_code == 400


def test_duplicate_dependent_cpf_is_rejected(api_client, make_beneficiary):
    api_client.force_authenticate(make_beneficiary().user)
    body = {**BODY, "cpf": generate_cpf("777888999")}
    assert api_client.post(URL, body, format="json").status_code == 201
    assert api_client.post(URL, body, format="json").status_code == 400


def test_admin_must_inform_beneficiary(api_client, make_user, make_beneficiary):
    profile = make_beneficiary()
    api_client.force_authenticate(make_user(Role.ADMIN))
    assert api_client.post(URL, BODY, format="json").status_code == 400
    response = api_client.post(URL, {**BODY, "beneficiary": profile.pk}, format="json")
    assert response.status_code == 201


@pytest.mark.parametrize("role", [Role.WORKER, Role.BISHOP, Role.PROVIDER])
def test_other_roles_cannot_create(api_client, make_user, make_beneficiary, role):
    profile = make_beneficiary()
    api_client.force_authenticate(make_user(role))
    response = api_client.post(URL, {**BODY, "beneficiary": profile.pk}, format="json")
    assert response.status_code == 403


def test_worker_lists_only_own_dependents(api_client, make_user, make_beneficiary):
    worker = make_user(Role.WORKER)
    _make_dependent(make_beneficiary(worker=worker.worker_profile))
    _make_dependent(make_beneficiary())
    api_client.force_authenticate(worker)
    assert api_client.get(URL).data["count"] == 1


def test_bishop_reads_all_dependents(api_client, make_user, make_beneficiary):
    _make_dependent(make_beneficiary())
    _make_dependent(make_beneficiary())
    api_client.force_authenticate(make_user(Role.BISHOP))
    assert api_client.get(URL).data["count"] == 2


def test_other_beneficiary_cannot_see_dependent(api_client, make_beneficiary):
    dependent = _make_dependent(make_beneficiary())
    api_client.force_authenticate(make_beneficiary().user)
    assert api_client.get(f"{URL}{dependent.pk}/").status_code == 404
    assert api_client.patch(f"{URL}{dependent.pk}/", {"full_name": "X"}, format="json").status_code == 404


def test_delete_deactivates_dependent(api_client, make_beneficiary):
    profile = make_beneficiary()
    dependent = _make_dependent(profile)
    api_client.force_authenticate(profile.user)
    assert api_client.delete(f"{URL}{dependent.pk}/").status_code == 204
    dependent.refresh_from_db()
    assert dependent.is_active is False
    assert api_client.get(URL).data["count"] == 0
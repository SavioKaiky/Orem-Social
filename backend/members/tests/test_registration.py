import pytest

from accounts.models import Role, User
from accounts.tests.helpers import generate_cpf
from members.models import BeneficiaryProfile, BeneficiaryStatus, Dependent, TermsAcceptance, TermsVersion

URL = "/api/beneficiaries/register/"


@pytest.fixture
def payload(make_user):
    worker = make_user(Role.WORKER).worker_profile
    return {
        "cpf": generate_cpf("111222333"),
        "full_name": "Maria Silva",
        "phone": "62999990000",
        "email": "maria@example.com",
        "password": "Orem#Social2026",
        "birth_date": "1985-04-20",
        "city": "Goiânia",
        "state": "GO",
        "worker_code": worker.code,
        "accept_terms": True,
        "dependents": [
            {"full_name": "João Silva", "birth_date": "2010-06-01", "relationship": "child"},
            {
                "full_name": "Ana Silva",
                "birth_date": "1960-02-10",
                "cpf": generate_cpf("444555666"),
                "relationship": "parent",
            },
        ],
    }


def test_terms_are_public(api_client, current_terms):
    response = api_client.get("/api/terms/current/")
    assert response.status_code == 200
    assert response.data["version"] == "teste-1.0"


def test_register_creates_everything(api_client, current_terms, payload):
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 201
    assert "password" not in response.data
    assert response.data["group"] == "OREM/GO"
    assert response.data["worker_code"] == payload["worker_code"]
    assert len(response.data["dependents"]) == 2

    user = User.objects.get(cpf=payload["cpf"])
    assert user.role == Role.BENEFICIARY
    assert user.check_password(payload["password"])
    profile = BeneficiaryProfile.objects.get(user=user)
    assert profile.status == BeneficiaryStatus.PENDING
    assert profile.worker.code == payload["worker_code"]
    assert Dependent.objects.filter(beneficiary=profile).count() == 2
    acceptance = TermsAcceptance.objects.get(user=user)
    assert acceptance.terms.version == "teste-1.0"


def test_registered_user_can_login(api_client, current_terms, payload):
    api_client.post(URL, payload, format="json")
    response = api_client.post(
        "/api/auth/login/", {"cpf": payload["cpf"], "password": payload["password"]}, format="json"
    )
    assert response.status_code == 200
    assert response.data["user"]["role"] == Role.BENEFICIARY


def test_terms_must_be_accepted(api_client, current_terms, payload):
    payload["accept_terms"] = False
    assert api_client.post(URL, payload, format="json").status_code == 400
    assert not User.objects.filter(cpf=payload["cpf"]).exists()


def test_worker_code_is_required(api_client, current_terms, payload):
    del payload["worker_code"]
    assert api_client.post(URL, payload, format="json").status_code == 400


def test_unknown_worker_code_is_rejected(api_client, current_terms, payload):
    payload["worker_code"] = "OBR-999"
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "worker_code" in response.data


def test_invalid_state_is_rejected(api_client, current_terms, payload):
    payload["state"] = "XX"
    assert api_client.post(URL, payload, format="json").status_code == 400


def test_future_birth_date_is_rejected(api_client, current_terms, payload):
    payload["birth_date"] = "2999-01-01"
    assert api_client.post(URL, payload, format="json").status_code == 400


def test_duplicate_cpf_is_rejected(api_client, current_terms, payload):
    assert api_client.post(URL, payload, format="json").status_code == 201
    assert api_client.post(URL, payload, format="json").status_code == 400


def test_repeated_dependent_cpf_is_rejected(api_client, current_terms, payload):
    repeated = generate_cpf("444555666")
    for dependent in payload["dependents"]:
        dependent["cpf"] = repeated
    assert api_client.post(URL, payload, format="json").status_code == 400


def test_register_fails_without_current_terms(api_client, payload):
    TermsVersion.objects.update(is_current=False)
    assert api_client.post(URL, payload, format="json").status_code == 400
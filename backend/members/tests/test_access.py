import pytest
from django.utils import timezone

from accounts.models import Role
from billing.models import Payment, PaymentPurpose, PaymentStatus
from members.models import BeneficiaryStatus, State


def test_anonymous_has_no_access(api_client):
    assert api_client.get("/api/beneficiaries/").status_code == 401


def test_provider_has_no_access(api_client, make_user):
    api_client.force_authenticate(make_user(Role.PROVIDER))
    assert api_client.get("/api/beneficiaries/").status_code == 403


def test_beneficiary_sees_only_self(api_client, make_beneficiary):
    mine = make_beneficiary()
    make_beneficiary()
    api_client.force_authenticate(mine.user)
    response = api_client.get("/api/beneficiaries/")
    assert response.data["count"] == 1
    assert response.data["results"][0]["cpf"] == mine.user.cpf


def test_worker_sees_only_own_beneficiaries(api_client, make_user, make_beneficiary):
    worker_a = make_user(Role.WORKER)
    worker_b = make_user(Role.WORKER)
    make_beneficiary(worker=worker_a.worker_profile)
    make_beneficiary(worker=worker_a.worker_profile)
    make_beneficiary(worker=worker_b.worker_profile)
    api_client.force_authenticate(worker_a)
    assert api_client.get("/api/beneficiaries/").data["count"] == 2


@pytest.mark.parametrize("role", [Role.ADMIN, Role.BISHOP])
def test_admin_and_bishop_see_everything(api_client, make_user, make_beneficiary, role):
    for _ in range(3):
        make_beneficiary()
    api_client.force_authenticate(make_user(role))
    assert api_client.get("/api/beneficiaries/").data["count"] == 3


def test_filter_by_state(api_client, make_user, make_beneficiary):
    make_beneficiary(state=State.GO)
    make_beneficiary(state=State.SP)
    api_client.force_authenticate(make_user(Role.ADMIN))
    response = api_client.get("/api/beneficiaries/?state=sp")
    assert response.data["count"] == 1
    assert response.data["results"][0]["group"] == "OREM/SP"


def test_beneficiary_updates_own_contact(api_client, make_beneficiary):
    profile = make_beneficiary()
    api_client.force_authenticate(profile.user)
    response = api_client.patch(
        f"/api/beneficiaries/{profile.pk}/", {"city": "Anápolis", "phone": "62911112222"}, format="json"
    )
    assert response.status_code == 200
    profile.refresh_from_db()
    profile.user.refresh_from_db()
    assert profile.city == "Anápolis"
    assert profile.user.phone == "62911112222"


def test_beneficiary_cannot_change_status(api_client, make_beneficiary):
    profile = make_beneficiary()
    api_client.force_authenticate(profile.user)
    api_client.patch(f"/api/beneficiaries/{profile.pk}/", {"status": "active"}, format="json")
    profile.refresh_from_db()
    assert profile.status == BeneficiaryStatus.PENDING


def test_beneficiary_cannot_touch_another(api_client, make_beneficiary):
    mine = make_beneficiary()
    other = make_beneficiary()
    api_client.force_authenticate(mine.user)
    response = api_client.patch(f"/api/beneficiaries/{other.pk}/", {"city": "X"}, format="json")
    assert response.status_code == 404


@pytest.mark.parametrize("role", [Role.BISHOP, Role.WORKER])
def test_bishop_and_worker_are_read_only(api_client, make_user, make_beneficiary, role):
    profile = make_beneficiary()
    user = make_user(role)
    api_client.force_authenticate(user)
    response = api_client.patch(f"/api/beneficiaries/{profile.pk}/", {"city": "X"}, format="json")
    assert response.status_code == 403


def test_admin_can_edit(api_client, make_user, make_beneficiary):
    profile = make_beneficiary()
    api_client.force_authenticate(make_user(Role.ADMIN))
    response = api_client.patch(f"/api/beneficiaries/{profile.pk}/", {"city": "Rio Verde"}, format="json")
    assert response.status_code == 200


def test_summary_groups_by_state(api_client, make_user, make_beneficiary):
    make_beneficiary(state=State.GO)
    make_beneficiary(state=State.GO, status=BeneficiaryStatus.ACTIVE)
    make_beneficiary(state=State.DF)
    api_client.force_authenticate(make_user(Role.ADMIN))
    data = api_client.get("/api/beneficiaries/summary/").data
    assert data["total"] == 3
    assert [g["group"] for g in data["groups"]] == ["OREM/DF", "OREM/GO"]
    assert data["groups"][1]["total"] == 2
    assert data["groups"][1]["by_status"] == {"pending": 1, "active": 1}


def test_summary_is_scoped_for_worker(api_client, make_user, make_beneficiary):
    worker = make_user(Role.WORKER)
    make_beneficiary(worker=worker.worker_profile)
    make_beneficiary()
    api_client.force_authenticate(worker)
    assert api_client.get("/api/beneficiaries/summary/").data["total"] == 1


def test_worker_retention_counts_each_confirmed_contributor_once(api_client, make_user, make_beneficiary):
    worker = make_user(Role.WORKER)
    active = make_beneficiary(worker=worker.worker_profile, status=BeneficiaryStatus.ACTIVE)
    inactive = make_beneficiary(worker=worker.worker_profile, status=BeneficiaryStatus.INACTIVE)
    pending = make_beneficiary(worker=worker.worker_profile)
    active_without_contribution = make_beneficiary(
        worker=worker.worker_profile, status=BeneficiaryStatus.ACTIVE
    )
    other = make_beneficiary(status=BeneficiaryStatus.ACTIVE)
    for index, (beneficiary, purpose, status) in enumerate([
        (active, PaymentPurpose.CONTRIBUTION, PaymentStatus.PAID),
        (active, PaymentPurpose.CONTRIBUTION, PaymentStatus.PAID),
        (inactive, PaymentPurpose.CONTRIBUTION, PaymentStatus.PAID),
        (pending, PaymentPurpose.CONTRIBUTION, PaymentStatus.PENDING),
        (active_without_contribution, PaymentPurpose.DONATION, PaymentStatus.PAID),
        (other, PaymentPurpose.CONTRIBUTION, PaymentStatus.PAID),
    ]):
        Payment.objects.create(
            beneficiary=beneficiary,
            purpose=purpose,
            status=status,
            amount=50,
            txid=f"retention-{index}",
            expires_at=timezone.now(),
            paid_at=timezone.now() if status == PaymentStatus.PAID else None,
        )

    api_client.force_authenticate(worker)
    response = api_client.get("/api/beneficiaries/summary/")
    assert response.data["total"] == 4
    assert response.data["retention"] == {
        "contributors": 2,
        "active_contributors": 1,
        "percentage": 50.0,
    }


def test_worker_retention_without_confirmed_contributions(api_client, make_user, make_beneficiary):
    worker = make_user(Role.WORKER)
    make_beneficiary(worker=worker.worker_profile)
    api_client.force_authenticate(worker)
    response = api_client.get("/api/beneficiaries/summary/")
    assert response.data["retention"] == {
        "contributors": 0,
        "active_contributors": 0,
        "percentage": None,
    }


def test_summary_forbidden_for_beneficiary(api_client, make_beneficiary):
    api_client.force_authenticate(make_beneficiary().user)
    assert api_client.get("/api/beneficiaries/summary/").status_code == 403
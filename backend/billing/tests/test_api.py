from decimal import Decimal

import pytest
from django.utils import timezone

from accounts.models import Role
from billing.models import (
    Notification,
    NotificationKind,
    Payment,
    PaymentStatus,
    Subscription,
    UnidentifiedPayment,
)
from billing.services import create_contribution_charge
from members.models import BeneficiaryStatus

WEBHOOK = "/api/billing/webhook/pix/"


def _webhook_body(payment, amount=None, e2e="E2026110912000000000000001"):
    return {
        "pix": [
            {
                "endToEndId": e2e,
                "txid": payment.txid,
                "valor": str(amount or payment.amount),
                "horario": timezone.now().isoformat(),
            }
        ]
    }


def test_payment_methods_highlight_automatic(api_client, make_beneficiary):
    api_client.force_authenticate(make_beneficiary().user)
    data = api_client.get("/api/billing/payment-methods/").data
    automatic = next(m for m in data if m["code"] == "pix_automatic")
    manual = next(m for m in data if m["code"] == "pix_manual")
    assert automatic["recommended"] is True and manual["recommended"] is False
    assert automatic["available"] is False  # só liga quando o BB confirmar o acesso
    assert manual["available"] is True


def test_beneficiary_generates_charge(api_client, make_beneficiary):
    api_client.force_authenticate(make_beneficiary().user)
    first = api_client.post("/api/billing/charges/")
    second = api_client.post("/api/billing/charges/")
    assert first.status_code == 201
    assert first.data["status"] == "pending"
    assert first.data["amount"] == "32.42"
    assert first.data["pix_copy_paste"].startswith("FAKE-PIX")
    assert second.data["txid"] == first.data["txid"]


@pytest.mark.parametrize("role", [Role.WORKER, Role.BISHOP, Role.ADMIN, Role.PROVIDER])
def test_only_beneficiary_generates_charge(api_client, make_user, role):
    api_client.force_authenticate(make_user(role))
    assert api_client.post("/api/billing/charges/").status_code == 403


def test_billing_summary_before_first_payment(api_client, make_beneficiary):
    api_client.force_authenticate(make_beneficiary().user)
    data = api_client.get("/api/billing/me/").data
    assert data["status"] == BeneficiaryStatus.PENDING
    assert data["is_current"] is False
    assert data["can_renew"] is True
    assert data["next_amount"] == Decimal("32.42")


def test_webhook_confirms_payment_and_activates(api_client, make_beneficiary, settings):
    settings.PIX_WEBHOOK_SECRET = "segredo"
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary)
    response = api_client.post(f"{WEBHOOK}?hmac=segredo", _webhook_body(payment), format="json")
    assert response.status_code == 200
    payment.refresh_from_db()
    beneficiary.refresh_from_db()
    assert payment.status == PaymentStatus.PAID
    assert beneficiary.status == BeneficiaryStatus.ACTIVE

    api_client.force_authenticate(beneficiary.user)
    assert api_client.get("/api/billing/me/").data["is_current"] is True


def test_webhook_is_idempotent(api_client, make_beneficiary, settings):
    settings.PIX_WEBHOOK_SECRET = "segredo"
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary)
    body = _webhook_body(payment)

    api_client.post(f"{WEBHOOK}?hmac=segredo", body, format="json")
    # Busca no banco: o objeto em cache do beneficiário ainda estaria desatualizado
    covered_after_first = Subscription.objects.get(beneficiary=beneficiary).covered_until
    api_client.post(f"{WEBHOOK}?hmac=segredo", body, format="json")
    covered_after_second = Subscription.objects.get(beneficiary=beneficiary).covered_until

    assert covered_after_first is not None
    assert covered_after_second == covered_after_first
    assert Payment.objects.filter(status=PaymentStatus.PAID).count() == 1


def test_webhook_rejects_wrong_secret(api_client, make_beneficiary, settings):
    settings.PIX_WEBHOOK_SECRET = "segredo"
    payment = create_contribution_charge(make_beneficiary())
    response = api_client.post(f"{WEBHOOK}?hmac=errado", _webhook_body(payment), format="json")
    assert response.status_code == 403
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.PENDING


def test_webhook_without_configured_secret_is_rejected_in_production(
    api_client, make_beneficiary, settings
):
    settings.PIX_WEBHOOK_SECRET = ""
    settings.DEBUG = False
    payment = create_contribution_charge(make_beneficiary())
    assert api_client.post(WEBHOOK, _webhook_body(payment), format="json").status_code == 403


def test_webhook_unknown_txid_is_queued_for_admin(api_client, db, settings):
    settings.PIX_WEBHOOK_SECRET = "segredo"
    body = {"pix": [{"endToEndId": "E1", "txid": "desconhecido", "valor": "32.42"}]}
    response = api_client.post(f"{WEBHOOK}?hmac=segredo", body, format="json")
    assert response.status_code == 200
    assert UnidentifiedPayment.objects.count() == 1
    assert not Notification.objects.filter(kind=NotificationKind.UNIDENTIFIED_PAYMENT).exists()


def test_webhook_wrong_amount_notifies_beneficiary_once(api_client, make_beneficiary, settings):
    settings.PIX_WEBHOOK_SECRET = "segredo"
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary)
    body = _webhook_body(payment, amount=Decimal("10.00"), e2e="E1")

    for _ in range(2):
        response = api_client.post(f"{WEBHOOK}?hmac=segredo", body, format="json")
        assert response.status_code == 200

    notification = Notification.objects.get(kind=NotificationKind.UNIDENTIFIED_PAYMENT)
    assert notification.user == beneficiary.user
    assert notification.title == "Não identificamos seu pagamento"
    assert Notification.objects.filter(kind=NotificationKind.UNIDENTIFIED_PAYMENT).count() == 1
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.PENDING


def test_payments_list_is_scoped(api_client, make_user, make_beneficiary):
    mine = make_beneficiary()
    create_contribution_charge(mine)
    create_contribution_charge(make_beneficiary())

    api_client.force_authenticate(mine.user)
    assert api_client.get("/api/billing/payments/").data["count"] == 1
    api_client.force_authenticate(make_user(Role.ADMIN))
    assert api_client.get("/api/billing/payments/").data["count"] == 2
    api_client.force_authenticate(make_user(Role.BISHOP))
    assert api_client.get("/api/billing/payments/").data["count"] == 2
    api_client.force_authenticate(make_user(Role.WORKER))
    assert api_client.get("/api/billing/payments/").status_code == 403


def test_simulate_payment_only_in_debug(api_client, make_beneficiary, settings):
    beneficiary = make_beneficiary()
    api_client.force_authenticate(beneficiary.user)
    txid = api_client.post("/api/billing/charges/").data["txid"]

    settings.DEBUG = False
    assert api_client.post("/api/billing/dev/simulate-payment/", {"txid": txid}).status_code == 404

    settings.DEBUG = True
    response = api_client.post("/api/billing/dev/simulate-payment/", {"txid": txid})
    assert response.status_code == 200
    assert response.data["status"] == "paid"


def test_notifications_are_private(api_client, make_user):
    owner = make_user()
    other = make_user()
    Notification.objects.create(
        user=owner, kind=NotificationKind.DUE_SOON, title="t", body="b", dedupe_key="x-1"
    )
    api_client.force_authenticate(owner)
    assert api_client.get("/api/billing/notifications/").data["count"] == 1
    api_client.force_authenticate(other)
    assert api_client.get("/api/billing/notifications/").data["count"] == 0
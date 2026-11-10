import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest

from billing.models import Notification, NotificationKind, Payment, PaymentStatus, UnidentifiedPayment
from billing.providers.base import PixEvent
from billing.providers.fake import FakePixProvider
from billing.services import (
    BillingError,
    confirm_payment,
    create_contribution_charge,
    get_subscription,
    reconcile_pending_payments,
    run_status_sync,
)
from members.models import BeneficiaryStatus, Dependent

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=dt_timezone.utc)


def days(n):
    return timedelta(days=n)


def pay(beneficiary, at):
    """Gera a cobrança e confirma o pagamento na data informada."""
    payment = create_contribution_charge(beneficiary, now=at)
    confirm_payment(
        txid=payment.txid, end_to_end_id=f"E{uuid.uuid4().hex}", amount=payment.amount, paid_at=at
    )
    return payment


def test_first_payment_starts_cycle(make_beneficiary):
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    subscription = get_subscription(beneficiary)
    beneficiary.refresh_from_db()
    assert subscription.covered_until == T0 + days(30)
    assert subscription.streak_started_at == T0
    assert beneficiary.status == BeneficiaryStatus.ACTIVE


@pytest.mark.parametrize("offset", [25, 30, 33, 35])
def test_paying_until_the_deadline_keeps_the_cycle(make_beneficiary, offset):
    # 35 dias = 30 do ciclo + 5 de tolerância: o último instante ainda vale
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    pay(beneficiary, T0 + days(offset))
    subscription = get_subscription(beneficiary)
    assert subscription.covered_until == T0 + days(60)
    assert subscription.streak_started_at == T0


def test_paying_after_the_deadline_restarts_the_cycle(make_beneficiary):
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    pay(beneficiary, T0 + days(36))
    subscription = get_subscription(beneficiary)
    assert subscription.covered_until == T0 + days(66)
    assert subscription.streak_started_at == T0 + days(36)


def test_cannot_generate_charge_too_early(make_beneficiary):
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    with pytest.raises(BillingError):
        create_contribution_charge(beneficiary, now=T0 + days(5))


def test_pending_charge_is_reused(make_beneficiary):
    beneficiary = make_beneficiary()
    first = create_contribution_charge(beneficiary, now=T0)
    second = create_contribution_charge(beneficiary, now=T0 + timedelta(hours=1))
    assert first.pk == second.pk


def test_amount_counts_active_dependents(make_beneficiary):
    beneficiary = make_beneficiary()
    for name in ("A", "B"):
        Dependent.objects.create(
            beneficiary=beneficiary, full_name=name, birth_date=T0.date(), relationship="child"
        )
    payment = create_contribution_charge(beneficiary, now=T0)
    assert payment.amount == Decimal("64.84")
    assert payment.dependents_count == 2


def test_dependent_added_mid_cycle_counts_from_next_charge(make_beneficiary):
    beneficiary = make_beneficiary()
    first = pay(beneficiary, T0)
    Dependent.objects.create(
        beneficiary=beneficiary, full_name="Novo", birth_date=T0.date(), relationship="child"
    )
    second = pay(beneficiary, T0 + days(30))
    assert first.amount == Decimal("32.42")
    assert second.amount == Decimal("48.63")


def test_confirm_is_idempotent(make_beneficiary):
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary, now=T0)
    kwargs = dict(txid=payment.txid, end_to_end_id="E123", amount=payment.amount, paid_at=T0)
    confirm_payment(**kwargs)
    confirm_payment(**kwargs)
    assert get_subscription(beneficiary).covered_until == T0 + days(30)


def test_wrong_amount_is_not_confirmed(make_beneficiary):
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary, now=T0)
    result = confirm_payment(txid=payment.txid, end_to_end_id="E999", amount=Decimal("1.00"), paid_at=T0)
    payment.refresh_from_db()
    assert result is None
    assert payment.status == PaymentStatus.PENDING
    assert UnidentifiedPayment.objects.count() == 1


def test_unknown_txid_goes_to_unidentified(db):
    assert confirm_payment(txid="naoexiste", end_to_end_id="E1", amount=Decimal("32.42"), paid_at=T0) is None
    assert UnidentifiedPayment.objects.count() == 1


@pytest.mark.parametrize(
    ("first_payment", "carence_end"),
    [
        (datetime(2026, 6, 10, 12, tzinfo=dt_timezone.utc), datetime(2026, 10, 10, 12, tzinfo=dt_timezone.utc)),
        (datetime(2026, 10, 31, 12, tzinfo=dt_timezone.utc), datetime(2027, 2, 28, 12, tzinfo=dt_timezone.utc)),
    ],
)
def test_carence_needs_four_calendar_months(make_beneficiary, first_payment, carence_end):
    beneficiary = make_beneficiary()
    for offset in (0, 30, 60, 90):
        pay(beneficiary, first_payment + days(offset))
    subscription = get_subscription(beneficiary)
    assert subscription.carence_met(carence_end - timedelta(seconds=1)) is False
    assert subscription.carence_met(carence_end) is True


def test_sync_deactivates_after_grace_and_notifies_once(make_beneficiary):
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    assert run_status_sync(now=T0 + days(34))["deactivated"] == 0
    assert run_status_sync(now=T0 + days(35))["deactivated"] == 0  # o prazo ainda vale
    assert run_status_sync(now=T0 + days(36))["deactivated"] == 1
    run_status_sync(now=T0 + days(37))
    beneficiary.refresh_from_db()
    assert beneficiary.status == BeneficiaryStatus.INACTIVE
    assert Notification.objects.filter(kind=NotificationKind.OVERDUE).count() == 1


def test_paying_again_reactivates_and_resets_carence(make_beneficiary):
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    run_status_sync(now=T0 + days(36))
    pay(beneficiary, T0 + days(37))
    beneficiary.refresh_from_db()
    assert beneficiary.status == BeneficiaryStatus.ACTIVE
    assert get_subscription(beneficiary).streak_started_at == T0 + days(37)


def test_due_soon_reminder_is_sent_once(make_beneficiary):
    beneficiary = make_beneficiary()
    pay(beneficiary, T0)
    assert run_status_sync(now=T0 + days(28))["reminders"] == 1
    assert run_status_sync(now=T0 + days(28))["reminders"] == 0
    assert Notification.objects.filter(kind=NotificationKind.DUE_SOON).count() == 1


def test_old_pending_charges_expire(make_beneficiary):
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary, now=T0)
    assert run_status_sync(now=T0 + days(2))["expired_charges"] == 1
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.EXPIRED


class _PaidProvider(FakePixProvider):
    """Simula um banco que já recebeu o PIX, mas cujo webhook se perdeu."""

    def get_payment(self, txid):
        return PixEvent(txid=txid, end_to_end_id=f"E{uuid.uuid4().hex}", amount=Decimal("32.42"), paid_at=T0)


def test_reconcile_confirms_payment_when_webhook_was_lost(make_beneficiary, monkeypatch):
    beneficiary = make_beneficiary()
    payment = create_contribution_charge(beneficiary, now=T0)
    monkeypatch.setattr("billing.services.get_provider", lambda: _PaidProvider())
    assert reconcile_pending_payments(now=T0 + timedelta(hours=1)) == 1
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.PAID
"""Regras de cobrança. Todas as funções aceitam `now`/`paid_at` para serem testáveis."""
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from members.models import BeneficiaryProfile, BeneficiaryStatus

from .models import (
    Notification,
    NotificationKind,
    Payment,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    PricingConfig,
    Subscription,
    UnidentifiedPayment,
)
from .providers import get_provider
from .rules import (
    CHARGE_EXPIRATION_HOURS,
    CYCLE_DAYS,
    DUE_SOON_DAYS,
    GRACE_DAYS,
    RENEWAL_WINDOW_DAYS,
)


class BillingError(Exception):
    """Erro de regra de negócio, com mensagem pronta para o usuário."""


def get_subscription(beneficiary):
    subscription, _ = Subscription.objects.get_or_create(beneficiary=beneficiary)
    return subscription


def monthly_amount(beneficiary, on=None):
    """Valor da mensalidade com os dependentes ativos no momento da cobrança."""
    count = beneficiary.dependents.filter(is_active=True).count()
    return PricingConfig.current(on).total_for(count), count


def can_renew(subscription, now=None):
    """A cobrança só pode ser gerada nos últimos dias do ciclo (ou se nunca pagou/estourou o prazo)."""
    now = now or timezone.now()
    if subscription.covered_until is None:
        return True
    return now >= subscription.covered_until - timedelta(days=RENEWAL_WINDOW_DAYS)


@transaction.atomic
def create_contribution_charge(beneficiary, now=None):
    now = now or timezone.now()
    # Trava a assinatura para duas chamadas simultâneas não gerarem duas cobranças
    subscription = Subscription.objects.select_for_update().get(pk=get_subscription(beneficiary).pk)
    if not can_renew(subscription, now):
        opens_at = timezone.localtime(subscription.covered_until - timedelta(days=RENEWAL_WINDOW_DAYS))
        raise BillingError(
            f"Sua contribuição está em dia. A próxima cobrança poderá ser gerada a partir de {opens_at:%d/%m/%Y}."
        )
    pending = Payment.objects.filter(
        beneficiary=beneficiary,
        purpose=PaymentPurpose.CONTRIBUTION,
        status=PaymentStatus.PENDING,
        expires_at__gt=now,
    ).first()
    if pending:
        return pending

    amount, dependents_count = monthly_amount(beneficiary)
    txid = uuid.uuid4().hex
    expires_at = now + timedelta(hours=CHARGE_EXPIRATION_HOURS)
    charge = get_provider().create_charge(
        txid=txid, amount=amount, description="Contribuição mensal Orem Social", expires_at=expires_at
    )
    return Payment.objects.create(
        beneficiary=beneficiary,
        purpose=PaymentPurpose.CONTRIBUTION,
        method=PaymentMethod.PIX_MANUAL,
        amount=amount,
        dependents_count=dependents_count,
        txid=charge.txid,
        pix_copy_paste=charge.copy_paste,
        expires_at=expires_at,
    )


def _record_unidentified(txid, end_to_end_id, amount, reason):
    UnidentifiedPayment.objects.get_or_create(
        end_to_end_id=end_to_end_id,
        defaults={"txid": txid or "", "amount": amount, "reason": reason},
    )


@transaction.atomic
def confirm_payment(*, txid, end_to_end_id, amount, paid_at):
    """
    Confirma um PIX recebido. É idempotente: o banco pode repetir o webhook sem efeito duplicado.
    Devolve o pagamento, ou None se o PIX não casou com nenhuma cobrança.
    """
    payment = Payment.objects.select_for_update().filter(txid=txid).first() if txid else None
    if payment is None:
        _record_unidentified(txid, end_to_end_id, amount, "Cobrança não encontrada para o txid informado.")
        return None
    if payment.status == PaymentStatus.PAID:
        return payment
    if amount != payment.amount:
        _record_unidentified(txid, end_to_end_id, amount, "Valor pago diferente do valor cobrado.")
        return None

    payment.status = PaymentStatus.PAID
    payment.paid_at = paid_at
    payment.paid_amount = amount
    payment.end_to_end_id = end_to_end_id
    payment.save()
    if payment.purpose == PaymentPurpose.CONTRIBUTION:
        _extend_coverage(payment.beneficiary, paid_at)
    return payment


def _extend_coverage(beneficiary, paid_at):
    """
    Pagou até o prazo máximo: o ciclo continua (soma 30 dias ao vencimento anterior).
    Passou do prazo: o ciclo reinicia na data do pagamento e a carência recomeça.
    """
    subscription = Subscription.objects.select_for_update().get(pk=get_subscription(beneficiary).pk)
    if subscription.covered_until is not None and paid_at <= subscription.grace_deadline:
        start = subscription.covered_until
    else:
        start = paid_at
        subscription.streak_started_at = paid_at
    subscription.covered_until = start + timedelta(days=CYCLE_DAYS)
    subscription.save()

    beneficiary.status = BeneficiaryStatus.ACTIVE
    beneficiary.save(update_fields=["status", "updated_at"])


def reconcile_pending_payments(now=None):
    """Consulta o banco sobre cobranças pendentes, para o caso de o webhook ter falhado."""
    now = now or timezone.now()
    provider = get_provider()
    confirmed = 0
    for payment in Payment.objects.filter(status=PaymentStatus.PENDING, expires_at__gt=now):
        event = provider.get_payment(payment.txid)
        if event and confirm_payment(
            txid=payment.txid,
            end_to_end_id=event.end_to_end_id,
            amount=event.amount,
            paid_at=event.paid_at,
        ):
            confirmed += 1
    return confirmed


@transaction.atomic
def run_status_sync(now=None):
    """Inativa quem passou do prazo, avisa vencimentos e expira cobranças antigas."""
    now = now or timezone.now()

    cutoff = now - timedelta(days=GRACE_DAYS)
    lapsed = BeneficiaryProfile.objects.filter(
        status=BeneficiaryStatus.ACTIVE, subscription__covered_until__lt=cutoff
    ).select_related("user", "subscription")
    deactivated = 0
    for beneficiary in lapsed:
        beneficiary.status = BeneficiaryStatus.INACTIVE
        beneficiary.save(update_fields=["status", "updated_at"])
        Notification.objects.get_or_create(
            dedupe_key=f"overdue-{beneficiary.pk}-{beneficiary.subscription.covered_until:%Y%m%d}",
            defaults={
                "user": beneficiary.user,
                "kind": NotificationKind.OVERDUE,
                "title": "Pagamento não identificado",
                "body": (
                    "Não identificamos o pagamento da sua contribuição em até 5 dias após o vencimento. "
                    "Seus benefícios foram suspensos. Contribua novamente para reativar; a carência recomeça."
                ),
            },
        )
        deactivated += 1

    reminders = 0
    due_soon = Subscription.objects.filter(
        beneficiary__status=BeneficiaryStatus.ACTIVE,
        covered_until__gt=now,
        covered_until__lte=now + timedelta(days=DUE_SOON_DAYS),
    ).select_related("beneficiary__user")
    for subscription in due_soon:
        _, created = Notification.objects.get_or_create(
            dedupe_key=f"due-soon-{subscription.beneficiary_id}-{subscription.covered_until:%Y%m%d}",
            defaults={
                "user": subscription.beneficiary.user,
                "kind": NotificationKind.DUE_SOON,
                "title": "Sua contribuição vence em breve",
                "body": "Pague até o vencimento para manter seus benefícios e a contagem da carência.",
            },
        )
        reminders += int(created)

    expired = Payment.objects.filter(status=PaymentStatus.PENDING, expires_at__lt=now).update(
        status=PaymentStatus.EXPIRED
    )
    return {"deactivated": deactivated, "reminders": reminders, "expired_charges": expired}
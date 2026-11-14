from calendar import monthrange
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import models
from django.utils import timezone

from accounts.models import TimeStampedModel, User
from members.models import BeneficiaryProfile

from .rules import GRACE_DAYS

CARENCE_MONTHS = 4


class PricingConfig(models.Model):
    """Valores da contribuição, derivados do salário mínimo. Cada linha vale a partir de uma data."""

    valid_from = models.DateField("Vigente desde", unique=True)
    minimum_wage = models.DecimalField("Salário mínimo (R$)", max_digits=10, decimal_places=2)
    holder_percent = models.DecimalField("% do titular", max_digits=5, decimal_places=2, default=Decimal("2.00"))
    dependent_percent = models.DecimalField("% do dependente", max_digits=5, decimal_places=2, default=Decimal("1.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "valor de contribuição"
        verbose_name_plural = "valores de contribuição"
        ordering = ["-valid_from"]

    @classmethod
    def current(cls, on=None):
        """Configuração vigente na data (hoje, por padrão)."""
        on = on or timezone.localdate()
        config = cls.objects.filter(valid_from__lte=on).order_by("-valid_from").first()
        if config is None:
            raise cls.DoesNotExist("Nenhum valor de contribuição configurado.")
        return config

    def _share(self, percent):
        value = self.minimum_wage * percent / Decimal("100")
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def holder_amount(self):
        return self._share(self.holder_percent)

    @property
    def dependent_amount(self):
        return self._share(self.dependent_percent)

    def total_for(self, dependents_count):
        return self.holder_amount + self.dependent_amount * dependents_count

    def __str__(self):
        return f"A partir de {self.valid_from}: salário mínimo R$ {self.minimum_wage}"


class Subscription(TimeStampedModel):
    """Situação de cobertura do beneficiário: até quando está pago e desde quando é contínuo."""

    beneficiary = models.OneToOneField(BeneficiaryProfile, on_delete=models.CASCADE, related_name="subscription")
    covered_until = models.DateTimeField("Coberto até", null=True, blank=True)
    # Início da adimplência contínua; é a base da carência e zera quando o prazo estoura
    streak_started_at = models.DateTimeField("Adimplente desde", null=True, blank=True)

    class Meta:
        verbose_name = "assinatura"
        verbose_name_plural = "assinaturas"

    @property
    def grace_deadline(self):
        """Prazo máximo para pagar sem perder o ciclo."""
        if self.covered_until is None:
            return None
        return self.covered_until + timedelta(days=GRACE_DAYS)

    def is_current(self, now=None):
        now = now or timezone.now()
        return self.covered_until is not None and now <= self.grace_deadline

    def carence_met(self, now=None):
        now = now or timezone.now()
        if self.streak_started_at is None or not self.is_current(now):
            return False
        start = timezone.localtime(self.streak_started_at)
        month_offset = start.month - 1 + CARENCE_MONTHS
        year = start.year + month_offset // 12
        month = month_offset % 12 + 1
        day = min(start.day, monthrange(year, month)[1])
        return now >= start.replace(year=year, month=month, day=day)

    def __str__(self):
        return f"Assinatura de {self.beneficiary}"


class PaymentPurpose(models.TextChoices):
    CONTRIBUTION = "contribution", "Contribuição mensal"
    DONATION = "donation", "Doação ao Celeiro"
    CONSULTATION = "consultation", "Consulta de telemedicina"


class PaymentMethod(models.TextChoices):
    PIX_MANUAL = "pix_manual", "PIX manual"
    PIX_AUTOMATIC = "pix_automatic", "Pix Automático"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Aguardando pagamento"
    PAID = "paid", "Pago"
    EXPIRED = "expired", "Expirado"


class Payment(TimeStampedModel):
    """Cobrança PIX. Genérica: serve à contribuição, às doações do Celeiro e às consultas."""

    beneficiary = models.ForeignKey(BeneficiaryProfile, on_delete=models.PROTECT, related_name="payments")
    purpose = models.CharField(max_length=20, choices=PaymentPurpose.choices)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.PIX_MANUAL)
    amount = models.DecimalField("Valor", max_digits=10, decimal_places=2)
    # Quantos dependentes entraram no cálculo (registro para auditoria)
    dependents_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)
    txid = models.CharField(max_length=35, unique=True)
    pix_copy_paste = models.TextField("PIX copia e cola", blank=True)
    expires_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    end_to_end_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_purpose_display()} R$ {self.amount} ({self.get_status_display()})"


class UnidentifiedPayment(models.Model):
    """PIX recebido que não casou com nenhuma cobrança (txid desconhecido ou valor diferente)."""

    txid = models.CharField(max_length=64, blank=True)
    end_to_end_id = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200)
    resolved = models.BooleanField("Resolvido", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pagamento não identificado"
        verbose_name_plural = "pagamentos não identificados"
        ordering = ["-created_at"]

    def __str__(self):
        return f"R$ {self.amount} - {self.reason}"


class NotificationKind(models.TextChoices):
    DUE_SOON = "due_soon", "Vencimento próximo"
    OVERDUE = "overdue", "Pagamento não identificado"
    UNIDENTIFIED_PAYMENT = "unidentified_payment", "PIX não identificado"


class Notification(models.Model):
    """Notificação interna. O envio por push (Firebase) entra em uma etapa posterior."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=NotificationKind.choices)
    title = models.CharField(max_length=120)
    body = models.TextField()
    # Garante uma única notificação por evento, mesmo se o job rodar várias vezes
    dedupe_key = models.CharField(max_length=100, unique=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        ordering = ["-created_at"]
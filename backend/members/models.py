from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Role, TimeStampedModel, User, WorkerProfile
from accounts.validators import validate_cpf

from .validators import validate_not_future


class State(models.TextChoices):
    """UF do beneficiário; define o grupo regional (OREM/GO, OREM/DF...)."""

    AC = "AC", "Acre"
    AL = "AL", "Alagoas"
    AP = "AP", "Amapá"
    AM = "AM", "Amazonas"
    BA = "BA", "Bahia"
    CE = "CE", "Ceará"
    DF = "DF", "Distrito Federal"
    ES = "ES", "Espírito Santo"
    GO = "GO", "Goiás"
    MA = "MA", "Maranhão"
    MT = "MT", "Mato Grosso"
    MS = "MS", "Mato Grosso do Sul"
    MG = "MG", "Minas Gerais"
    PA = "PA", "Pará"
    PB = "PB", "Paraíba"
    PR = "PR", "Paraná"
    PE = "PE", "Pernambuco"
    PI = "PI", "Piauí"
    RJ = "RJ", "Rio de Janeiro"
    RN = "RN", "Rio Grande do Norte"
    RS = "RS", "Rio Grande do Sul"
    RO = "RO", "Rondônia"
    RR = "RR", "Roraima"
    SC = "SC", "Santa Catarina"
    SP = "SP", "São Paulo"
    SE = "SE", "Sergipe"
    TO = "TO", "Tocantins"


class BeneficiaryStatus(models.TextChoices):
    PENDING = "pending", "Aguardando pagamento"
    ACTIVE = "active", "Ativo"
    INACTIVE = "inactive", "Inativo"


class Relationship(models.TextChoices):
    SPOUSE = "spouse", "Cônjuge"
    CHILD = "child", "Filho(a)"
    PARENT = "parent", "Pai/Mãe"
    PARENT_IN_LAW = "parent_in_law", "Sogro(a)"
    OTHER = "other", "Outro"


class TermsVersion(TimeStampedModel):
    """Versão dos Termos de Uso. Só uma versão pode ser a vigente."""

    version = models.CharField("Versão", max_length=30, unique=True)
    content = models.TextField("Texto")
    is_current = models.BooleanField("Vigente", default=False)

    class Meta:
        verbose_name = "versão dos termos"
        verbose_name_plural = "versões dos termos"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_current"], condition=Q(is_current=True), name="single_current_terms"
            )
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_current:
                # Ao publicar uma nova versão, a anterior deixa de ser vigente
                TermsVersion.objects.exclude(pk=self.pk).filter(is_current=True).update(is_current=False)
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Termos {self.version}"


class TermsAcceptance(models.Model):
    """Registro do aceite digital: quem aceitou, qual versão, quando e de qual IP."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="terms_acceptances")
    terms = models.ForeignKey(TermsVersion, on_delete=models.PROTECT, related_name="acceptances")
    accepted_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "aceite dos termos"
        verbose_name_plural = "aceites dos termos"
        constraints = [models.UniqueConstraint(fields=["user", "terms"], name="unique_acceptance_per_version")]


class BeneficiaryProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="beneficiary_profile")
    # PROTECT: não dá para apagar um obreiro que ainda tem beneficiários
    worker = models.ForeignKey(WorkerProfile, on_delete=models.PROTECT, related_name="beneficiaries")
    birth_date = models.DateField("Data de nascimento", validators=[validate_not_future])
    city = models.CharField("Cidade", max_length=100)
    state = models.CharField("Estado", max_length=2, choices=State.choices, db_index=True)
    status = models.CharField(
        "Situação", max_length=10, choices=BeneficiaryStatus.choices, default=BeneficiaryStatus.PENDING, db_index=True
    )

    class Meta:
        verbose_name = "beneficiário"
        verbose_name_plural = "beneficiários"

    def clean(self):
        user = getattr(self, "user", None)
        if user is not None and user.role != Role.BENEFICIARY:
            raise ValidationError({"user": "O usuário precisa ter o papel 'Beneficiário'."})

    @property
    def group_name(self):
        """Grupo regional derivado do estado, ex.: OREM/GO."""
        return f"OREM/{self.state}"

    def __str__(self):
        return f"{self.user.full_name} ({self.group_name})"


class Dependent(TimeStampedModel):
    """Dependente cadastrado no perfil do titular (sem login próprio)."""

    beneficiary = models.ForeignKey(BeneficiaryProfile, on_delete=models.CASCADE, related_name="dependents")
    full_name = models.CharField("Nome completo", max_length=150)
    birth_date = models.DateField("Data de nascimento", validators=[validate_not_future])
    cpf = models.CharField("CPF", max_length=11, blank=True, default="", validators=[validate_cpf])
    email = models.EmailField("E-mail", blank=True, default="")
    relationship = models.CharField("Parentesco", max_length=20, choices=Relationship.choices)
    # Remoção é lógica: preserva o histórico usado em cobrança e prebenda
    is_active = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "dependente"
        verbose_name_plural = "dependentes"
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["cpf"], condition=~Q(cpf=""), name="unique_dependent_cpf_when_set"
            )
        ]

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"
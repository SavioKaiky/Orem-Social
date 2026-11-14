from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .validators import normalize_phone, only_digits, validate_cpf


class Role(models.TextChoices):
    """Papéis de acesso. Cada papel tem seu perfil (tabela) próprio."""

    ADMIN = "admin", "Administrador"
    BISHOP = "bishop", "Bispo Presidente"
    WORKER = "worker", "Obreiro multiplicador"
    BENEFICIARY = "beneficiary", "Beneficiário"
    PROVIDER = "provider", "Prestador de serviço"


class ServiceType(models.TextChoices):
    TELEMEDICINE = "telemedicine", "Telemedicina"
    FUNERAL = "funeral", "Proteção funerária"
    CELEIRO = "celeiro", "Celeiro da OREM"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, cpf, password, **extra_fields):
        cpf = only_digits(cpf)
        validate_cpf(cpf)
        if not extra_fields.get("full_name"):
            raise ValueError("O nome completo é obrigatório.")
        user = self.model(cpf=cpf, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, cpf, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.BENEFICIARY)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(cpf, password, **extra_fields)

    def create_superuser(self, cpf, password=None, **extra_fields):
        # Superusuário sempre é Admin, com acesso total
        extra_fields.update(role=Role.ADMIN, is_staff=True, is_superuser=True)
        return self._create_user(cpf, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Tabela única de login. Os dados específicos de cada papel ficam nos perfis."""

    cpf = models.CharField("CPF", max_length=11, unique=True, validators=[validate_cpf])
    full_name = models.CharField("Nome completo", max_length=150)
    email = models.EmailField("E-mail", blank=True)
    phone = models.CharField("Telefone", max_length=20, blank=True)
    role = models.CharField("Papel", max_length=20, choices=Role.choices, default=Role.BENEFICIARY, db_index=True)
    is_active = models.BooleanField("Ativo", default=True)
    is_staff = models.BooleanField("Acesso ao Django Admin", default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "cpf"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["phone"], condition=~Q(phone=""), name="unique_user_phone_when_set"
            ),
        ]

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


def _ensure_role(user, role):
    """Garante que o perfil só seja ligado a um usuário do papel correspondente."""
    if user is not None and user.role != role:
        raise ValidationError({"user": f"O usuário precisa ter o papel '{Role(role).label}'."})


class BishopProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="bishop_profile")

    class Meta:
        verbose_name = "perfil de Bispo"
        verbose_name_plural = "perfis de Bispo"

    def clean(self):
        _ensure_role(getattr(self, "user", None), Role.BISHOP)

    def __str__(self):
        return f"Bispo: {self.user.full_name}"


class WorkerProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="worker_profile")
    # Código único usado pelo beneficiário no cadastro (ex.: OBR-01)
    code = models.CharField("Código", max_length=20, unique=True, null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "obreiro multiplicador"
        verbose_name_plural = "obreiros multiplicadores"
        ordering = ["id"]

    def clean(self):
        _ensure_role(getattr(self, "user", None), Role.WORKER)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.code:
            # O código nasce do id, o que evita colisão em cadastros simultâneos
            self.code = f"OBR-{self.pk:02d}"
            super().save(update_fields=["code"])

    def __str__(self):
        return f"{self.code} - {self.user.full_name}"


class ProviderProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="provider_profile")
    company_name = models.CharField("Empresa", max_length=150)
    service_type = models.CharField("Serviço", max_length=20, choices=ServiceType.choices)

    class Meta:
        verbose_name = "prestador de serviço"
        verbose_name_plural = "prestadores de serviço"

    def clean(self):
        _ensure_role(getattr(self, "user", None), Role.PROVIDER)

    def __str__(self):
        return f"{self.company_name} ({self.get_service_type_display()})"
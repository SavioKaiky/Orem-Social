import ipaddress

from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from accounts.models import Role, User, WorkerProfile
from accounts.validators import only_digits
from accounts.validators import validate_cpf as check_cpf

from .models import (
    BeneficiaryProfile,
    Dependent,
    State,
    TermsAcceptance,
    TermsVersion,
)
from .validators import validate_not_future


def _client_ip(request):
    """IP real do cliente, para registrar no aceite dos termos.

    Atrás do túnel da Cloudflare o REMOTE_ADDR é o do próprio túnel; o IP de quem fez a
    requisição vem no cabeçalho CF-Connecting-IP. Só aceitamos valores que sejam um IP válido,
    para um cabeçalho malformado nunca quebrar o cadastro (o campo do banco só guarda IPs).
    """
    candidates = (request.META.get("HTTP_CF_CONNECTING_IP"), request.META.get("REMOTE_ADDR"))
    for raw in candidates:
        if not raw:
            continue
        try:
            return str(ipaddress.ip_address(raw.strip()))
        except ValueError:
            continue
    return None

class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsVersion
        fields = ["version", "content", "created_at"]


class DependentInputSerializer(serializers.ModelSerializer):
    """Dados do dependente. Usado no cadastro do titular e como base da API de dependentes."""

    cpf = serializers.CharField(validators=[check_cpf])
    email = serializers.EmailField(max_length=254)

    class Meta:
        model = Dependent
        fields = ["full_name", "birth_date", "cpf", "email", "relationship"]

    def validate_cpf(self, value):
        cpf = only_digits(value)
        queryset = Dependent.objects.filter(cpf=cpf)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um dependente cadastrado com este CPF.")
        return cpf


class DependentSerializer(DependentInputSerializer):
    beneficiary = serializers.PrimaryKeyRelatedField(
        queryset=BeneficiaryProfile.objects.all(), required=False
    )

    class Meta(DependentInputSerializer.Meta):
        fields = ["id", "beneficiary", "full_name", "birth_date", "cpf", "email", "relationship", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        if self.instance is not None:
            # O titular de um dependente existente não muda
            attrs.pop("beneficiary", None)
            return attrs
        user = self.context["request"].user
        if user.role == Role.BENEFICIARY:
            # O beneficiário só cadastra dependentes no próprio perfil, ignorando o que vier no corpo
            attrs["beneficiary"] = user.beneficiary_profile
        elif "beneficiary" not in attrs:
            raise serializers.ValidationError({"beneficiary": "Este campo é obrigatório."})
        return attrs


class BeneficiarySerializer(serializers.ModelSerializer):
    cpf = serializers.CharField(source="user.cpf", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)
    phone = serializers.CharField(source="user.phone", required=False, max_length=20)
    worker_code = serializers.CharField(source="worker.code", read_only=True)
    group = serializers.CharField(source="group_name", read_only=True)
    dependents = serializers.SerializerMethodField()

    class Meta:
        model = BeneficiaryProfile
        fields = [
            "id", "cpf", "full_name", "email", "phone", "birth_date", "city", "state",
            "group", "status", "worker_code", "dependents", "created_at",
        ]
        # O titular só altera contato, cidade e estado; status vem do pagamento
        read_only_fields = ["id", "birth_date", "status", "created_at"]

    def get_dependents(self, obj):
        items = getattr(obj, "active_dependents", None)
        if items is None:
            items = obj.dependents.filter(is_active=True)
        return DependentSerializer(items, many=True, context=self.context).data

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()
        return instance


class BeneficiaryRegistrationSerializer(serializers.Serializer):
    """Autocadastro público: cria login, perfil, aceite dos termos e dependentes de uma vez."""

    cpf = serializers.CharField(validators=[check_cpf])
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=True, allow_blank=False)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    birth_date = serializers.DateField(validators=[validate_not_future])
    city = serializers.CharField(max_length=100)
    state = serializers.ChoiceField(choices=State.choices)
    worker_code = serializers.CharField(max_length=20)
    accept_terms = serializers.BooleanField()
    dependents = DependentInputSerializer(many=True, required=False)

    def validate_cpf(self, value):
        cpf = only_digits(value)
        if User.objects.filter(cpf=cpf).exists():
            raise serializers.ValidationError("Já existe um cadastro com este CPF.")
        return cpf

    def validate_password(self, value):
        try:
            run_password_validators(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("É preciso aceitar os Termos de Uso para se cadastrar.")
        return value

    def validate(self, attrs):
        worker = WorkerProfile.objects.filter(
            code__iexact=attrs["worker_code"].strip(), user__is_active=True
        ).first()
        if worker is None:
            raise serializers.ValidationError({"worker_code": "Código do obreiro não encontrado."})
        terms = TermsVersion.objects.filter(is_current=True).first()
        if terms is None:
            raise serializers.ValidationError("Termos de Uso indisponíveis no momento.")
        dependent_cpfs = [d["cpf"] for d in attrs.get("dependents", []) if d.get("cpf")]
        if len(dependent_cpfs) != len(set(dependent_cpfs)) or attrs["cpf"] in dependent_cpfs:
            raise serializers.ValidationError({"dependents": "CPF repetido entre titular e dependentes."})
        attrs["worker"] = worker
        attrs["terms"] = terms
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = User.objects.create_user(
            cpf=validated_data["cpf"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            role=Role.BENEFICIARY,
        )
        profile = BeneficiaryProfile.objects.create(
            user=user,
            worker=validated_data["worker"],
            birth_date=validated_data["birth_date"],
            city=validated_data["city"],
            state=validated_data["state"],
        )
        TermsAcceptance.objects.create(
            user=user, terms=validated_data["terms"], ip_address=_client_ip(request)
        )
        Dependent.objects.bulk_create(
            [Dependent(beneficiary=profile, **data) for data in validated_data.get("dependents", [])]
        )
        return profile
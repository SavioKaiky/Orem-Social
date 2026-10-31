from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role, User, WorkerProfile
from .validators import only_digits, validate_cpf


class UserSerializer(serializers.ModelSerializer):
    worker_code = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "cpf", "full_name", "email", "phone", "role", "worker_code"]
        read_only_fields = fields

    def get_worker_code(self, obj):
        return obj.worker_profile.code if hasattr(obj, "worker_profile") else None


class LoginSerializer(TokenObtainPairSerializer):
    """Login com CPF (com ou sem máscara) e senha."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        attrs[self.username_field] = only_digits(attrs[self.username_field])
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class WorkerSerializer(serializers.ModelSerializer):
    """Cadastro do obreiro: cria o usuário de login e o perfil em uma só chamada."""

    cpf = serializers.CharField(source="user.cpf", validators=[validate_cpf])
    full_name = serializers.CharField(source="user.full_name", max_length=150)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)
    phone = serializers.CharField(source="user.phone", required=False, allow_blank=True, max_length=20)
    is_active = serializers.BooleanField(source="user.is_active", required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = WorkerProfile
        fields = ["id", "code", "cpf", "full_name", "email", "phone", "is_active", "password", "created_at"]
        read_only_fields = ["id", "code", "created_at"]

    def validate_cpf(self, value):
        cpf = only_digits(value)
        queryset = User.objects.filter(cpf=cpf)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um usuário com este CPF.")
        return cpf

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Este campo é obrigatório."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, role=Role.WORKER, **user_data)
        return WorkerProfile.objects.create(user=user)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        if password:
            user.set_password(password)
        user.save()
        return instance
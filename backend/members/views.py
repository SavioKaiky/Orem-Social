from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import Role
from accounts.validators import only_digits

from .models import BeneficiaryProfile, Dependent, TermsVersion
from .permissions import CanViewReports, MemberDataAccess
from .serializers import (
    BeneficiaryRegistrationSerializer,
    BeneficiarySerializer,
    DependentSerializer,
    TermsSerializer,
)


def scope_queryset(queryset, user, *, worker_lookup, owner_lookup):
    """
    Define o que cada papel enxerga:
    Admin e Bispo veem tudo; Obreiro só o que é dos seus beneficiários;
    Beneficiário só o que é dele; os demais não veem nada.
    """
    if user.role in (Role.ADMIN, Role.BISHOP):
        return queryset
    if user.role == Role.WORKER:
        return queryset.filter(**{worker_lookup: user})
    if user.role == Role.BENEFICIARY:
        return queryset.filter(**{owner_lookup: user})
    return queryset.none()


class CurrentTermsView(RetrieveAPIView):
    """Termos de Uso vigentes (público, para exibir antes do cadastro)."""

    serializer_class = TermsSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_object(self):
        return get_object_or_404(TermsVersion, is_current=True)


class BeneficiaryRegistrationView(CreateAPIView):
    """Autocadastro do beneficiário (público, com limite de tentativas por IP)."""

    serializer_class = BeneficiaryRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        output = BeneficiarySerializer(profile, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class BeneficiaryViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = BeneficiarySerializer
    permission_classes = [MemberDataAccess]
    http_method_names = ["get", "patch", "head", "options"]

    def scoped_queryset(self):
        """Recorte por papel + filtros (?state=GO&status=active&search=...), sem joins extras."""
        queryset = BeneficiaryProfile.objects.all()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        queryset = scope_queryset(
            queryset, self.request.user, worker_lookup="worker__user", owner_lookup="user"
        )
        params = self.request.query_params
        if params.get("state"):
            queryset = queryset.filter(state=params["state"].upper())
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        search = params.get("search")
        if search:
            condition = Q(user__full_name__icontains=search)
            digits = only_digits(search)
            if digits:
                condition |= Q(user__cpf__startswith=digits)
            queryset = queryset.filter(condition)
        return queryset

    def get_queryset(self):
        return (
            self.scoped_queryset()
            .select_related("user", "worker__user")
            .prefetch_related(
                Prefetch(
                    "dependents",
                    queryset=Dependent.objects.filter(is_active=True),
                    to_attr="active_dependents",
                )
            )
            .order_by("user__full_name")
        )

    @action(detail=False, methods=["get"], permission_classes=[CanViewReports])
    def summary(self, request):
        """Totais por grupo regional (estado) e situação, respeitando o recorte do usuário."""
        rows = (
            self.scoped_queryset()
            .order_by("state")
            .values("state", "status")
            .annotate(total=Count("id"))
        )
        groups = {}
        for row in rows:
            group = groups.setdefault(
                row["state"],
                {"group": f"OREM/{row['state']}", "state": row["state"], "total": 0, "by_status": {}},
            )
            group["total"] += row["total"]
            group["by_status"][row["status"]] = row["total"]
        data = list(groups.values())
        return Response({"total": sum(g["total"] for g in data), "groups": data})


class DependentViewSet(viewsets.ModelViewSet):
    """Dependentes. DELETE desativa o dependente (não apaga o histórico)."""

    serializer_class = DependentSerializer
    permission_classes = [MemberDataAccess]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Dependent.objects.filter(is_active=True).select_related("beneficiary__user")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return scope_queryset(
            queryset,
            self.request.user,
            worker_lookup="beneficiary__worker__user",
            owner_lookup="beneficiary__user",
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
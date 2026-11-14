from django.db.models import Count, F, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from members.models import BeneficiaryStatus

from .models import WorkerProfile
from .permissions import CanManageWorkers, IsAdminOrBishopReadOnly
from .serializers import LoginSerializer, UserSerializer, WorkerSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    # Limite de tentativas por IP, contra tentativa de adivinhar senha
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(RetrieveAPIView):
    """Dados do usuário logado."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class WorkerViewSet(viewsets.ModelViewSet):
    """Obreiros multiplicadores. Não há DELETE: para desligar, use is_active=false."""

    queryset = WorkerProfile.objects.select_related("user")
    serializer_class = WorkerSerializer
    permission_classes = [CanManageWorkers]
    http_method_names = ["get", "post", "patch", "head", "options"]

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrBishopReadOnly])
    def ranking(self, request):
        """Dez obreiros com mais beneficiários vinculados."""
        workers = (
            self.get_queryset()
            .annotate(
                full_name=F("user__full_name"),
                total=Count("beneficiaries"),
                active=Count("beneficiaries", filter=Q(beneficiaries__status=BeneficiaryStatus.ACTIVE)),
            )
            .filter(total__gt=0)
            .order_by("-total", "-active", "full_name", "pk")
            .values("id", "full_name", "code", "total", "active")[:10]
        )
        return Response(list(workers))

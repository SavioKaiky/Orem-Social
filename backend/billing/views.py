from uuid import uuid4

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role

from .models import CARENCE_MONTHS, Notification, Payment, PricingConfig
from .permissions import CanReadPayments, IsBeneficiary
from .providers import get_provider
from .rules import CARENCE_DAYS
from .serializers import NotificationSerializer, PaymentSerializer
from .services import (
    BillingError,
    can_renew,
    confirm_payment,
    create_contribution_charge,
    get_subscription,
    monthly_amount,
)
from .texts import PAYMENT_METHODS


class PricingView(APIView):
    """Valores vigentes da contribuição (público, para mostrar antes do cadastro)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        pricing = PricingConfig.current()
        return Response(
            {
                "valid_from": pricing.valid_from,
                "minimum_wage": pricing.minimum_wage,
                "holder_amount": pricing.holder_amount,
                "dependent_amount": pricing.dependent_amount,
            }
        )


class PaymentMethodsView(APIView):
    """Formas de pagamento da mensalidade, com o texto explicativo exibido no app."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = [
            {**method, "available": method["code"] != "pix_automatic" or settings.PIX_AUTOMATIC_ENABLED}
            for method in PAYMENT_METHODS
        ]
        return Response(data)


class BillingSummaryView(APIView):
    """Situação de pagamento do beneficiário logado."""

    permission_classes = [IsBeneficiary]

    def get(self, request):
        beneficiary = request.user.beneficiary_profile
        subscription = get_subscription(beneficiary)
        now = timezone.now()
        amount, dependents_count = monthly_amount(beneficiary)
        return Response(
            {
                "status": beneficiary.status,
                "covered_until": subscription.covered_until,
                "grace_deadline": subscription.grace_deadline,
                "is_current": subscription.is_current(now),
                "carence_met": subscription.carence_met(now),
                "carence_days": CARENCE_DAYS,
                "carence_months": CARENCE_MONTHS,
                "can_renew": can_renew(subscription, now),
                "next_amount": amount,
                "dependents_count": dependents_count,
            }
        )


class ChargeCreateView(APIView):
    """Gera (ou reaproveita) a cobrança PIX da contribuição mensal."""

    permission_classes = [IsBeneficiary]

    def post(self, request):
        try:
            payment = create_contribution_charge(request.user.beneficiary_profile)
        except BillingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [CanReadPayments]

    def get_queryset(self):
        queryset = Payment.objects.all()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        if self.request.user.role == Role.BENEFICIARY:
            queryset = queryset.filter(beneficiary__user=self.request.user)
        return queryset


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})


class PixWebhookView(APIView):
    """Recebe a confirmação de PIX do banco. Protegido por segredo, sem login."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        provider = get_provider()
        if not provider.verify_webhook(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        events = provider.parse_webhook(request.data)
        for event in events:
            confirm_payment(
                txid=event.txid,
                end_to_end_id=event.end_to_end_id,
                amount=event.amount,
                paid_at=event.paid_at,
            )
        return Response({"processed": len(events)})


class DevSimulatePaymentView(APIView):
    """Só em desenvolvimento com o provedor simulado: marca uma cobrança como paga."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (settings.DEBUG and settings.PIX_PROVIDER == "fake"):
            raise Http404
        payment = get_object_or_404(Payment, txid=request.data.get("txid"), beneficiary__user=request.user)
        confirm_payment(
            txid=payment.txid,
            end_to_end_id=f"E{uuid4().hex}",
            amount=payment.amount,
            paid_at=timezone.now(),
        )
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data)
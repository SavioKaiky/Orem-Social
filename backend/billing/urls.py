from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    BillingSummaryView,
    ChargeCreateView,
    DevSimulatePaymentView,
    NotificationViewSet,
    PaymentMethodsView,
    PaymentViewSet,
    PixWebhookView,
    PricingView,
)

router = SimpleRouter()
router.register("billing/payments", PaymentViewSet, basename="payment")
router.register("billing/notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("billing/pricing/", PricingView.as_view(), name="pricing"),
    path("billing/payment-methods/", PaymentMethodsView.as_view(), name="payment-methods"),
    path("billing/me/", BillingSummaryView.as_view(), name="billing-me"),
    path("billing/charges/", ChargeCreateView.as_view(), name="charge-create"),
    path("billing/webhook/pix/", PixWebhookView.as_view(), name="pix-webhook"),
    path("billing/dev/simulate-payment/", DevSimulatePaymentView.as_view(), name="dev-simulate-payment"),
    path("", include(router.urls)),
]
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BeneficiaryRegistrationView,
    BeneficiaryViewSet,
    CurrentTermsView,
    DependentViewSet,
)

router = DefaultRouter()
router.register("beneficiaries", BeneficiaryViewSet, basename="beneficiary")
router.register("dependents", DependentViewSet, basename="dependent")

urlpatterns = [
    path("terms/current/", CurrentTermsView.as_view(), name="terms-current"),
    # Precisa vir antes do router para "register" não ser lido como id
    path("beneficiaries/register/", BeneficiaryRegistrationView.as_view(), name="beneficiary-register"),
    path("", include(router.urls)),
]
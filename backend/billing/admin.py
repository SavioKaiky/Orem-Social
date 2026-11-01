from django.contrib import admin

from .models import Notification, Payment, PricingConfig, Subscription, UnidentifiedPayment


@admin.register(PricingConfig)
class PricingConfigAdmin(admin.ModelAdmin):
    """O Admin cadastra um novo salário mínimo com a data de vigência; cobranças já geradas não mudam."""

    list_display = ("valid_from", "minimum_wage", "holder_amount", "dependent_amount")


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "beneficiary", "purpose", "amount", "status")
    list_filter = ("purpose", "status", "method")
    search_fields = ("txid", "beneficiary__user__full_name", "beneficiary__user__cpf")


@admin.register(Subscription)
class SubscriptionAdmin(ReadOnlyAdmin):
    list_display = ("beneficiary", "covered_until", "streak_started_at")


@admin.register(UnidentifiedPayment)
class UnidentifiedPaymentAdmin(admin.ModelAdmin):
    """Fila de PIX que o Admin precisa investigar; só o campo 'resolvido' é editável."""

    list_display = ("created_at", "amount", "reason", "resolved")
    list_filter = ("resolved",)
    readonly_fields = ("txid", "end_to_end_id", "amount", "reason", "created_at")

    def has_add_permission(self, request):
        return False


admin.site.register(Notification)
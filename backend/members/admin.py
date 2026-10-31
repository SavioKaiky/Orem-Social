from django.contrib import admin

from .models import BeneficiaryProfile, Dependent, TermsAcceptance, TermsVersion


class DependentInline(admin.TabularInline):
    model = Dependent
    extra = 0


@admin.register(BeneficiaryProfile)
class BeneficiaryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "worker", "state", "status")
    list_filter = ("state", "status")
    search_fields = ("user__full_name", "user__cpf")
    inlines = [DependentInline]


@admin.register(TermsVersion)
class TermsVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "is_current", "created_at")


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(admin.ModelAdmin):
    """Prova do aceite: somente leitura, ninguém edita nem cria à mão."""

    list_display = ("user", "terms", "accepted_at", "ip_address")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
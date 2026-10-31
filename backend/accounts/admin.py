from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserCreationForm, UserEditForm
from .models import BishopProfile, ProviderProfile, User, WorkerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserEditForm
    add_form = UserCreationForm
    ordering = ("full_name",)
    list_display = ("cpf", "full_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("cpf", "full_name", "email")
    fieldsets = (
        (None, {"fields": ("cpf", "password")}),
        ("Dados pessoais", {"fields": ("full_name", "email", "phone", "role")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("cpf", "full_name", "role", "password1", "password2")}),
    )


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ("code", "user")
    search_fields = ("code", "user__full_name", "user__cpf")


admin.site.register(BishopProfile)
admin.site.register(ProviderProfile)
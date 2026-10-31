from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("cpf", "full_name", "role")
        field_classes = {}


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        field_classes = {}
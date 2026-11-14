from django.db import migrations, models
from django.db.models import Q


def normalize_existing_phones(apps, schema_editor):
    """Padroniza telefones antes de impor unicidade e interrompe se houver colisões."""
    User = apps.get_model("accounts", "User")
    using = schema_editor.connection.alias
    owners = {}
    updates = []
    conflicts = {}

    for user in User.objects.using(using).exclude(phone="").order_by("pk").iterator():
        digits = "".join(character for character in user.phone if character.isdigit())
        if digits.startswith("55") and len(digits) in (12, 13):
            digits = digits[2:]
        if not digits:
            digits = ""

        if digits and digits in owners:
            conflicts.setdefault(digits, [owners[digits]]).append(user.pk)
        elif digits:
            owners[digits] = user.pk

        if user.phone != digits:
            updates.append((user.pk, digits))

    if conflicts:
        ids = ", ".join(
            f"{phone}: usuários {user_ids}" for phone, user_ids in conflicts.items()
        )
        raise RuntimeError(
            "Há telefones repetidos após a normalização. Corrija os telefones destes usuários "
            f"no Admin e execute a migração novamente. {ids}"
        )

    for user_id, phone in updates:
        User.objects.using(using).filter(pk=user_id).update(phone=phone)


def noop(apps, schema_editor):
    """Migração reversa não restaura as máscaras anteriores dos telefones."""


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(normalize_existing_phones, noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=("phone",),
                condition=~Q(phone=""),
                name="unique_user_phone_when_set",
            ),
        ),
    ]

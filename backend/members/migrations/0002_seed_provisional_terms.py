from django.db import migrations

PROVISIONAL_TEXT = (
    "TEXTO PROVISÓRIO. Estes Termos de Uso aguardam a validação da assessoria jurídica "
    "da Igreja OREM e serão substituídos antes da publicação do aplicativo. "
    "A adesão ao Orem Social é voluntária; o beneficiário pode sair e retornar livremente, "
    "sem negativação."
)


def create_provisional_terms(apps, schema_editor):
    TermsVersion = apps.get_model("members", "TermsVersion")
    TermsVersion.objects.get_or_create(
        version="0.1-provisorio",
        defaults={"content": PROVISIONAL_TEXT, "is_current": True},
    )


class Migration(migrations.Migration):
    dependencies = [("members", "0001_initial")]

    operations = [migrations.RunPython(create_provisional_terms, migrations.RunPython.noop)]
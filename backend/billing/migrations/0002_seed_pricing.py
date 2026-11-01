from datetime import date
from decimal import Decimal

from django.db import migrations


def seed_pricing(apps, schema_editor):
    PricingConfig = apps.get_model("billing", "PricingConfig")
    # Salário mínimo de referência do relatório do sistema
    PricingConfig.objects.get_or_create(
        valid_from=date(2026, 1, 1), defaults={"minimum_wage": Decimal("1621.00")}
    )


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]

    operations = [migrations.RunPython(seed_pricing, migrations.RunPython.noop)]
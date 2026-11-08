from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("members", "0002_seed_provisional_terms")]

    operations = [
        migrations.AddField(
            model_name="dependent",
            name="email",
            field=models.EmailField("E-mail", blank=True, default="", max_length=254),
        ),
    ]

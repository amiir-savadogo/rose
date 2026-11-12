from django.db import migrations

from apps.risks.taxonomie import charger_typologie


def charger(apps, schema_editor):
    charger_typologie(
        apps.get_model("risks", "CategorieEvenement"),
        apps.get_model("risks", "SousCategorieEvenement"),
        apps.get_model("risks", "RiskCategory"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('risks', '0005_typologie_evenements'),
    ]

    operations = [
        # Pas de retour arrière des données : le référentiel est conservé si on annule 0005+.
        migrations.RunPython(charger, migrations.RunPython.noop),
    ]

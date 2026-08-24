from django.db import migrations

# Valeurs de départ raisonnables, cohérentes avec le comportement du logiciel
# avant que cette matrice ne devienne éditable. L'administrateur peut tout
# changer depuis Paramètres > Rôles et permissions.
DEFAUTS = {
    "risk_manager": ["gerer_risques", "traiter_incidents", "gerer_controles", "gerer_obligations", "gerer_bibliotheque"],
    "controleur": ["traiter_incidents", "consulter_audit"],
    "agent": [],
    "direction": [],
}


def creer_defauts(apps, schema_editor):
    RolePermission = apps.get_model("accounts", "RolePermission")
    toutes_permissions = ["gerer_risques", "traiter_incidents", "gerer_controles", "gerer_obligations", "gerer_bibliotheque", "consulter_audit"]
    for role, permissions_autorisees in DEFAUTS.items():
        for cle in toutes_permissions:
            RolePermission.objects.get_or_create(
                role=role, permission=cle, defaults={"autorise": cle in permissions_autorisees}
            )


def revenir_en_arriere(apps, schema_editor):
    RolePermission = apps.get_model("accounts", "RolePermission")
    RolePermission.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_rolepermission"),
    ]

    operations = [
        migrations.RunPython(creer_defauts, revenir_en_arriere),
    ]

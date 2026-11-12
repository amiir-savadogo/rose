import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0003_incident_direction'),
        ('risks', '0006_charger_typologie_evenements'),
    ]

    operations = [
        migrations.AlterField(
            model_name='incident',
            name='categorie_evenement',
            field=models.CharField(blank=True, choices=[('fraude_interne', 'Fraude interne'), ('fraude_externe', 'Fraude externe'), ('pratiques_rh', "Pratiques en matière d'emploi et sécurité sur le lieu de travail"), ('clients_produits', "Pratiques concernant les clients, les produits et l'activité commerciale"), ('dommages_actifs', 'Dommages occasionnés aux actifs physiques'), ('interruption_si', "Interruptions d'activités et défaillance des systèmes"), ('execution_livraison', 'Exécution des opérations, livraison et gestion des processus')], max_length=30),
        ),
        migrations.AddField(
            model_name='incident',
            name='sous_categorie',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='incidents', to='risks.souscategorieevenement', verbose_name="Sous-catégorie d'événement"),
        ),
    ]

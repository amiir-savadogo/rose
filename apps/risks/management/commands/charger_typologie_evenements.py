from django.core.management.base import BaseCommand

from apps.risks.models import CategorieEvenement, RiskCategory, SousCategorieEvenement
from apps.risks.taxonomie import charger_typologie


class Command(BaseCommand):
    help = (
        "Charge (ou remet à jour) la typologie des événements de pertes opérationnelles de la "
        "Circulaire 003-2017/CB/C. Sans risque à rejouer : aucun doublon, rien n'est supprimé."
    )

    def handle(self, *args, **options):
        nb_cat, nb_sous = charger_typologie(CategorieEvenement, SousCategorieEvenement, RiskCategory)
        self.stdout.write(self.style.SUCCESS(f"{nb_cat} catégories et {nb_sous} sous-catégories chargées."))

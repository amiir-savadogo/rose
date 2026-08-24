"""Génère automatiquement les prochaines occurrences des obligations actives.

Prévu pour être exécuté régulièrement (ex: tâche planifiée quotidienne / cron)
afin d'alimenter le suivi des échéances sans intervention manuelle.

Usage : python manage.py generer_echeances
"""
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.obligations.models import Obligation, ObligationOccurrence

DELTA_PAR_PERIODICITE = {
    Obligation.Periodicite.MENSUELLE: relativedelta(months=1),
    Obligation.Periodicite.TRIMESTRIELLE: relativedelta(months=3),
    Obligation.Periodicite.SEMESTRIELLE: relativedelta(months=6),
    Obligation.Periodicite.ANNUELLE: relativedelta(years=1),
}

HORIZON_MOIS = 3  # on génère les échéances jusqu'à 3 mois à l'avance


class Command(BaseCommand):
    help = "Génère les prochaines occurrences d'échéance pour les obligations récurrentes actives."

    def handle(self, *args, **options):
        aujourdhui = timezone.now().date()
        horizon = aujourdhui + relativedelta(months=HORIZON_MOIS)
        total_crees = 0

        for obligation in Obligation.objects.filter(active=True).exclude(
            periodicite=Obligation.Periodicite.PONCTUELLE
        ):
            delta = DELTA_PAR_PERIODICITE[obligation.periodicite]
            derniere = obligation.occurrences.order_by("-date_echeance").first()
            prochaine_date = (derniere.date_echeance + delta) if derniere else aujourdhui

            while prochaine_date <= horizon:
                _, cree = ObligationOccurrence.objects.get_or_create(
                    obligation=obligation, date_echeance=prochaine_date
                )
                if cree:
                    total_crees += 1
                prochaine_date += delta

        # Marquer en retard les échéances non réalisées dont la date est dépassée
        ObligationOccurrence.objects.filter(
            statut=ObligationOccurrence.Statut.A_VENIR, date_echeance__lt=aujourdhui
        ).update(statut=ObligationOccurrence.Statut.EN_RETARD)

        self.stdout.write(self.style.SUCCESS(f"{total_crees} nouvelle(s) échéance(s) générée(s)."))

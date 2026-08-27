"""Tests des obligations réglementaires et de la génération des échéances."""
import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.obligations.models import Obligation, ObligationOccurrence


class GenererEcheancesTests(TestCase):
    """La commande generer_echeances doit produire les occurrences futures
    et marquer en retard celles dont l'échéance est dépassée sans être réalisée."""

    def setUp(self):
        self.responsable = User.objects.create_user(username="resp_obl", password="x", role="risk_manager")

    def test_genere_des_occurrences_futures(self):
        Obligation.objects.create(nom="Rapport mensuel", periodicite="mensuelle", responsable=self.responsable)
        call_command("generer_echeances")
        self.assertTrue(ObligationOccurrence.objects.exists())

    def test_marque_en_retard_les_echeances_passees_non_realisees(self):
        obligation = Obligation.objects.create(nom="Rapport test", periodicite="mensuelle", responsable=self.responsable)
        occurrence = ObligationOccurrence.objects.create(
            obligation=obligation, date_echeance=timezone.now().date() - datetime.timedelta(days=5),
            statut=ObligationOccurrence.Statut.A_VENIR,
        )
        call_command("generer_echeances")
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.statut, ObligationOccurrence.Statut.EN_RETARD)

    def test_obligation_ponctuelle_ignoree(self):
        """Une obligation ponctuelle n'a pas d'occurrence récurrente à générer."""
        Obligation.objects.create(nom="Déclaration unique", periodicite="ponctuelle", responsable=self.responsable)
        call_command("generer_echeances")
        self.assertFalse(ObligationOccurrence.objects.exists())

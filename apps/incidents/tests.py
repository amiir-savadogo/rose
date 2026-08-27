"""Tests des incidents : délai de détection, pertes, catégorisation."""
import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.incidents.models import Incident


class IncidentDelaiDetectionTests(TestCase):
    """L'écart entre survenance et détection mesure la capacité de détection
    de l'établissement — c'est un indicateur en soi."""

    def setUp(self):
        self.declarant = User.objects.create_user(username="declarant_i", password="x", role="agent")

    def test_delai_calcule_correctement(self):
        incident = Incident.objects.create(
            titre="Test", description="x",
            date_survenue=datetime.date(2026, 8, 1), date_detection=datetime.date(2026, 8, 10),
            declare_par=self.declarant,
        )
        self.assertEqual(incident.delai_detection_jours, 9)

    def test_delai_none_si_pas_de_detection(self):
        incident = Incident.objects.create(
            titre="Test", description="x", date_survenue=datetime.date(2026, 8, 1),
            declare_par=self.declarant,
        )
        self.assertIsNone(incident.delai_detection_jours)


class IncidentPerteNetteTests(TestCase):
    def setUp(self):
        self.declarant = User.objects.create_user(username="declarant_i2", password="x", role="agent")

    def test_perte_nette_calculee(self):
        incident = Incident.objects.create(
            titre="Test", description="x", date_survenue=datetime.date(2026, 8, 1),
            declare_par=self.declarant, perte_brute=250000, recuperation=50000,
        )
        self.assertEqual(incident.perte_nette, 200000)

    def test_perte_nette_none_sans_perte_brute(self):
        incident = Incident.objects.create(
            titre="Test", description="x", date_survenue=datetime.date(2026, 8, 1),
            declare_par=self.declarant,
        )
        self.assertIsNone(incident.perte_nette)

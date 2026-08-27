"""Tests du comité des risques : décisions et leur suivi d'exécution."""
import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.comite.models import DecisionComite, SeanceComite


class DecisionComiteStatutTests(TestCase):
    """Le statut d'une décision suit son échéance et sa date d'exécution —
    un comité qui ne sait pas qu'une décision est en retard perd son autorité."""

    def setUp(self):
        self.responsable = User.objects.create_user(username="responsable_c", password="x", role="risk_manager")
        self.createur = User.objects.create_user(username="createur_c", password="x", role="admin")
        self.seance = SeanceComite.objects.create(
            libelle="Comité test", date_seance=datetime.date(2026, 8, 1), cree_par=self.createur,
        )

    def test_decision_avec_echeance_future_est_a_executer(self):
        decision = DecisionComite.objects.create(
            seance=self.seance, libelle="Décision test", responsable=self.responsable,
            echeance=datetime.date(2099, 1, 1),
        )
        self.assertEqual(decision.statut, DecisionComite.Statut.A_EXECUTER)

    def test_decision_avec_echeance_passee_est_en_retard(self):
        decision = DecisionComite.objects.create(
            seance=self.seance, libelle="Décision test", responsable=self.responsable,
            echeance=datetime.date(2020, 1, 1),
        )
        self.assertEqual(decision.statut, DecisionComite.Statut.EN_RETARD)

    def test_decision_executee_reste_executee_meme_apres_echeance(self):
        decision = DecisionComite.objects.create(
            seance=self.seance, libelle="Décision test", responsable=self.responsable,
            echeance=datetime.date(2020, 1, 1), date_execution=datetime.date(2026, 8, 20),
        )
        self.assertEqual(decision.statut, DecisionComite.Statut.EXECUTEE)


class SeanceComiteTests(TestCase):
    def setUp(self):
        self.createur = User.objects.create_user(username="createur_s", password="x", role="admin")
        self.responsable = User.objects.create_user(username="responsable_s", password="x", role="risk_manager")

    def test_nb_decisions_correct(self):
        seance = SeanceComite.objects.create(
            libelle="Comité test", date_seance=datetime.date(2026, 8, 1), cree_par=self.createur,
        )
        self.assertEqual(seance.nb_decisions, 0)
        DecisionComite.objects.create(seance=seance, libelle="D1", responsable=self.responsable)
        DecisionComite.objects.create(seance=seance, libelle="D2", responsable=self.responsable)
        self.assertEqual(seance.nb_decisions, 2)

    def test_periode_debut_est_90_jours_avant(self):
        seance = SeanceComite.objects.create(
            libelle="Comité test", date_seance=datetime.date(2026, 8, 1), cree_par=self.createur,
        )
        self.assertEqual(seance.periode_debut, datetime.date(2026, 5, 3))

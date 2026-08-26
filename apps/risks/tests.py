"""Tests des règles métier critiques de la cartographie des risques."""
import datetime

from django.test import TestCase

from apps.accounts.models import Direction, User
from apps.risks.forms import KeyRiskIndicatorForm
from apps.risks.models import (
    ActionPlan, Campagne, KeyRiskIndicator, Risk, RiskCategory, RiskEvaluation, classer_score,
)


class ClasserScoreTests(TestCase):
    """Le niveau qualitatif d'un risque est calculé, jamais saisi à la main."""

    def test_score_eleve_est_critique(self):
        self.assertEqual(classer_score(20), "critique")

    def test_score_dix_est_eleve(self):
        self.assertEqual(classer_score(10), "eleve")

    def test_score_cinq_est_modere(self):
        self.assertEqual(classer_score(5), "modere")

    def test_score_un_est_faible(self):
        self.assertEqual(classer_score(1), "faible")


class KeyRiskIndicatorEtatTests(TestCase):
    """Un KRI porte deux seuils (alerte, limite) et un sens de variation —
    l'état affiché doit refléter correctement les deux cas (hausse et baisse)."""

    def setUp(self):
        user = User.objects.create_user(username="evaluateur", password="x", role="risk_manager")
        cat = RiskCategory.objects.create(nom="Risque de crédit")
        self.risque = Risk.objects.create(titre="Risque test", categorie=cat, proprietaire=user)

    def test_sens_hausse_dans_les_limites(self):
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Taux de créances douteuses", sens="hausse",
            seuil_alerte=5, seuil_limite=8, valeur_actuelle=3,
        )
        self.assertEqual(kri.etat, "dans_les_limites")

    def test_sens_hausse_alerte(self):
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Taux de créances douteuses", sens="hausse",
            seuil_alerte=5, seuil_limite=8, valeur_actuelle=6,
        )
        self.assertEqual(kri.etat, "alerte")

    def test_sens_hausse_limite_franchie(self):
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Taux de créances douteuses", sens="hausse",
            seuil_alerte=5, seuil_limite=8, valeur_actuelle=9,
        )
        self.assertEqual(kri.etat, "limite_franchie")

    def test_sens_baisse_dans_les_limites(self):
        """Un taux de disponibilité : le risque croît quand la valeur BAISSE."""
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Taux de disponibilité", sens="baisse",
            seuil_alerte=99, seuil_limite=97, valeur_actuelle=99.9,
        )
        self.assertEqual(kri.etat, "dans_les_limites")

    def test_sens_baisse_alerte(self):
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Taux de disponibilité", sens="baisse",
            seuil_alerte=99, seuil_limite=97, valeur_actuelle=98,
        )
        self.assertEqual(kri.etat, "alerte")

    def test_sens_baisse_limite_franchie(self):
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Taux de disponibilité", sens="baisse",
            seuil_alerte=99, seuil_limite=97, valeur_actuelle=90,
        )
        self.assertEqual(kri.etat, "limite_franchie")

    def test_sans_valeur_etat_inconnu(self):
        kri = KeyRiskIndicator.objects.create(
            risque=self.risque, nom="Sans valeur", seuil_alerte=5, seuil_limite=8,
        )
        self.assertEqual(kri.etat, "inconnu")


class KeyRiskIndicatorFormCoherenceTests(TestCase):
    """Le formulaire doit refuser des seuils incohérents avec le sens choisi."""

    def setUp(self):
        user = User.objects.create_user(username="evaluateur2", password="x", role="risk_manager")
        cat = RiskCategory.objects.create(nom="Risque opérationnel")
        self.risque = Risk.objects.create(titre="Risque test", categorie=cat, proprietaire=user)

    def test_hausse_avec_limite_inferieure_a_alerte_refuse(self):
        form = KeyRiskIndicatorForm(data={
            "nom": "Test", "sens": "hausse", "seuil_alerte": 8, "seuil_limite": 5, "valeur_actuelle": 3,
        })
        self.assertFalse(form.is_valid())

    def test_baisse_avec_limite_superieure_a_alerte_refuse(self):
        form = KeyRiskIndicatorForm(data={
            "nom": "Test", "sens": "baisse", "seuil_alerte": 90, "seuil_limite": 95, "valeur_actuelle": 92,
        })
        self.assertFalse(form.is_valid())

    def test_hausse_coherente_acceptee(self):
        form = KeyRiskIndicatorForm(data={
            "nom": "Test", "sens": "hausse", "seuil_alerte": 5, "seuil_limite": 8, "valeur_actuelle": 3,
        })
        self.assertTrue(form.is_valid())


class CampagneClotureTests(TestCase):
    """Une campagne clôturée fige ses évaluations — aucune modification possible après coup."""

    def setUp(self):
        self.user = User.objects.create_user(username="evaluateur3", password="x", role="risk_manager")
        cat = RiskCategory.objects.create(nom="Risque de crédit")
        self.risque = Risk.objects.create(titre="Risque test", categorie=cat, proprietaire=self.user)
        self.campagne = Campagne.objects.create(nom="Revue 2026", date_ouverture=datetime.date(2026, 1, 1))

    def test_evaluation_modifiable_pendant_campagne_ouverte(self):
        evaluation = RiskEvaluation.objects.create(
            risque=self.risque, campagne=self.campagne,
            probabilite_inherente=3, impact_inherent=3, qualite_dispositif_maitrise=3,
            probabilite_residuelle=2, impact_residuel=2, evalue_par=self.user,
        )
        evaluation.justification = "mise à jour"
        evaluation.save()  # ne doit pas lever d'erreur

    def test_evaluation_bloquee_apres_cloture(self):
        evaluation = RiskEvaluation.objects.create(
            risque=self.risque, campagne=self.campagne,
            probabilite_inherente=3, impact_inherent=3, qualite_dispositif_maitrise=3,
            probabilite_residuelle=2, impact_residuel=2, evalue_par=self.user,
        )
        self.campagne.statut = Campagne.Statut.CLOTUREE
        self.campagne.save()

        evaluation.justification = "tentative de modification après clôture"
        with self.assertRaises(PermissionError):
            evaluation.save()


class ActionPlanStatutAutomatiqueTests(TestCase):
    """Le statut d'un plan d'action suit mécaniquement l'avancement et l'échéance."""

    def setUp(self):
        self.user = User.objects.create_user(username="responsable", password="x", role="risk_manager")

    def _plan(self, avancement, echeance):
        return ActionPlan.objects.create(
            description="Action test", responsable=self.user, echeance=echeance, avancement=avancement,
        )

    def test_avancement_100_pourcent_est_clos(self):
        plan = self._plan(100, datetime.date(2099, 1, 1))
        self.assertEqual(plan.statut, ActionPlan.Statut.CLOS)

    def test_avancement_faible_est_a_lancer(self):
        plan = self._plan(5, datetime.date(2099, 1, 1))
        self.assertEqual(plan.statut, ActionPlan.Statut.A_LANCER)

    def test_echeance_depassee_est_en_retard(self):
        plan = self._plan(50, datetime.date(2020, 1, 1))
        self.assertEqual(plan.statut, ActionPlan.Statut.EN_RETARD)

    def test_avancement_intermediaire_est_en_cours(self):
        plan = self._plan(50, datetime.date(2099, 1, 1))
        self.assertEqual(plan.statut, ActionPlan.Statut.EN_COURS)

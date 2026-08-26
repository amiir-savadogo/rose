"""Tests des règles métier critiques du plan de contrôle."""
import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Direction, User
from apps.controles.forms import ControleForm
from apps.controles.models import Controle, ControleExecution


class ExecutantSuperviseurTests(TestCase):
    """La plateforme doit refuser qu'un même utilisateur soit à la fois
    exécutant et superviseur d'un contrôle — c'est la séparation des tâches
    qui donne sa valeur au contrôle."""

    def setUp(self):
        self.jean = User.objects.create_user(username="jean", password="x", role="agent")
        self.marie = User.objects.create_user(username="marie", password="x", role="risk_manager")

    def test_formulaire_refuse_meme_personne(self):
        form = ControleForm(data={
            "nom": "Contrôle test", "niveau": "n1", "frequence": "mensuelle",
            "executant": self.jean.pk, "superviseur": self.jean.pk, "actif": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("personnes différentes", str(form.errors))

    def test_formulaire_accepte_personnes_differentes(self):
        form = ControleForm(data={
            "nom": "Contrôle test", "niveau": "n1", "frequence": "mensuelle",
            "executant": self.jean.pk, "superviseur": self.marie.pk, "actif": True,
        })
        self.assertTrue(form.is_valid())

    def test_contrainte_base_de_donnees_refuse_meme_personne(self):
        """Même en contournant le formulaire (ex: import, script), la base doit refuser."""
        controle = Controle(
            nom="Contrôle direct", niveau="n1", frequence="mensuelle",
            executant=self.jean, superviseur=self.jean,
        )
        with self.assertRaises(ValidationError):
            controle.full_clean()

    def test_modele_accepte_personnes_differentes(self):
        controle = Controle.objects.create(
            nom="Contrôle OK", niveau="n1", frequence="mensuelle",
            executant=self.jean, superviseur=self.marie,
        )
        self.assertIsNotNone(controle.pk)


class PreuveManquanteTests(TestCase):
    """Un contrôle déclaré conforme sans preuve archivée doit être signalé —
    « un contrôle sans preuve est un contrôle non fait »."""

    def setUp(self):
        jean = User.objects.create_user(username="jean2", password="x", role="agent")
        marie = User.objects.create_user(username="marie2", password="x", role="risk_manager")
        self.controle = Controle.objects.create(
            nom="Contrôle test", niveau="n1", frequence="mensuelle", executant=jean, superviseur=marie,
        )

    def test_conforme_sans_preuve_est_signale(self):
        execution = ControleExecution.objects.create(
            controle=self.controle, date_prevue=datetime.date(2026, 8, 1),
            date_realisee=datetime.date(2026, 8, 1), resultat=ControleExecution.Resultat.CONFORME,
        )
        self.assertTrue(execution.preuve_manquante)

    def test_non_realise_n_est_pas_signale_comme_preuve_manquante(self):
        """Un contrôle pas encore réalisé n'a pas de preuve à fournir — ce n'est pas
        le même problème qu'un contrôle réalisé sans preuve."""
        execution = ControleExecution.objects.create(
            controle=self.controle, date_prevue=datetime.date(2026, 8, 1),
        )
        self.assertFalse(execution.preuve_manquante)


class ExecutionEnRetardTests(TestCase):
    def setUp(self):
        jean = User.objects.create_user(username="jean3", password="x", role="agent")
        marie = User.objects.create_user(username="marie3", password="x", role="risk_manager")
        self.controle = Controle.objects.create(
            nom="Contrôle test", niveau="n1", frequence="mensuelle", executant=jean, superviseur=marie,
        )

    def test_execution_passee_non_realisee_est_en_retard(self):
        execution = ControleExecution.objects.create(controle=self.controle, date_prevue=datetime.date(2020, 1, 1))
        self.assertTrue(execution.en_retard)

    def test_execution_future_non_realisee_n_est_pas_en_retard(self):
        execution = ControleExecution.objects.create(controle=self.controle, date_prevue=datetime.date(2099, 1, 1))
        self.assertFalse(execution.en_retard)

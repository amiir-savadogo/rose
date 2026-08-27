"""Tests du journal d'audit : inaltérable, et alimenté automatiquement."""
from django.test import Client, TestCase

from apps.accounts.models import Direction, User
from apps.audit.models import AuditLogEntry
from apps.risks.models import Risk, RiskCategory


class AuditLogEntryImmutableTests(TestCase):
    """Une entrée du journal ne peut jamais être modifiée ni supprimée,
    y compris par un administrateur — c'est ce qui lui donne sa valeur probante."""

    def setUp(self):
        self.user = User.objects.create_user(username="quelqu_un", password="x", role="admin")
        self.entree = AuditLogEntry.objects.create(
            utilisateur=self.user, action=AuditLogEntry.Action.CREATION,
            modele="risks.Risk", objet_id="1", objet_repr="Test",
        )

    def test_modification_refusee(self):
        self.entree.objet_repr = "Modifié après coup"
        with self.assertRaises(PermissionError):
            self.entree.save()

    def test_suppression_refusee(self):
        with self.assertRaises(PermissionError):
            self.entree.delete()


class AuditLogAutomatiqueTests(TestCase):
    """La création d'un risque doit générer automatiquement une entrée
    d'audit, sans intervention explicite du code métier."""

    def setUp(self):
        self.user = User.objects.create_user(username="createur", password="x", role="risk_manager")
        self.cat = RiskCategory.objects.create(nom="Risque test")

    def test_creation_risque_journalisee(self):
        avant = AuditLogEntry.objects.filter(modele="risks.Risk").count()
        Risk.objects.create(titre="Risque audité", categorie=self.cat, proprietaire=self.user)
        apres = AuditLogEntry.objects.filter(modele="risks.Risk").count()
        self.assertEqual(apres, avant + 1)


class AuditConnexionTests(TestCase):
    """Toute connexion, réussie ou non, doit être journalisée."""

    def setUp(self):
        self.user = User.objects.create_user(username="testeur_connexion", password="motdepasse123", role="agent")

    def test_connexion_reussie_journalisee(self):
        avant = AuditLogEntry.objects.filter(modele="auth.Connexion").count()
        client = Client()
        client.post("/accounts/login/", {"username": "testeur_connexion", "password": "motdepasse123"})
        apres = AuditLogEntry.objects.filter(modele="auth.Connexion").count()
        self.assertEqual(apres, avant + 1)

    def test_connexion_echouee_journalisee(self):
        avant = AuditLogEntry.objects.filter(modele="auth.ConnexionEchouee").count()
        client = Client()
        client.post("/accounts/login/", {"username": "testeur_connexion", "password": "mauvais_mot_de_passe"})
        apres = AuditLogEntry.objects.filter(modele="auth.ConnexionEchouee").count()
        self.assertEqual(apres, avant + 1)

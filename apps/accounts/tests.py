"""Tests du filtrage par périmètre (entité/direction).

Politique testée : les rôles transverses (admin, risk_manager, contrôleur)
voient toutes les directions ; les rôles « métier » (agent, direction) ne
voient que les objets rattachés à leur propre direction — et cette
restriction doit tenir aussi bien sur les listes que sur l'accès direct à
un objet précis par son identifiant."""
import datetime

from django.test import Client, TestCase

from apps.accounts.models import Direction, User
from apps.accounts.perimetre import a_perimetre_restreint, filtrer_par_perimetre, objet_ou_404_perimetre
from apps.incidents.models import Incident
from apps.risks.models import Risk, RiskCategory
from django.http import Http404


class PerimetreRestreintTests(TestCase):
    def setUp(self):
        self.dir_ouaga = Direction.objects.create(nom="Agence de Ouagadougou")
        self.admin = User.objects.create_user(username="admin_t", password="x", role="admin")
        self.risk_manager = User.objects.create_user(username="rm_t", password="x", role="risk_manager")
        self.controleur = User.objects.create_user(username="ctrl_t", password="x", role="controleur")
        self.agent = User.objects.create_user(username="agent_t", password="x", role="agent", direction=self.dir_ouaga)
        self.direction_role = User.objects.create_user(username="dir_t", password="x", role="direction", direction=self.dir_ouaga)

    def test_roles_transverses_non_restreints(self):
        self.assertFalse(a_perimetre_restreint(self.admin))
        self.assertFalse(a_perimetre_restreint(self.risk_manager))
        self.assertFalse(a_perimetre_restreint(self.controleur))

    def test_roles_metier_restreints(self):
        self.assertTrue(a_perimetre_restreint(self.agent))
        self.assertTrue(a_perimetre_restreint(self.direction_role))

    def test_superuser_jamais_restreint_meme_avec_role_agent(self):
        superuser = User.objects.create_superuser(username="super_t", email="s@s.com", password="x")
        superuser.role = "agent"
        superuser.save()
        self.assertFalse(a_perimetre_restreint(superuser))


class FiltrerParPerimetreTests(TestCase):
    def setUp(self):
        self.dir_ouaga = Direction.objects.create(nom="Agence de Ouagadougou")
        self.dir_bobo = Direction.objects.create(nom="Agence de Bobo-Dioulasso")
        self.admin = User.objects.create_user(username="admin_f", password="x", role="admin")
        self.chef_ouaga = User.objects.create_user(username="chef_ouaga_f", password="x", role="agent", direction=self.dir_ouaga)

        cat = RiskCategory.objects.create(nom="Risque opérationnel")
        self.risque_ouaga = Risk.objects.create(titre="Risque Ouaga", categorie=cat, proprietaire=self.admin, direction=self.dir_ouaga)
        self.risque_bobo = Risk.objects.create(titre="Risque Bobo", categorie=cat, proprietaire=self.admin, direction=self.dir_bobo)

    def test_admin_voit_toutes_les_directions(self):
        qs = filtrer_par_perimetre(Risk.objects.all(), self.admin, champ="direction")
        self.assertEqual(qs.count(), 2)

    def test_agent_ne_voit_que_sa_direction(self):
        qs = filtrer_par_perimetre(Risk.objects.all(), self.chef_ouaga, champ="direction")
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.risque_ouaga)

    def test_objet_ou_404_bloque_hors_perimetre(self):
        with self.assertRaises(Http404):
            objet_ou_404_perimetre(Risk, self.chef_ouaga, self.risque_bobo.pk, champ="direction")

    def test_objet_ou_404_autorise_dans_perimetre(self):
        obtenu = objet_ou_404_perimetre(Risk, self.chef_ouaga, self.risque_ouaga.pk, champ="direction")
        self.assertEqual(obtenu, self.risque_ouaga)


class PerimetreBoutABoutTests(TestCase):
    """Vérifie que la restriction tient sur de vraies requêtes HTTP, pas
    seulement au niveau des fonctions Python — la liste ET l'accès direct
    par URL à un objet hors périmètre."""

    def setUp(self):
        self.dir_ouaga = Direction.objects.create(nom="Agence de Ouagadougou")
        self.dir_bobo = Direction.objects.create(nom="Agence de Bobo-Dioulasso")
        self.admin = User.objects.create_user(username="admin_e2e", password="x", role="admin", is_staff=True)
        self.chef_ouaga = User.objects.create_user(username="chef_ouaga_e2e", password="motdepasse123", role="agent", direction=self.dir_ouaga)

        cat = RiskCategory.objects.create(nom="Risque de crédit")
        self.risque_bobo = Risk.objects.create(titre="Risque confidentiel de Bobo", categorie=cat, proprietaire=self.admin, direction=self.dir_bobo)
        self.incident_bobo = Incident.objects.create(
            titre="Incident confidentiel de Bobo", description="x",
            date_survenue=datetime.date(2026, 1, 1), declare_par=self.admin, direction=self.dir_bobo,
        )

    def test_liste_risques_ne_montre_pas_hors_perimetre(self):
        client = Client()
        client.force_login(self.chef_ouaga)
        response = client.get("/risques/")
        self.assertNotContains(response, "Risque confidentiel de Bobo")

    def test_acces_direct_risque_hors_perimetre_renvoie_404(self):
        client = Client()
        client.force_login(self.chef_ouaga)
        response = client.get(f"/risques/{self.risque_bobo.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_acces_direct_incident_hors_perimetre_renvoie_404(self):
        client = Client()
        client.force_login(self.chef_ouaga)
        response = client.get(f"/incidents/{self.incident_bobo.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_dashboard_ne_compte_pas_les_incidents_hors_perimetre(self):
        client = Client()
        client.force_login(self.chef_ouaga)
        response = client.get("/")
        self.assertNotContains(response, "Incident confidentiel de Bobo")

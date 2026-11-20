"""Tests de non-régression du durcissement de sécurité (audit de novembre 2026).

Chaque classe correspond à une faille corrigée : si l'un de ces tests échoue un jour,
c'est que la faille correspondante est revenue.
"""
import datetime
import io
import os
import subprocess
import sys
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from apps.accounts.context_processors import permissions_front
from apps.accounts.forms import ChangerMotDePasseForm, ReinitialiserMotDePasseForm, UserCreateForm
from apps.accounts.models import Direction, RolePermission, User
from apps.audit.models import AuditLogEntry
from apps.audit.signals import adresse_ip
from apps.bibliotheque.models import Document, DocumentVersion
from apps.comite.models import DecisionComite, SeanceComite
from apps.controles.models import Controle, ControleExecution
from apps.incidents.forms import IncidentForm
from apps.incidents.models import Incident, IncidentPieceJointe
from apps.obligations.models import Obligation, ObligationOccurrence
from apps.risks.forms import RiskForm
from apps.risks.models import ActionPlan, Campagne, Risk, RiskCategory, RiskEvaluation
from apps.risks.views import securiser_cellule_excel
from config.fichiers import valider_fichier_televerse
from django import forms


def _evaluation(risque, user, **kw):
    valeurs = dict(
        probabilite_inherente=4, impact_inherent=4, qualite_dispositif_maitrise=2,
        probabilite_residuelle=3, impact_residuel=3, evalue_par=user,
    )
    valeurs.update(kw)
    return RiskEvaluation.objects.create(risque=risque, **valeurs)


class BaseSecuriteTests(TestCase):
    """Deux directions, un admin, un agent de chaque direction, des objets dans chacune."""

    def setUp(self):
        self.dir_a = Direction.objects.create(nom="Direction A")
        self.dir_b = Direction.objects.create(nom="Direction B")
        self.admin = User.objects.create_user(username="adm", password="Mdp-Solide-9472!", role="admin", is_staff=True)
        self.agent_a = User.objects.create_user(username="agent_a", password="Mdp-Solide-9472!", role="agent", direction=self.dir_a)
        self.rm = User.objects.create_user(username="rm", password="Mdp-Solide-9472!", role="risk_manager")
        cat = RiskCategory.objects.create(nom="Crédit")
        self.risque_a = Risk.objects.create(titre="Risque visible A", categorie=cat, direction=self.dir_a, proprietaire=self.admin, processus="Octroi A")
        self.risque_b = Risk.objects.create(titre="Risque secret B", categorie=cat, direction=self.dir_b, proprietaire=self.admin, processus="Octroi B")
        _evaluation(self.risque_a, self.admin)
        _evaluation(self.risque_b, self.admin)
        self.plan_a = ActionPlan.objects.create(risque=self.risque_a, description="Plan visible A", responsable=self.admin, echeance=datetime.date(2099, 1, 1))
        self.plan_b = ActionPlan.objects.create(risque=self.risque_b, description="Plan secret B", responsable=self.admin, echeance=datetime.date(2099, 1, 1))
        self.incident_a = Incident.objects.create(titre="Incident A", description="x", date_survenue=datetime.date(2026, 1, 1), declare_par=self.admin, direction=self.dir_a, perte_brute=100)
        self.incident_b = Incident.objects.create(titre="Incident secret B", description="x", date_survenue=datetime.date(2026, 1, 1), declare_par=self.admin, direction=self.dir_b, perte_brute=900)

    def client_de(self, user):
        c = Client()
        c.force_login(user)
        return c


# --------------------------------------------------------------------------------------
class ComiteAuthentificationTests(TestCase):
    """SEC : les vues du comité étaient accessibles sans connexion (dossier = tous les risques)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="a", password="x", role="admin")
        self.seance = SeanceComite.objects.create(libelle="Comité", date_seance=datetime.date(2026, 8, 1), cree_par=self.admin)
        self.decision = DecisionComite.objects.create(seance=self.seance, libelle="D", responsable=self.admin, echeance=datetime.date(2099, 1, 1))

    def test_dossier_exige_une_connexion(self):
        r = Client().get(f"/comite/{self.seance.pk}/dossier/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_ajouter_decision_exige_une_connexion(self):
        r = Client().post(f"/comite/{self.seance.pk}/decision/", {})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_executer_decision_exige_une_connexion(self):
        r = Client().post(f"/comite/decision/{self.decision.pk}/executer/", {"date_execution": "2026-09-01"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
        self.decision.refresh_from_db()
        self.assertIsNone(self.decision.date_execution)

    def test_utilisateur_connecte_voit_le_dossier(self):
        self.assertEqual(self.client_de(self.admin).get(f"/comite/{self.seance.pk}/dossier/").status_code, 200)

    def client_de(self, user):
        c = Client()
        c.force_login(user)
        return c


# --------------------------------------------------------------------------------------
class FuitesDePerimetreTests(BaseSecuriteTests):
    """SEC : export, matrice, plans d'action et analyse des incidents ignoraient le périmètre."""

    def test_export_excel_filtre_par_perimetre(self):
        r = self.client_de(self.agent_a).get("/risques/export.xlsx")
        self.assertEqual(r.status_code, 200)
        ws = load_workbook(io.BytesIO(r.content)).active
        titres = [row[1] for row in ws.iter_rows(min_row=2, values_only=True)]
        self.assertIn("Risque visible A", titres)
        self.assertNotIn("Risque secret B", titres)

    def test_export_excel_admin_voit_tout(self):
        ws = load_workbook(io.BytesIO(self.client_de(self.admin).get("/risques/export.xlsx").content)).active
        titres = [row[1] for row in ws.iter_rows(min_row=2, values_only=True)]
        self.assertIn("Risque secret B", titres)

    def test_matrice_filtree_par_perimetre(self):
        r = self.client_de(self.agent_a).get("/risques/matrice/")
        self.assertContains(r, "Octroi A")
        self.assertNotContains(r, "Octroi B")
        self.assertNotContains(r, "Risque secret B")

    def test_liste_plans_action_filtree(self):
        r = self.client_de(self.agent_a).get("/risques/plans-action/")
        self.assertContains(r, "Plan visible A")
        self.assertNotContains(r, "Plan secret B")

    def test_modification_plan_hors_perimetre_404(self):
        RolePermission.objects.update_or_create(role="agent", permission="gerer_risques", defaults={"autorise": True})
        c = self.client_de(self.agent_a)
        self.assertEqual(c.get(f"/risques/plans-action/{self.plan_b.pk}/modifier/").status_code, 404)
        self.assertEqual(c.get(f"/risques/plans-action/{self.plan_a.pk}/modifier/").status_code, 200)

    def test_analyse_incidents_filtree(self):
        r = self.client_de(self.agent_a).get("/incidents/analyse/")
        self.assertEqual(r.context["total_incidents"], 1)
        self.assertEqual(r.context["perte_brute"], 100)

    def test_analyse_incidents_admin_voit_tout(self):
        r = self.client_de(self.admin).get("/incidents/analyse/")
        self.assertEqual(r.context["total_incidents"], 2)

    def test_formulaire_risque_limite_la_direction_choisissable(self):
        form = RiskForm(user=self.agent_a)
        self.assertEqual(list(form.fields["direction"].queryset), [self.dir_a])

    def test_formulaire_risque_admin_non_limite(self):
        form = RiskForm(user=self.admin)
        self.assertEqual(form.fields["direction"].queryset.count(), 2)

    def test_formulaire_incident_limite_directions_et_risques(self):
        form = IncidentForm(user=self.agent_a)
        self.assertEqual(list(form.fields["direction"].queryset), [self.dir_a])
        self.assertEqual(list(form.fields["risques_lies"].queryset), [self.risque_a])

    def test_agent_ne_peut_pas_creer_incident_dans_une_autre_direction(self):
        data = {"titre": "T", "description": "d", "date_survenue": "2026-01-01", "gravite": "moderee",
                "direction": self.dir_b.pk, "sous_categorie": ""}
        form = IncidentForm(data=data, user=self.agent_a)
        self.assertFalse(form.is_valid())
        self.assertIn("direction", form.errors)


# --------------------------------------------------------------------------------------
class ActionsEnEcritureSeulementEnPostTests(BaseSecuriteTests):
    """SEC : ces actions modifiaient des données sur simple GET (CSRF par lien)."""

    def test_cloturer_campagne_refuse_get(self):
        camp = Campagne.objects.create(nom="C", date_ouverture=datetime.date(2026, 1, 1))
        c = self.client_de(self.admin)
        self.assertEqual(c.get(f"/risques/campagnes/{camp.pk}/cloturer/").status_code, 405)
        camp.refresh_from_db()
        self.assertEqual(camp.statut, Campagne.Statut.OUVERTE)
        c.post(f"/risques/campagnes/{camp.pk}/cloturer/")
        camp.refresh_from_db()
        self.assertEqual(camp.statut, Campagne.Statut.CLOTUREE)

    def test_marquer_realisee_refuse_get(self):
        obl = Obligation.objects.create(nom="O", periodicite="mensuelle", responsable=self.admin)
        occ = ObligationOccurrence.objects.create(obligation=obl, date_echeance=datetime.date(2026, 1, 1))
        c = self.client_de(self.admin)
        self.assertEqual(c.get(f"/echeances/{occ.pk}/realisee/").status_code, 405)
        occ.refresh_from_db()
        self.assertNotEqual(occ.statut, ObligationOccurrence.Statut.REALISEE)
        c.post(f"/echeances/{occ.pk}/realisee/")
        occ.refresh_from_db()
        self.assertEqual(occ.statut, ObligationOccurrence.Statut.REALISEE)


# --------------------------------------------------------------------------------------
class RenseignerExecutionAutorisationTests(BaseSecuriteTests):
    """SEC : n'importe quel utilisateur du périmètre pouvait renseigner (et clore) une exécution."""

    def setUp(self):
        super().setUp()
        self.executant = User.objects.create_user(username="exe", password="x", role="agent", direction=self.dir_a)
        self.superviseur = User.objects.create_user(username="sup", password="x", role="agent", direction=self.dir_a)
        self.curieux = User.objects.create_user(username="cur", password="x", role="agent", direction=self.dir_a)
        self.controle = Controle.objects.create(
            nom="Ctl", niveau="n1", frequence="mensuelle", executant=self.executant,
            superviseur=self.superviseur, direction=self.dir_a,
        )
        self.execution = ControleExecution.objects.create(controle=self.controle, date_prevue=datetime.date(2026, 1, 1))

    def _renseigner(self, user):
        return self.client_de(user).post(f"/controles/execution/{self.execution.pk}/", {
            "date_realisee": "2026-01-02", "resultat": "non_conforme", "commentaire": "x",
        })

    def test_tiers_sans_droit_refuse(self):
        self._renseigner(self.curieux)
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.resultat, ControleExecution.Resultat.NON_REALISE)

    def test_executant_autorise(self):
        self._renseigner(self.executant)
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.resultat, ControleExecution.Resultat.NON_CONFORME)

    def test_gestionnaire_des_controles_autorise(self):
        RolePermission.objects.update_or_create(role="risk_manager", permission="gerer_controles", defaults={"autorise": True})
        self._renseigner(self.rm)
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.resultat, ControleExecution.Resultat.NON_CONFORME)


# --------------------------------------------------------------------------------------
class FichiersTeleversesTests(BaseSecuriteTests):
    """SEC : aucun contrôle des fichiers déposés ; aucun téléchargement authentifié en production."""

    def test_extension_dangereuse_refusee(self):
        for nom in ("piege.html", "piege.svg", "piege.js", "piege.exe", "sans_extension"):
            with self.assertRaises(forms.ValidationError, msg=nom):
                valider_fichier_televerse(SimpleUploadedFile(nom, b"x"))

    def test_extension_autorisee_acceptee(self):
        for nom in ("doc.pdf", "preuve.PNG", "tableau.xlsx", "note.docx"):
            valider_fichier_televerse(SimpleUploadedFile(nom, b"x"))

    @override_settings(UPLOAD_MAX_BYTES=10)
    def test_fichier_trop_volumineux_refuse(self):
        with self.assertRaises(forms.ValidationError):
            valider_fichier_televerse(SimpleUploadedFile("gros.pdf", b"x" * 11))

    def test_formulaire_piece_jointe_refuse_html(self):
        from apps.incidents.forms import PieceJointeForm
        form = PieceJointeForm(files={"fichier": SimpleUploadedFile("xss.html", b"<script>alert(1)</script>")})
        self.assertFalse(form.is_valid())

    def test_televersement_via_la_vue_refuse_html(self):
        c = self.client_de(self.admin)
        c.post(f"/incidents/{self.incident_a.pk}/piece-jointe/", {"fichier": SimpleUploadedFile("xss.html", b"<script>")})
        self.assertEqual(self.incident_a.pieces_jointes.count(), 0)

    def test_telechargements_exigent_une_connexion_et_respectent_le_perimetre(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            pj_b = IncidentPieceJointe.objects.create(
                incident=self.incident_b, fichier=SimpleUploadedFile("secret.pdf", b"%PDF-secret"), depose_par=self.admin)
            pj_a = IncidentPieceJointe.objects.create(
                incident=self.incident_a, fichier=SimpleUploadedFile("ok.pdf", b"%PDF-ok"), depose_par=self.admin)
            url_a = reverse("incidents:telecharger_piece_jointe", args=[pj_a.pk])
            url_b = reverse("incidents:telecharger_piece_jointe", args=[pj_b.pk])

            self.assertEqual(Client().get(url_a).status_code, 302)  # anonyme -> connexion
            c = self.client_de(self.agent_a)
            self.assertEqual(c.get(url_b).status_code, 404)  # hors périmètre
            r = c.get(url_a)
            self.assertEqual(r.status_code, 200)
            self.assertIn("attachment", r["Content-Disposition"])
            self.assertEqual(r["X-Content-Type-Options"], "nosniff")
            self.assertEqual(b"".join(r.streaming_content), b"%PDF-ok")

    def test_telechargement_version_document(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            doc = Document.objects.create(titre="Charte", nature="charte", responsable=self.admin)
            v = DocumentVersion.objects.create(
                document=doc, version="1.0", fichier=SimpleUploadedFile("charte.pdf", b"%PDF"),
                date_approbation=datetime.date(2026, 1, 1), revue_prevue=datetime.date(2027, 1, 1), deposee_par=self.admin)
            url = reverse("bibliotheque:telecharger_version", args=[v.pk])
            self.assertEqual(Client().get(url).status_code, 302)
            r = self.client_de(self.agent_a).get(url)
            self.assertEqual(r.status_code, 200)
            self.assertIn("attachment", r["Content-Disposition"])

    def test_telechargement_fichier_absent_donne_404(self):
        v = DocumentVersion.objects.create(
            document=Document.objects.create(titre="D", nature="charte", responsable=self.admin), version="1.0",
            date_approbation=datetime.date(2026, 1, 1), revue_prevue=datetime.date(2027, 1, 1), deposee_par=self.admin)
        self.assertEqual(self.client_de(self.admin).get(reverse("bibliotheque:telecharger_version", args=[v.pk])).status_code, 404)

    def test_telechargement_preuve_controle_respecte_le_perimetre(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            ctl_b = Controle.objects.create(nom="CB", niveau="n1", frequence="mensuelle", executant=self.admin, superviseur=self.rm, direction=self.dir_b)
            ex_b = ControleExecution.objects.create(controle=ctl_b, date_prevue=datetime.date(2026, 1, 1), preuve=SimpleUploadedFile("p.pdf", b"%PDF"))
            url = reverse("controles:telecharger_preuve", args=[ex_b.pk])
            self.assertEqual(self.client_de(self.agent_a).get(url).status_code, 404)
            self.assertEqual(self.client_de(self.admin).get(url).status_code, 200)


# --------------------------------------------------------------------------------------
class BlocageBruteForceTests(TestCase):
    """SEC : aucune limite de tentatives sur la page de connexion."""

    def setUp(self):
        self.user = User.objects.create_user(username="victime", password="Mdp-Solide-9472!", role="agent")

    def _tenter(self, mot_de_passe, identifiant="victime"):
        return Client().post("/accounts/login/", {"username": identifiant, "password": mot_de_passe})

    def test_blocage_apres_trop_d_echecs_meme_avec_le_bon_mot_de_passe(self):
        for _ in range(5):
            self._tenter("mauvais")
        r = self._tenter("Mdp-Solide-9472!")
        self.assertEqual(r.status_code, 200)  # pas de redirection : connexion refusée
        self.assertTrue(r.context["bloque"])
        self.assertNotIn("_auth_user_id", r.client.session)

    def test_connexion_normale_non_bloquee(self):
        for _ in range(4):
            self._tenter("mauvais")
        r = self._tenter("Mdp-Solide-9472!")
        self.assertEqual(r.status_code, 302)

    def test_le_blocage_expire(self):
        for _ in range(5):
            self._tenter("mauvais")
        AuditLogEntry.objects.filter(modele="auth.ConnexionEchouee").update(horodatage=timezone.now() - timedelta(minutes=30))
        self.assertEqual(self._tenter("Mdp-Solide-9472!").status_code, 302)

    def test_le_blocage_est_insensible_a_la_casse(self):
        for _ in range(5):
            self._tenter("mauvais", identifiant="VICTIME")
        r = self._tenter("Mdp-Solide-9472!", identifiant="victime")
        self.assertEqual(r.status_code, 200)

    @override_settings(LOGIN_MAX_ECHECS_PAR_IP=3)
    def test_blocage_par_adresse_ip(self):
        for i in range(3):
            self._tenter("mauvais", identifiant=f"inconnu{i}")
        r = self._tenter("Mdp-Solide-9472!")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["bloque"])

    def test_identifiant_journalise_est_tronque(self):
        self._tenter("x", identifiant="a" * 400)
        entree = AuditLogEntry.objects.filter(modele="auth.ConnexionEchouee").latest("pk")
        self.assertLessEqual(len(entree.valeurs_apres["identifiant_saisi"]), 150)


class AdresseIPTests(TestCase):
    """SEC : l'IP du journal venait de la valeur de gauche de X-Forwarded-For, falsifiable."""

    def _req(self, xff=None, remote="10.0.0.9"):
        meta = {"REMOTE_ADDR": remote}
        if xff:
            meta["HTTP_X_FORWARDED_FOR"] = xff
        return RequestFactory().get("/", **meta)

    @override_settings(BEHIND_PROXY=True, TRUSTED_PROXY_COUNT=1)
    def test_derriere_un_proxy_on_prend_la_valeur_ajoutee_par_le_proxy(self):
        self.assertEqual(adresse_ip(self._req("6.6.6.6, 203.0.113.7")), "203.0.113.7")

    @override_settings(BEHIND_PROXY=True, TRUSTED_PROXY_COUNT=2)
    def test_deux_proxys_de_confiance(self):
        self.assertEqual(adresse_ip(self._req("6.6.6.6, 203.0.113.7, 10.1.1.1")), "203.0.113.7")

    @override_settings(BEHIND_PROXY=False)
    def test_sans_proxy_l_en_tete_est_ignore(self):
        self.assertEqual(adresse_ip(self._req("6.6.6.6", remote="198.51.100.4")), "198.51.100.4")


# --------------------------------------------------------------------------------------
class PolitiqueMotDePasseTests(BaseSecuriteTests):
    """SEC : les validateurs de mot de passe n'étaient jamais appliqués dans l'interface."""

    def test_creation_utilisateur_refuse_mot_de_passe_faible(self):
        data = {"username": "nouveau", "role": "agent", "password1": "12345678", "password2": "12345678", "is_active": True}
        form = UserCreateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_creation_utilisateur_accepte_mot_de_passe_solide(self):
        data = {"username": "nouveau", "role": "agent", "password1": "Zx!7-quartz-Lemon", "password2": "Zx!7-quartz-Lemon", "is_active": True}
        self.assertTrue(UserCreateForm(data=data).is_valid())

    def test_creation_refuse_mot_de_passe_trop_proche_de_l_identifiant(self):
        data = {"username": "ikraamsavadogo", "role": "agent", "password1": "ikraamsavadogo1", "password2": "ikraamsavadogo1", "is_active": True}
        self.assertFalse(UserCreateForm(data=data).is_valid())

    def test_reinitialisation_refuse_mot_de_passe_faible(self):
        form = ReinitialiserMotDePasseForm(data={"password1": "password", "password2": "password"}, user=self.agent_a)
        self.assertFalse(form.is_valid())

    def test_changement_refuse_mot_de_passe_faible(self):
        form = ChangerMotDePasseForm(self.agent_a, data={"ancien_mot_de_passe": "Mdp-Solide-9472!", "password1": "abc", "password2": "abc"})
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_changement_accepte_mot_de_passe_solide(self):
        form = ChangerMotDePasseForm(self.agent_a, data={
            "ancien_mot_de_passe": "Mdp-Solide-9472!", "password1": "Zx!7-quartz-Lemon", "password2": "Zx!7-quartz-Lemon"})
        self.assertTrue(form.is_valid(), form.errors)


# --------------------------------------------------------------------------------------
class ExcelInjectionEtImportTests(BaseSecuriteTests):
    """SEC : formules exécutées à l'ouverture de l'export ; import sans bornes."""

    def test_cellule_formule_neutralisee(self):
        for dangereux in ("=1+1", "+cmd|' /C calc'!A0", "-2+3", "@SUM(A1)", "\t=1"):
            self.assertTrue(securiser_cellule_excel(dangereux).startswith("'"), dangereux)
        self.assertEqual(securiser_cellule_excel("Risque normal"), "Risque normal")
        self.assertEqual(securiser_cellule_excel(12), 12)
        self.assertIsNone(securiser_cellule_excel(None))

    def test_export_neutralise_une_formule_dans_un_titre(self):
        Risk.objects.create(titre='=HYPERLINK("http://evil","clic")', categorie=self.risque_a.categorie, direction=self.dir_a, proprietaire=self.admin)
        ws = load_workbook(io.BytesIO(self.client_de(self.admin).get("/risques/export.xlsx").content)).active
        cellules = [row[1] for row in ws.iter_rows(min_row=2, values_only=True)]
        self.assertTrue(any(isinstance(c, str) and c.startswith("'=HYPERLINK") for c in cellules))
        self.assertFalse(any(isinstance(c, str) and c.startswith("=") for c in cellules))

    def _xlsx(self, lignes):
        wb = Workbook()
        ws = wb.active
        ws.append(["Titre du risque", "Catégorie", "Direction / Entité", "Processus", "Description"])
        for ligne in lignes:
            ws.append(ligne)
        buf = io.BytesIO()
        wb.save(buf)
        return SimpleUploadedFile("import.xlsx", buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_import_refuse_un_fichier_qui_n_est_pas_xlsx(self):
        c = self.client_de(self.admin)
        c.post("/risques/import/", {"fichier": SimpleUploadedFile("risques.csv", b"a,b")})
        self.assertEqual(Risk.objects.count(), 2)

    def test_import_borne_le_nombre_de_lignes(self):
        c = self.client_de(self.admin)
        c.post("/risques/import/", {"fichier": self._xlsx([[f"R{i}", "Crédit", "", "", ""] for i in range(2005)])})
        self.assertEqual(Risk.objects.count(), 2)  # rien n'a été importé

    def test_import_signale_un_titre_trop_long_sans_planter(self):
        c = self.client_de(self.admin)
        r = c.post("/risques/import/", {"fichier": self._xlsx([["T" * 300, "Crédit", "", "", ""], ["Titre valide", "Crédit", "", "", ""]])})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Risk.objects.filter(titre="Titre valide").count(), 1)
        self.assertEqual(Risk.objects.count(), 3)
        self.assertTrue(any("trop long" in e for e in r.context["resume"]["erreurs"]))

    def test_import_force_la_direction_d_un_utilisateur_restreint(self):
        RolePermission.objects.update_or_create(role="agent", permission="gerer_risques", defaults={"autorise": True})
        c = self.client_de(self.agent_a)
        c.post("/risques/import/", {"fichier": self._xlsx([["Import agent", "Crédit", "Direction B", "", ""]])})
        risque = Risk.objects.get(titre="Import agent")
        self.assertEqual(risque.direction, self.dir_a)
        self.assertEqual(Direction.objects.filter(nom="Direction B").count(), 1)


# --------------------------------------------------------------------------------------
class JournalAuditTests(BaseSecuriteTests):
    """SEC/BUG : la recherche du journal ne portait que sur les 300 dernières entrées."""

    def test_la_recherche_porte_sur_tout_le_journal(self):
        ancienne = AuditLogEntry.objects.create(action="creation", modele="x.Y", objet_id="1", objet_repr="Entrée très ancienne et unique")
        AuditLogEntry.objects.bulk_create([
            AuditLogEntry(action="creation", modele="x.Y", objet_id=str(i), objet_repr=f"bruit {i}") for i in range(320)
        ])
        AuditLogEntry.objects.filter(pk=ancienne.pk).update(horodatage=timezone.now() - timedelta(days=30))
        r = self.client_de(self.admin).get("/audit/?q=très+ancienne")
        self.assertContains(r, "Entrée très ancienne et unique")

    def test_avant_apres_sans_cache_global(self):
        self.risque_a.titre = "Modifié"
        self.risque_a.save()
        entree = AuditLogEntry.objects.filter(modele="risks.Risk", objet_id=str(self.risque_a.pk), action="modification").latest("pk")
        self.assertEqual(entree.valeurs_avant["titre"], "Risque visible A")
        self.assertEqual(entree.valeurs_apres["titre"], "Modifié")
        self.assertFalse(hasattr(__import__("apps.audit.signals", fromlist=["x"]), "_avant_cache"))

    def test_page_sessions_toujours_fonctionnelle(self):
        self.client_de(self.agent_a).get("/")
        r = self.client_de(self.admin).get("/parametres/sessions/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["utilisateurs"]), User.objects.count())


# --------------------------------------------------------------------------------------
class CampagneEtEvaluationTests(BaseSecuriteTests):
    """BUG : les évaluations n'étaient jamais rattachées à une campagne : la clôture ne figeait rien."""

    def test_evaluation_rattachee_a_la_campagne_ouverte(self):
        Campagne.objects.create(nom="Ancienne", date_ouverture=datetime.date(2025, 1, 1), statut=Campagne.Statut.CLOTUREE)
        ouverte = Campagne.objects.create(nom="Revue 2026", date_ouverture=datetime.date(2026, 1, 1))
        r = self.client_de(self.admin).post(f"/risques/{self.risque_a.pk}/evaluer/", {
            "probabilite_inherente": 3, "impact_inherent": 3, "qualite_dispositif_maitrise": 3,
            "probabilite_residuelle": 2, "impact_residuel": 2, "justification": "x"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.risque_a.derniere_evaluation.campagne, ouverte)

    def test_evaluation_sans_campagne_ouverte(self):
        self.client_de(self.admin).post(f"/risques/{self.risque_a.pk}/evaluer/", {
            "probabilite_inherente": 3, "impact_inherent": 3, "qualite_dispositif_maitrise": 3,
            "probabilite_residuelle": 2, "impact_residuel": 2})
        self.assertIsNone(self.risque_a.derniere_evaluation.campagne)


# --------------------------------------------------------------------------------------
class PerformanceTests(BaseSecuriteTests):
    """PERF : requêtes N+1 (derniere_evaluation ignorait le préchargement ; 7 requêtes de droits par page)."""

    def test_derniere_evaluation_utilise_le_prechargement(self):
        _evaluation(self.risque_a, self.admin, probabilite_residuelle=5, impact_residuel=5)
        with self.assertNumQueries(2):
            risques = list(Risk.objects.prefetch_related("evaluations"))
            niveaux = [r.derniere_evaluation for r in risques]
        self.assertEqual(len(niveaux), 2)
        self.assertEqual(self.risque_a.derniere_evaluation.score_residuel, 25)

    def test_derniere_evaluation_departage_les_egalites_de_date(self):
        a = _evaluation(self.risque_b, self.admin)
        b = _evaluation(self.risque_b, self.admin)
        RiskEvaluation.objects.filter(risque=self.risque_b).update(date_evaluation=a.date_evaluation)
        risque = Risk.objects.prefetch_related("evaluations").get(pk=self.risque_b.pk)
        self.assertEqual(risque.derniere_evaluation.pk, self.risque_b.derniere_evaluation.pk)

    def test_une_seule_requete_pour_les_droits_du_menu(self):
        requete = RequestFactory().get("/")
        requete.user = self.agent_a
        with self.assertNumQueries(1):
            contexte = permissions_front(requete)
        self.assertFalse(contexte["peut_gerer_risques"])
        RolePermission.objects.update_or_create(role="agent", permission="gerer_risques", defaults={"autorise": True})
        requete.user = User.objects.get(pk=self.agent_a.pk)
        self.assertTrue(permissions_front(requete)["peut_gerer_risques"])

    def test_admin_n_interroge_pas_la_table_des_droits(self):
        requete = RequestFactory().get("/")
        requete.user = self.admin
        with self.assertNumQueries(0):
            contexte = permissions_front(requete)
        self.assertTrue(all(contexte.values()))

    def test_controles_en_retard_filtres_en_base(self):
        ctl = Controle.objects.create(nom="C", niveau="n1", frequence="mensuelle", executant=self.admin, superviseur=self.rm, direction=self.dir_a)
        ControleExecution.objects.create(controle=ctl, date_prevue=datetime.date(2020, 1, 1))
        ControleExecution.objects.create(controle=ctl, date_prevue=datetime.date(2099, 1, 1))
        ControleExecution.objects.create(controle=ctl, date_prevue=datetime.date(2020, 1, 1), resultat="conforme", preuve="x/y.pdf")
        ControleExecution.objects.create(controle=ctl, date_prevue=datetime.date(2020, 1, 1), resultat="conforme")
        r = self.client_de(self.admin).get("/")
        self.assertEqual(r.context["total_controles_en_retard"], 1)
        self.assertEqual(len(r.context["executions_sans_preuve"]), 1)


# --------------------------------------------------------------------------------------
class DeploiementEtReglagesTests(TestCase):
    def test_sonde_de_sante_publique(self):
        r = Client().get("/healthz/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"ok")

    def test_api_auth_supprimee(self):
        self.assertEqual(Client().get("/api-auth/login/").status_code, 404)

    def _importer_settings(self, **env):
        base = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        base.update(env)
        base["PYTHONPATH"] = os.getcwd()
        return subprocess.run(
            [sys.executable, "-c", "import config.settings"], env=base, capture_output=True, text=True, cwd=os.getcwd())

    def test_refuse_de_demarrer_avec_une_cle_d_exemple(self):
        for cle in ("remplacez-par-une-cle-aleatoire-generee-avec-la-commande-ci-dessus", "trop-courte", ""):
            r = self._importer_settings(DJANGO_DEBUG="False", DJANGO_SECRET_KEY=cle)
            self.assertNotEqual(r.returncode, 0, cle)
            self.assertIn("DJANGO_SECRET_KEY", r.stderr)

    def test_demarre_avec_une_vraie_cle(self):
        r = self._importer_settings(DJANGO_DEBUG="False", DJANGO_SECRET_KEY="k" * 50)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_hotes_render_exacts_sans_joker(self):
        code = (
            "import config.settings as s;"
            "assert s.ALLOWED_HOSTS[-1]=='rose-x.onrender.com', s.ALLOWED_HOSTS;"
            "assert s.CSRF_TRUSTED_ORIGINS==['https://rose-x.onrender.com'], s.CSRF_TRUSTED_ORIGINS"
        )
        base = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        base.update(DJANGO_DEBUG="False", DJANGO_SECRET_KEY="k" * 50, RENDER_EXTERNAL_HOSTNAME="rose-x.onrender.com", PYTHONPATH=os.getcwd())
        r = subprocess.run([sys.executable, "-c", code], env=base, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

"""Tests de la bibliothèque documentaire : versions et complétude."""
import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.bibliotheque.models import Document, DocumentAttendu, DocumentVersion


class DocumentAttenduCompletudeTests(TestCase):
    """Le contrôle de complétude compare le corpus attendu aux documents
    réellement présents — un document non rattaché est « manquant »."""

    def setUp(self):
        self.responsable = User.objects.create_user(username="resp_doc", password="x", role="risk_manager")

    def test_document_attendu_sans_document_est_manquant(self):
        attendu = DocumentAttendu.objects.create(titre="Politique de crédit", nature="politique")
        self.assertEqual(attendu.etat, "manquant")

    def test_document_attendu_rattache_herite_etat_du_document(self):
        document = Document.objects.create(titre="Politique de conformité", nature="politique", responsable=self.responsable)
        DocumentVersion.objects.create(
            document=document, version="1.0",
            date_approbation=datetime.date(2025, 1, 1), revue_prevue=datetime.date(2099, 1, 1),
            deposee_par=self.responsable,
        )
        attendu = DocumentAttendu.objects.create(titre="Politique de conformité", nature="politique", document=document)
        self.assertEqual(attendu.etat, "a_jour")


class DocumentVersionArchivageTests(TestCase):
    """Une version archivée n'est jamais écrasée ; une nouvelle révision crée
    une nouvelle ligne, l'ancienne reste consultable."""

    def setUp(self):
        self.responsable = User.objects.create_user(username="resp_doc2", password="x", role="risk_manager")
        self.document = Document.objects.create(titre="Charte de l'audit interne", nature="charte", responsable=self.responsable)

    def test_version_archivee_non_modifiable(self):
        version = DocumentVersion.objects.create(
            document=self.document, version="1.0",
            date_approbation=datetime.date(2025, 1, 1), revue_prevue=datetime.date(2026, 1, 1),
            deposee_par=self.responsable,
        )
        version.version = "1.1 — modifiée en douce"
        with self.assertRaises(PermissionError):
            version.save()

    def test_version_archivee_non_supprimable(self):
        version = DocumentVersion.objects.create(
            document=self.document, version="1.0",
            date_approbation=datetime.date(2025, 1, 1), revue_prevue=datetime.date(2026, 1, 1),
            deposee_par=self.responsable,
        )
        with self.assertRaises(PermissionError):
            version.delete()

    def test_derniere_version_est_la_plus_recente(self):
        DocumentVersion.objects.create(
            document=self.document, version="1.0",
            date_approbation=datetime.date(2025, 1, 1), revue_prevue=datetime.date(2026, 1, 1),
            deposee_par=self.responsable,
        )
        DocumentVersion.objects.create(
            document=self.document, version="2.0",
            date_approbation=datetime.date(2026, 6, 1), revue_prevue=datetime.date(2027, 6, 1),
            deposee_par=self.responsable,
        )
        self.assertEqual(self.document.derniere_version.version, "2.0")
        self.assertEqual(self.document.versions.count(), 2)

    def test_document_en_retard_si_revue_depassee(self):
        DocumentVersion.objects.create(
            document=self.document, version="1.0",
            date_approbation=datetime.date(2020, 1, 1), revue_prevue=datetime.date(2021, 1, 1),
            deposee_par=self.responsable,
        )
        self.assertEqual(self.document.etat, "en_retard")

from django.conf import settings
from django.db import models
from django.utils import timezone


class Document(models.Model):
    """Un document normatif (charte, politique, procédure, plan).

    Le document lui-même ne porte plus le fichier ni les dates directement :
    chaque révision est une DocumentVersion distincte, jamais écrasée. Ce qui
    s'affiche comme « le document » reflète toujours sa dernière version.
    """

    class Nature(models.TextChoices):
        CHARTE = "charte", "Charte"
        POLITIQUE = "politique", "Politique"
        PROCEDURE = "procedure", "Procédure"
        PLAN = "plan", "Plan"

    titre = models.CharField(max_length=200)
    nature = models.CharField(max_length=20, choices=Nature.choices)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="documents_dont_je_suis_responsable")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Bibliothèque documentaire"
        ordering = ["titre"]

    def __str__(self):
        return self.titre

    @property
    def derniere_version(self):
        return self.versions.order_by("-date_approbation", "-id").first()

    @property
    def etat(self):
        derniere = self.derniere_version
        if not derniere:
            return "sans_version"
        jours = (derniere.revue_prevue - timezone.now().date()).days
        if jours < 0:
            return "en_retard"
        if jours <= 60:
            return "proche"
        return "a_jour"

    @property
    def jours_avant_revue(self):
        derniere = self.derniere_version
        if not derniere:
            return None
        return (derniere.revue_prevue - timezone.now().date()).days


class DocumentVersion(models.Model):
    """Une révision archivée d'un document. Jamais modifiée après coup —
    une nouvelle révision crée une nouvelle ligne, l'ancienne reste consultable
    et téléchargeable telle quelle (exigence d'auditabilité)."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=20, help_text="ex: 1.0, 2.1, 3.0")
    fichier = models.FileField(upload_to="bibliotheque/%Y/%m/", null=True, blank=True)
    date_approbation = models.DateField()
    revue_prevue = models.DateField()
    note_revision = models.TextField(blank=True, help_text="Qu'est-ce qui a changé dans cette révision ?")
    deposee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="versions_deposees")
    deposee_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Version de document"
        verbose_name_plural = "Versions de document"
        ordering = ["-date_approbation", "-id"]
        unique_together = ("document", "version")

    def __str__(self):
        return f"{self.document.titre} — v{self.version}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("Une version archivée ne peut pas être modifiée — créez une nouvelle version.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Une version archivée ne peut pas être supprimée.")

from django.conf import settings
from django.db import models


class Obligation(models.Model):
    """Obligation réglementaire ou interne soumise à échéance récurrente."""

    class Periodicite(models.TextChoices):
        MENSUELLE = "mensuelle", "Mensuelle"
        TRIMESTRIELLE = "trimestrielle", "Trimestrielle"
        SEMESTRIELLE = "semestrielle", "Semestrielle"
        ANNUELLE = "annuelle", "Annuelle"
        PONCTUELLE = "ponctuelle", "Ponctuelle"

    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    texte_reference = models.CharField(
        max_length=255, blank=True, help_text="Référence réglementaire (ex: circulaire BCEAO n°...)"
    )
    periodicite = models.CharField(max_length=20, choices=Periodicite.choices)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="obligations_dont_je_suis_responsable")
    active = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Obligation"
        verbose_name_plural = "Obligations"

    def __str__(self):
        return self.nom


class ObligationOccurrence(models.Model):
    """Une échéance concrète générée pour une obligation donnée."""

    class Statut(models.TextChoices):
        A_VENIR = "a_venir", "À venir"
        EN_RETARD = "en_retard", "En retard"
        REALISEE = "realisee", "Réalisée"

    obligation = models.ForeignKey(Obligation, on_delete=models.CASCADE, related_name="occurrences")
    date_echeance = models.DateField()
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.A_VENIR)
    date_realisation = models.DateField(null=True, blank=True)
    preuve = models.FileField(upload_to="obligations/preuves/%Y/%m/", null=True, blank=True)
    commentaire = models.TextField(blank=True)

    class Meta:
        verbose_name = "Échéance"
        verbose_name_plural = "Échéances"
        ordering = ["date_echeance"]
        unique_together = ("obligation", "date_echeance")

    def __str__(self):
        return f"{self.obligation} — échéance {self.date_echeance:%d/%m/%Y}"

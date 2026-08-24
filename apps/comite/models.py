from django.conf import settings
from django.db import models


class SeanceComite(models.Model):
    """Une séance du comité des risques (planifiée ou tenue)."""

    class Statut(models.TextChoices):
        PLANIFIEE = "planifiee", "Planifiée"
        TENUE = "tenue", "Tenue"
        ANNULEE = "annulee", "Annulée"

    libelle = models.CharField(max_length=200)
    date_seance = models.DateField()
    direction = models.ForeignKey("accounts.Direction", null=True, blank=True, on_delete=models.SET_NULL, related_name="seances_comite")
    participants = models.TextField(blank=True, help_text="Un nom par ligne, ou liste séparée par des virgules")
    ordre_du_jour = models.TextField(blank=True)
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.PLANIFIEE)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="seances_creees")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Séance du comité des risques"
        verbose_name_plural = "Séances du comité des risques"
        ordering = ["-date_seance"]

    def __str__(self):
        return f"{self.libelle} — {self.date_seance:%d/%m/%Y}"

    @property
    def periode_debut(self):
        """Début de la période couverte par le dossier : 90 jours avant la séance."""
        import datetime
        return self.date_seance - datetime.timedelta(days=90)

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

    @property
    def nb_decisions(self):
        return self.decisions.count()


class DecisionComite(models.Model):
    """Une décision prise en séance, avec son propre suivi d'exécution —
    un comité qui redécouvre à chaque séance qu'une décision n'a pas été
    appliquée perd son autorité, d'où ce suivi séparé des simples minutes."""

    class Statut(models.TextChoices):
        A_EXECUTER = "a_executer", "À exécuter"
        EN_COURS = "en_cours", "En cours"
        EXECUTEE = "executee", "Exécutée"
        EN_RETARD = "en_retard", "En retard"

    seance = models.ForeignKey(SeanceComite, on_delete=models.CASCADE, related_name="decisions")
    libelle = models.TextField()
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="decisions_comite_a_executer")
    echeance = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.A_EXECUTER)
    date_execution = models.DateField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Décision de comité"
        verbose_name_plural = "Décisions de comité"
        ordering = ["echeance"]

    def __str__(self):
        return self.libelle[:80]

    def calculer_statut(self):
        from django.utils import timezone
        if self.date_execution:
            return self.Statut.EXECUTEE
        if self.echeance and self.echeance < timezone.now().date():
            return self.Statut.EN_RETARD
        return self.statut if self.statut in (self.Statut.A_EXECUTER, self.Statut.EN_COURS) else self.Statut.A_EXECUTER

    def save(self, *args, **kwargs):
        self.statut = self.calculer_statut()
        super().save(*args, **kwargs)

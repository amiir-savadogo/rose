from django.conf import settings
from django.db import models

from apps.risks.models import Risk


class Controle(models.Model):
    """Un contrôle récurrent (opérationnel ou indépendant) rattaché à un risque."""

    class Niveau(models.TextChoices):
        NIVEAU_1 = "n1", "Niveau 1 — contrôle opérationnel"
        NIVEAU_2 = "n2", "Niveau 2 — contrôle indépendant"

    class Frequence(models.TextChoices):
        QUOTIDIENNE = "quotidienne", "Quotidien"
        HEBDOMADAIRE = "hebdomadaire", "Hebdomadaire"
        MENSUELLE = "mensuelle", "Mensuel"
        TRIMESTRIELLE = "trimestrielle", "Trimestriel"
        SEMESTRIELLE = "semestrielle", "Semestriel"
        ANNUELLE = "annuelle", "Annuel"

    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    risque = models.ForeignKey(Risk, null=True, blank=True, on_delete=models.SET_NULL, related_name="controles")
    direction = models.ForeignKey("accounts.Direction", null=True, blank=True, on_delete=models.SET_NULL, related_name="controles")
    niveau = models.CharField(max_length=5, choices=Niveau.choices, default=Niveau.NIVEAU_1)
    frequence = models.CharField(max_length=20, choices=Frequence.choices)
    executant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="controles_a_executer")
    superviseur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="controles_a_superviser")
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contrôle"
        verbose_name_plural = "Contrôles"
        constraints = [
            models.CheckConstraint(
                check=~models.Q(executant=models.F("superviseur")),
                name="controle_executant_different_superviseur",
            )
        ]

    def __str__(self):
        return self.nom

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.executant_id and self.superviseur_id and self.executant_id == self.superviseur_id:
            raise ValidationError("L'exécutant et le superviseur doivent être deux personnes différentes.")

    @property
    def derniere_execution(self):
        return self.executions.order_by("-date_prevue").first()


class ControleExecution(models.Model):
    """Une exécution planifiée ou réalisée d'un contrôle."""

    class Resultat(models.TextChoices):
        NON_REALISE = "non_realise", "Non réalisé"
        CONFORME = "conforme", "Conforme"
        NON_CONFORME = "non_conforme", "Non conforme"
        SANS_PREUVE = "sans_preuve", "Sans preuve archivée"

    controle = models.ForeignKey(Controle, on_delete=models.CASCADE, related_name="executions")
    date_prevue = models.DateField()
    date_realisee = models.DateField(null=True, blank=True)
    resultat = models.CharField(max_length=20, choices=Resultat.choices, default=Resultat.NON_REALISE)
    preuve = models.FileField(upload_to="controles/preuves/%Y/%m/", null=True, blank=True)
    commentaire = models.TextField(blank=True)

    class Meta:
        verbose_name = "Exécution de contrôle"
        verbose_name_plural = "Exécutions de contrôle"
        ordering = ["-date_prevue"]

    def __str__(self):
        return f"{self.controle} — {self.date_prevue:%d/%m/%Y}"

    @property
    def en_retard(self):
        from django.utils import timezone
        return self.resultat == self.Resultat.NON_REALISE and self.date_prevue < timezone.now().date()

    @property
    def preuve_manquante(self):
        """Un contrôle réalisé (conforme ou non) sans preuve archivée est signalé —
        « un contrôle sans preuve est un contrôle non fait »."""
        return self.resultat in (self.Resultat.CONFORME, self.Resultat.NON_CONFORME) and not self.preuve

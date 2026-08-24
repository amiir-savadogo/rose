from django.conf import settings
from django.db import models


class Campagne(models.Model):
    """Campagne de revue des risques (ex: 'Revue annuelle 2026').

    Les évaluations sont rattachées à une campagne. Une fois la campagne
    clôturée, ses évaluations sont figées (affichage seul, non modifiables).
    """

    class Statut(models.TextChoices):
        OUVERTE = "ouverte", "Ouverte"
        CLOTUREE = "cloturee", "Clôturée"

    nom = models.CharField(max_length=150)
    date_ouverture = models.DateField()
    date_cloture = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.OUVERTE)
    seuil_appetence = models.IntegerField(
        default=8, help_text="Score résiduel (probabilité × impact) à partir duquel un risque est hors appétence"
    )

    class Meta:
        verbose_name = "Campagne de revue"
        verbose_name_plural = "Campagnes de revue"
        ordering = ["-date_ouverture"]

    def __str__(self):
        return self.nom

    @property
    def est_figee(self):
        return self.statut == self.Statut.CLOTUREE


class RiskCategory(models.Model):
    """Catégorie de risque (fraude, processus, SI, RH, prestataires externes...)."""

    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catégorie de risque"
        verbose_name_plural = "Catégories de risque"

    def __str__(self):
        return self.nom


class NiveauCotation(models.IntegerChoices):
    TRES_FAIBLE = 1, "Très faible"
    FAIBLE = 2, "Faible"
    MOYEN = 3, "Moyen"
    ELEVE = 4, "Élevé"
    TRES_ELEVE = 5, "Très élevé"


class Risk(models.Model):
    """Un risque opérationnel identifié dans la cartographie."""

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        MAITRISE = "maitrise", "Maîtrisé"
        CLOTURE = "cloture", "Clôturé"

    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    categorie = models.ForeignKey(RiskCategory, on_delete=models.PROTECT, related_name="risques")
    direction = models.ForeignKey(
        "accounts.Direction", null=True, blank=True, on_delete=models.SET_NULL, related_name="risques"
    )
    processus = models.CharField(max_length=200, blank=True, help_text="Processus métier concerné")
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="risques_dont_je_suis_proprietaire"
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Risque"
        verbose_name_plural = "Risques"
        ordering = ["-modifie_le"]

    def __str__(self):
        return self.titre

    @property
    def derniere_evaluation(self):
        return self.evaluations.order_by("-date_evaluation").first()


class RiskEvaluation(models.Model):
    """Une évaluation du risque à un instant T : inhérent / maîtrise / résiduel.

    Chaque nouvelle évaluation crée une nouvelle ligne (append-only) afin de
    conserver l'historique complet requis par le cahier des charges — on ne
    modifie jamais une évaluation passée.
    """

    risque = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name="evaluations")
    campagne = models.ForeignKey(Campagne, null=True, blank=True, on_delete=models.SET_NULL, related_name="evaluations")
    probabilite_inherente = models.IntegerField(choices=NiveauCotation.choices)
    impact_inherent = models.IntegerField(choices=NiveauCotation.choices)
    qualite_dispositif_maitrise = models.IntegerField(
        choices=NiveauCotation.choices, help_text="1 = dispositif très faible, 5 = dispositif très solide"
    )
    probabilite_residuelle = models.IntegerField(choices=NiveauCotation.choices)
    impact_residuel = models.IntegerField(choices=NiveauCotation.choices)
    justification = models.TextField(blank=True)
    evalue_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evaluations_realisees")
    date_evaluation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Évaluation de risque"
        verbose_name_plural = "Évaluations de risque"
        ordering = ["-date_evaluation"]

    def __str__(self):
        return f"Évaluation de {self.risque} du {self.date_evaluation:%d/%m/%Y}"

    @property
    def score_inherent(self):
        return self.probabilite_inherente * self.impact_inherent

    @property
    def score_residuel(self):
        return self.probabilite_residuelle * self.impact_residuel

    def save(self, *args, **kwargs):
        if self.pk and self.campagne and self.campagne.est_figee:
            raise PermissionError("Cette évaluation appartient à une campagne clôturée et ne peut plus être modifiée.")
        super().save(*args, **kwargs)

    @property
    def niveau_residuel(self):
        return classer_score(self.score_residuel)

    @property
    def niveau_residuel_display(self):
        return {"critique": "Critique", "eleve": "Élevé", "modere": "Modéré", "faible": "Faible"}[self.niveau_residuel]


def classer_score(score):
    """Classe un score (probabilité × impact, échelle 1-25) en niveau qualitatif."""
    if score >= 15:
        return "critique"
    if score >= 8:
        return "eleve"
    if score >= 4:
        return "modere"
    return "faible"


class ActionPlan(models.Model):
    """Mesure corrective associée à un risque (ou à une autre origine : incident, audit...)."""

    class Statut(models.TextChoices):
        A_LANCER = "a_lancer", "À lancer"
        EN_COURS = "en_cours", "En cours"
        EN_RETARD = "en_retard", "En retard"
        CLOS = "clos", "Clos"

    class Origine(models.TextChoices):
        RISQUE = "risque", "Cartographie des risques"
        INCIDENT = "incident", "Incident"
        AUDIT_INTERNE = "audit_interne", "Audit interne"
        AUTORITE_SUPERVISION = "autorite_supervision", "Autorité de supervision"
        AUTRE = "autre", "Autre"

    risque = models.ForeignKey(Risk, null=True, blank=True, on_delete=models.CASCADE, related_name="plans_action")
    origine = models.CharField(max_length=25, choices=Origine.choices, default=Origine.RISQUE)
    description = models.TextField()
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="actions_a_realiser")
    echeance = models.DateField()
    avancement = models.IntegerField(default=0, help_text="Pourcentage d'avancement, de 0 à 100")
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.A_LANCER)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plan d'action"
        verbose_name_plural = "Plans d'action"
        ordering = ["echeance"]

    def __str__(self):
        return f"Action sur {self.risque} — échéance {self.echeance:%d/%m/%Y}" if self.risque else self.description[:60]

    def calculer_statut(self):
        """Le statut suit mécaniquement l'avancement : 100% -> Clos, 0-10% -> À lancer,
        échéance dépassée sans clôture -> En retard, sinon En cours."""
        from django.utils import timezone
        if self.avancement >= 100:
            return self.Statut.CLOS
        if self.echeance and self.echeance < timezone.now().date():
            return self.Statut.EN_RETARD
        if self.avancement <= 10:
            return self.Statut.A_LANCER
        return self.Statut.EN_COURS

    def save(self, *args, **kwargs):
        self.statut = self.calculer_statut()
        super().save(*args, **kwargs)


class KeyRiskIndicator(models.Model):
    """Indicateur clé de risque (KRI) rattaché à un risque, avec seuil d'alerte."""

    risque = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name="indicateurs")
    nom = models.CharField(max_length=200)
    unite = models.CharField(max_length=50, blank=True, help_text="ex: nombre, %, FCFA")
    seuil_alerte = models.DecimalField(max_digits=12, decimal_places=2)
    valeur_actuelle = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Indicateur clé de risque (KRI)"
        verbose_name_plural = "Indicateurs clés de risque (KRI)"

    def __str__(self):
        return f"{self.nom} — {self.risque}"

    @property
    def en_alerte(self):
        if self.valeur_actuelle is None:
            return False
        return self.valeur_actuelle >= self.seuil_alerte

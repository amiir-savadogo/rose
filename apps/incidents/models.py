from django.conf import settings
from django.db import models

from apps.risks.models import Risk


class Incident(models.Model):
    """Incident opérationnel déclaré par un agent."""

    class Gravite(models.TextChoices):
        MINEURE = "mineure", "Mineure"
        MODEREE = "moderee", "Modérée"
        MAJEURE = "majeure", "Majeure"
        CRITIQUE = "critique", "Critique"

    class Statut(models.TextChoices):
        DECLARE = "declare", "Déclaré"
        EN_ANALYSE = "en_analyse", "En cours d'analyse"
        EN_TRAITEMENT = "en_traitement", "En traitement"
        CLOTURE = "cloture", "Clôturé"

    class CategorieEvenement(models.TextChoices):
        """Catégories d'événements de risque opérationnel (typologie Bâle II)."""
        FRAUDE_INTERNE = "fraude_interne", "Fraude interne"
        FRAUDE_EXTERNE = "fraude_externe", "Fraude externe"
        PRATIQUES_RH = "pratiques_rh", "Pratiques en matière d'emploi"
        CLIENTS_PRODUITS = "clients_produits", "Clients, produits et pratiques commerciales"
        DOMMAGES_ACTIFS = "dommages_actifs", "Dommages aux actifs corporels"
        INTERRUPTION_SI = "interruption_si", "Interruption d'activité et dysfonctionnement des systèmes"
        EXECUTION_LIVRAISON = "execution_livraison", "Exécution, livraison et gestion des processus"

    titre = models.CharField(max_length=200)
    description = models.TextField()
    categorie_evenement = models.CharField(max_length=30, choices=CategorieEvenement.choices, blank=True)
    date_survenue = models.DateField()
    date_detection = models.DateField(null=True, blank=True)
    direction = models.ForeignKey("accounts.Direction", null=True, blank=True, on_delete=models.SET_NULL, related_name="incidents")
    processus_concerne = models.CharField(max_length=200, blank=True)
    montant_impact = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Impact estimé (usage libre)")
    perte_brute = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    recuperation = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    gravite = models.CharField(max_length=20, choices=Gravite.choices, default=Gravite.MODEREE)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.DECLARE)
    risques_lies = models.ManyToManyField(Risk, blank=True, related_name="incidents")
    declare_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incidents_declares"
    )
    assigne_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="incidents_assignes"
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ["-cree_le"]

    def __str__(self):
        return self.titre

    @property
    def delai_detection_jours(self):
        if self.date_detection:
            return (self.date_detection - self.date_survenue).days
        return None

    @property
    def perte_nette(self):
        if self.perte_brute is None:
            return None
        return self.perte_brute - (self.recuperation or 0)


class IncidentPieceJointe(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="pieces_jointes")
    fichier = models.FileField(upload_to="incidents/%Y/%m/")
    depose_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    depose_le = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pièce jointe — {self.incident}"


class IncidentCommentaire(models.Model):
    """Commentaire ou changement de statut horodaté (historique de traitement)."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="commentaires")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texte = models.TextField()
    ancien_statut = models.CharField(max_length=20, blank=True)
    nouveau_statut = models.CharField(max_length=20, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["cree_le"]

    def __str__(self):
        return f"Commentaire sur {self.incident} par {self.auteur}"

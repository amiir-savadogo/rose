from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """Entrée du journal d'audit — non modifiable et non supprimable.

    Enregistre automatiquement (via signaux, voir signals.py) toute création,
    modification ou suppression sur les modèles suivis. Seuls les profils
    Contrôleur et Administrateur peuvent consulter/exporter ce journal
    (voir permissions dans l'admin et les vues DRF).
    """

    class Action(models.TextChoices):
        CREATION = "creation", "Création"
        MODIFICATION = "modification", "Modification"
        SUPPRESSION = "suppression", "Suppression"

    horodatage = models.DateTimeField(auto_now_add=True, db_index=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="actions_journalisees"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    modele = models.CharField(max_length=100, help_text="Nom du modèle concerné, ex: risks.Risk")
    objet_id = models.CharField(max_length=50)
    objet_repr = models.CharField(max_length=255, blank=True)
    valeurs_avant = models.JSONField(null=True, blank=True)
    valeurs_apres = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Entrée du journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ["-horodatage"]

    def __str__(self):
        return f"[{self.horodatage:%d/%m/%Y %H:%M}] {self.get_action_display()} — {self.modele} #{self.objet_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Une entrée du journal d'audit ne peut jamais être modifiée.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Une entrée du journal d'audit ne peut jamais être supprimée.")

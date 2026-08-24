from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Administrateur"
    RISK_MANAGER = "risk_manager", "Risk Manager"
    CONTROLEUR = "controleur", "Contrôleur / Auditeur"
    AGENT = "agent", "Agent opérationnel"
    DIRECTION = "direction", "Direction"


class Direction(models.Model):
    """Direction ou entité interne de l'institution cliente (périmètre d'accès)."""

    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Direction / Entité"
        verbose_name_plural = "Directions / Entités"

    def __str__(self):
        return self.nom


class RoseUserManager(UserManager):
    """Comme le manager standard, sauf que createsuperuser positionne aussi
    le rôle métier 'admin' — sans quoi un superutilisateur créé en ligne de
    commande resterait vu comme un simple agent côté front (le champ 'role'
    est propre à Rose ; Django ne le connaît pas nativement)."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Utilisateur de la plateforme Rose.

    Chaque utilisateur a un rôle (droits fonctionnels) et, optionnellement,
    un rattachement à une direction (périmètre de visibilité des données).
    """

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)
    direction = models.ForeignKey(
        Direction, null=True, blank=True, on_delete=models.SET_NULL, related_name="utilisateurs"
    )
    telephone = models.CharField(max_length=30, blank=True)
    notif_email = models.BooleanField(default=True, verbose_name="Notifications par courriel")
    notif_application = models.BooleanField(default=True, verbose_name="Notifications dans l'application")
    notif_sms = models.BooleanField(default=False, verbose_name="Notifications par SMS")

    objects = RoseUserManager()

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_risk_manager(self):
        return self.role == Role.RISK_MANAGER

    @property
    def is_controleur(self):
        return self.role == Role.CONTROLEUR


class Permission(models.TextChoices):
    """Actions de gestion (écriture) que l'on peut déléguer à un rôle autre qu'Administrateur.

    La gestion des utilisateurs/rôles/campagnes reste volontairement réservée
    aux administrateurs et n'apparaît pas ici — voir RolePermission plus bas.
    """
    GERER_RISQUES = "gerer_risques", "Créer / modifier un risque, une évaluation, un plan d'action"
    TRAITER_INCIDENTS = "traiter_incidents", "Changer le statut d'un incident"
    GERER_CONTROLES = "gerer_controles", "Créer / modifier un contrôle et ses exécutions"
    GERER_OBLIGATIONS = "gerer_obligations", "Créer / modifier une obligation réglementaire"
    GERER_BIBLIOTHEQUE = "gerer_bibliotheque", "Ajouter / modifier un document de la bibliothèque"
    CONSULTER_AUDIT = "consulter_audit", "Consulter le journal d'audit"


class RolePermission(models.Model):
    """Une permission accordée (ou non) à un rôle donné.

    Administrateur n'a pas besoin d'entrée : il a toujours tous les droits
    (voir apps/accounts/permissions.py). Cette table ne couvre que les
    quatre autres rôles, pour rester simple et éviter qu'un administrateur
    ne se retire lui-même l'accès par erreur.
    """

    role = models.CharField(max_length=20, choices=Role.choices)
    permission = models.CharField(max_length=30, choices=Permission.choices)
    autorise = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Permission de rôle"
        verbose_name_plural = "Permissions de rôle"
        unique_together = ("role", "permission")

    def __str__(self):
        return f"{self.get_role_display()} — {self.get_permission_display()} : {'oui' if self.autorise else 'non'}"

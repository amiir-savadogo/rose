"""Règles de permission centralisées pour le front (templates et vues).

Administrateur (et tout superutilisateur Django) a TOUJOURS tous les droits,
quoi que contienne la table RolePermission — c'est un garde-fou volontaire :
un administrateur ne peut jamais se retrouver bloqué hors de son propre
logiciel en modifiant la matrice des rôles par erreur.

Pour les quatre autres rôles, chaque action de gestion est vérifiée dans la
table RolePermission, modifiable depuis Paramètres > Rôles et permissions.
"""


def _autorise(user, cle_permission):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_admin:
        return True
    from .models import RolePermission
    return RolePermission.objects.filter(role=user.role, permission=cle_permission, autorise=True).exists()


def peut_gerer_risques(user):
    return _autorise(user, "gerer_risques")


def peut_traiter_incidents(user):
    return _autorise(user, "traiter_incidents")


def peut_gerer_controles(user):
    return _autorise(user, "gerer_controles")


def peut_gerer_obligations(user):
    return _autorise(user, "gerer_obligations")


def peut_gerer_bibliotheque(user):
    return _autorise(user, "gerer_bibliotheque")


def peut_administrer(user):
    return user.is_authenticated and (user.is_superuser or user.is_admin)


def peut_consulter_audit(user):
    return _autorise(user, "consulter_audit")


def peut_gerer_echeance(user, occurrence):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_admin:
        return True
    return peut_gerer_obligations(user) or occurrence.obligation.responsable_id == user.id

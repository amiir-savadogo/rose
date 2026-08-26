"""Filtrage par périmètre (entité/direction) — appliqué à la requête, jamais
seulement à l'affichage, pour qu'il ne se contourne pas en modifiant l'URL.

Politique retenue : les rôles à vocation transverse (Administrateur, Risk
Manager, Contrôleur) voient toutes les entités — c'est le sens de leur
fonction de supervision. Les rôles « métier » (Agent, Direction) ne voient
que les objets rattachés à leur propre direction ; un utilisateur sans
direction assignée est traité comme rattaché au Siège et ne voit que les
objets sans direction renseignée (comportement restrictif par défaut).
"""

ROLES_PERIMETRE_GLOBAL = {"admin", "risk_manager", "controleur"}


def a_perimetre_restreint(user):
    return user.is_authenticated and not user.is_superuser and user.role not in ROLES_PERIMETRE_GLOBAL


def filtrer_par_perimetre(queryset, user, champ="direction"):
    """Restreint un queryset au périmètre de l'utilisateur, si son rôle l'exige.
    `champ` est le nom du champ FK vers Direction sur le modèle (direct,
    ex: 'direction', ou via relation, ex: 'risque__direction')."""
    if not a_perimetre_restreint(user):
        return queryset
    return queryset.filter(**{champ: user.direction})


def objet_ou_404_perimetre(model_ou_queryset, user, pk, champ="direction"):
    """Comme get_object_or_404, mais applique le filtrage par périmètre AVANT
    de chercher l'objet — un utilisateur restreint qui devine l'ID d'un objet
    hors de son périmètre reçoit un 404, jamais l'objet lui-même. À utiliser
    pour toute action sur un objet précis (modifier, évaluer, programmer...),
    pas seulement pour les listes."""
    from django.shortcuts import get_object_or_404
    if hasattr(model_ou_queryset, "objects"):
        queryset = model_ou_queryset.objects.all()
    else:
        queryset = model_ou_queryset
    queryset = filtrer_par_perimetre(queryset, user, champ=champ)
    return get_object_or_404(queryset, pk=pk)

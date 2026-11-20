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
    pas seulement pour les listes.

    N'a de sens que pour les objets rattachés à une direction (Risk, Incident,
    Controle, KeyRiskIndicator via risque__direction). Les objets suivants sont
    délibérément institutionnels, sans notion de direction, et ne passent donc
    jamais par cette fonction : Document/DocumentVersion (bibliothèque),
    Obligation/ObligationOccurrence (calendrier réglementaire), Campagne (revue
    des risques), SeanceComite/DecisionComite (comité transversal, voir
    apps/comite/views.py). Ce n'est pas un oubli — ces modèles n'ont tout
    simplement pas de champ direction."""
    from django.shortcuts import get_object_or_404
    if hasattr(model_ou_queryset, "objects"):
        queryset = model_ou_queryset.objects.all()
    else:
        queryset = model_ou_queryset
    queryset = filtrer_par_perimetre(queryset, user, champ=champ)
    return get_object_or_404(queryset, pk=pk)


def limiter_aux_directions_visibles(champ_formulaire, user):
    """Pour un utilisateur à périmètre restreint, ne propose que sa propre direction (ou aucune,
    s'il n'en a pas) dans un champ de choix de direction : sans cela, il pourrait créer ou
    déplacer un objet vers une direction qu'il n'a pas le droit de voir."""
    if user is None or champ_formulaire is None or not a_perimetre_restreint(user):
        return
    queryset = champ_formulaire.queryset
    champ_formulaire.queryset = queryset.filter(pk=user.direction_id) if user.direction_id else queryset.none()


def limiter_aux_objets_du_perimetre(champ_formulaire, user, champ="direction"):
    """Limite un champ de choix d'objets (risque, contrôle...) à ceux du périmètre de l'utilisateur,
    pour ne pas lui révéler (liste déroulante) ni lui laisser rattacher des objets hors périmètre."""
    if user is None or champ_formulaire is None:
        return
    champ_formulaire.queryset = filtrer_par_perimetre(champ_formulaire.queryset, user, champ=champ)


class FormulaireAvecUtilisateurMixin:
    """À placer en premier parmi les bases d'une CreateView/UpdateView : transmet l'utilisateur
    courant au formulaire (argument `user`), qui s'en sert pour limiter ses choix au périmètre."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

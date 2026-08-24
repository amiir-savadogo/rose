from . import permissions as perm


def permissions_front(request):
    """Expose les booléens de permission à tous les templates, sans avoir à
    les repasser manuellement dans le contexte de chaque vue."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {
        "peut_gerer_risques": perm.peut_gerer_risques(user),
        "peut_traiter_incidents": perm.peut_traiter_incidents(user),
        "peut_gerer_controles": perm.peut_gerer_controles(user),
        "peut_gerer_obligations": perm.peut_gerer_obligations(user),
        "peut_gerer_bibliotheque": perm.peut_gerer_bibliotheque(user),
        "peut_administrer": perm.peut_administrer(user),
        "peut_consulter_audit": perm.peut_consulter_audit(user),
    }

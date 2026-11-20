from . import permissions as perm


def permissions_front(request):
    """Expose les booléens de permission à tous les templates, sans avoir à
    les repasser manuellement dans le contexte de chaque vue."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    # Une seule requête pour toutes les permissions du rôle (et non une par permission).
    if perm.peut_administrer(user):
        accordees = None  # administrateur : tout est permis
    else:
        from .models import RolePermission
        accordees = set(
            RolePermission.objects.filter(role=user.role, autorise=True).values_list("permission", flat=True)
        )

    def autorise(cle):
        return accordees is None or cle in accordees

    return {
        "peut_gerer_risques": autorise("gerer_risques"),
        "peut_traiter_incidents": autorise("traiter_incidents"),
        "peut_gerer_controles": autorise("gerer_controles"),
        "peut_gerer_obligations": autorise("gerer_obligations"),
        "peut_gerer_bibliotheque": autorise("gerer_bibliotheque"),
        "peut_administrer": perm.peut_administrer(user),
        "peut_consulter_audit": autorise("consulter_audit"),
    }

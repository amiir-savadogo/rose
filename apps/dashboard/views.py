from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.controles.models import ControleExecution
from apps.incidents.models import Incident
from apps.obligations.models import ObligationOccurrence
from apps.risks.models import KeyRiskIndicator, Risk


def _donnees_synthese(user):
    from apps.accounts.perimetre import filtrer_par_perimetre

    risques_actifs = filtrer_par_perimetre(
        Risk.objects.filter(statut=Risk.Statut.ACTIF).select_related("categorie", "direction").prefetch_related("evaluations"),
        user, champ="direction",
    )

    profil = {"critique": 0, "eleve": 0, "modere": 0, "faible": 0}
    risques_evalues = 0
    hors_appetence = []
    for risque in risques_actifs:
        derniere = risque.derniere_evaluation
        if not derniere:
            continue
        risques_evalues += 1
        profil[derniere.niveau_residuel] += 1
        if derniere.niveau_residuel in ("eleve", "critique"):
            hors_appetence.append((risque, derniere))
    hors_appetence.sort(key=lambda t: t[1].score_residuel, reverse=True)

    incidents_qs = filtrer_par_perimetre(Incident.objects.all(), user, champ="direction")
    incidents_par_statut = dict(incidents_qs.values_list("statut").annotate(total=Count("id")).order_by())
    total_incidents_ouverts = sum(v for k, v in incidents_par_statut.items() if k != Incident.Statut.CLOTURE)

    executions_qs = filtrer_par_perimetre(
        ControleExecution.objects.select_related("controle", "controle__direction"), user, champ="controle__direction"
    )
    executions_en_retard = list(executions_qs.filter(
        resultat=ControleExecution.Resultat.NON_REALISE, date_prevue__lt=timezone.now().date()
    ))
    executions_sans_preuve = list(
        executions_qs.filter(
            resultat__in=[ControleExecution.Resultat.CONFORME, ControleExecution.Resultat.NON_CONFORME]
        ).filter(Q(preuve="") | Q(preuve__isnull=True))
    )

    heatmap = {}
    for risque, derniere in [(r, r.derniere_evaluation) for r in risques_actifs if r.derniere_evaluation]:
        cle = (derniere.probabilite_residuelle, derniere.impact_residuel)
        heatmap[cle] = heatmap.get(cle, 0) + 1

    def couleur(score):
        from apps.risks.models import classer_score
        niveau = classer_score(score)
        return {"critique": "#9b2c2c", "eleve": "#b85c2e", "modere": "#b9791e", "faible": "#0d7377"}[niveau]

    heatmap_matrix = []
    for p in [5, 4, 3, 2, 1]:
        ligne = [{"total": heatmap.get((p, i), 0), "couleur": couleur(p * i)} for i in [1, 2, 3, 4, 5]]
        heatmap_matrix.append({"probabilite": p, "cellules": ligne})

    return {
        "risques_evalues": risques_evalues,
        "hors_appetence": hors_appetence,
        "total_hors_appetence": len(hors_appetence),
        "total_incidents_ouverts": total_incidents_ouverts,
        "executions_en_retard": executions_en_retard,
        "total_controles_en_retard": len(executions_en_retard),
        "executions_sans_preuve": executions_sans_preuve,
        "profil": profil,
        "heatmap_matrix": heatmap_matrix,
        "niveaux": [1, 2, 3, 4, 5],
    }


@login_required
def accueil(request):
    return render(request, "dashboard/dashboard.html", _donnees_synthese(request.user))


@login_required
def perimetre_produit(request):
    return render(request, "dashboard/perimetre.html")


@login_required
def analyse_interactive(request):
    from apps.risks.models import Risk, RiskCategory, classer_score
    from apps.accounts.perimetre import filtrer_par_perimetre

    categorie_id = request.GET.get("categorie")
    direction_id = request.GET.get("direction")

    risques = filtrer_par_perimetre(
        Risk.objects.filter(statut=Risk.Statut.ACTIF).select_related("categorie", "direction").prefetch_related("evaluations"),
        request.user, champ="direction",
    )
    if categorie_id:
        risques = risques.filter(categorie_id=categorie_id)
    if direction_id:
        risques = risques.filter(direction_id=direction_id)

    profil = {"faible": 0, "modere": 0, "eleve": 0, "critique": 0}
    par_categorie = {}
    ecarts = []

    for risque in risques:
        derniere = risque.derniere_evaluation
        if not derniere:
            continue
        profil[derniere.niveau_residuel] += 1
        cat = risque.categorie.nom
        par_categorie.setdefault(cat, []).append(derniere.score_residuel)
        ecarts.append({
            "risque": risque.titre,
            "inherent": derniere.score_inherent,
            "residuel": derniere.score_residuel,
        })

    moyenne_par_categorie = [
        {"categorie": cat, "moyenne": round(sum(scores) / len(scores), 1)}
        for cat, scores in par_categorie.items()
    ]
    moyenne_par_categorie.sort(key=lambda x: x["moyenne"], reverse=True)

    ecarts.sort(key=lambda x: x["inherent"] - x["residuel"], reverse=True)
    top_ecarts = ecarts[:10]

    from apps.incidents.models import Incident
    incidents_qs = filtrer_par_perimetre(
        Incident.objects.exclude(categorie_evenement=""), request.user, champ="direction"
    )
    labels_evt = dict(Incident.CategorieEvenement.choices)
    par_evenement = list(incidents_qs.values("categorie_evenement").annotate(total=Count("id")).order_by("-total"))
    for l in par_evenement:
        l["label"] = labels_evt.get(l["categorie_evenement"], l["categorie_evenement"])

    from apps.accounts.models import Direction

    return render(request, "dashboard/analyse_interactive.html", {
        "categories": RiskCategory.objects.all(),
        "directions": Direction.objects.all(),
        "categorie_id": int(categorie_id) if categorie_id else None,
        "direction_id": int(direction_id) if direction_id else None,
        "profil_json": profil,
        "moyenne_par_categorie_json": moyenne_par_categorie,
        "top_ecarts_json": top_ecarts,
        "par_evenement_json": par_evenement,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def synthese_api(request):
    """Version API (JSON) de la même synthèse, pour une future interface découplée."""
    data = _donnees_synthese(request.user)
    data["profil"] = data["profil"]
    data["hors_appetence"] = [
        {"id": r.pk, "titre": r.titre, "residuel": e.score_residuel, "niveau": e.niveau_residuel}
        for r, e in data["hors_appetence"]
    ]
    data["executions_en_retard"] = [str(e) for e in data["executions_en_retard"]]
    data.pop("heatmap_matrix", None)
    return Response(data)

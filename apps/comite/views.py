from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import peut_gerer_risques
from apps.controles.models import ControleExecution
from apps.incidents.models import Incident
from apps.risks.models import Risk
from .forms import DecisionComiteForm, ExecuterDecisionForm, SeanceComiteForm
from .models import DecisionComite, SeanceComite


class SeanceListView(LoginRequiredMixin, ListView):
    model = SeanceComite
    template_name = "comite/seance_list.html"
    context_object_name = "seances"


class SeanceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = SeanceComite
    form_class = SeanceComiteForm
    template_name = "comite/seance_form.html"

    def test_func(self):
        return peut_gerer_risques(self.request.user)

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, "Séance créée.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("comite:seances")


@login_required
def dossier_seance(request, pk):
    """Le Comité des risques est volontairement transversal : il voit
    l'ensemble des directions, sans filtrage par périmètre. C'est un choix de
    conception délibéré, pas un oubli — un organe de gouvernance centrale doit
    pouvoir arbitrer entre directions, ce qui suppose de toutes les voir."""
    seance = get_object_or_404(SeanceComite, pk=pk)

    risques_hors_appetence = []
    for risque in Risk.objects.filter(statut=Risk.Statut.ACTIF).prefetch_related("evaluations"):
        derniere = risque.derniere_evaluation
        if derniere and derniere.niveau_residuel in ("eleve", "critique"):
            risques_hors_appetence.append((risque, derniere))
    risques_hors_appetence.sort(key=lambda t: t[1].score_residuel, reverse=True)

    incidents_periode = Incident.objects.filter(
        date_survenue__gte=seance.periode_debut, date_survenue__lte=seance.date_seance
    ).order_by("-date_survenue")

    controles_retard = ControleExecution.objects.select_related("controle").filter(
        resultat=ControleExecution.Resultat.NON_REALISE, date_prevue__lt=timezone.now().date()
    )

    # Décisions non exécutées de TOUTES les séances antérieures — c'est ce qui donne
    # sa mémoire au comité : il ne redécouvre pas à chaque fois qu'une décision dort.
    decisions_en_attente = DecisionComite.objects.filter(
        seance__date_seance__lt=seance.date_seance,
    ).exclude(statut=DecisionComite.Statut.EXECUTEE).select_related("seance", "responsable")

    return render(request, "comite/dossier.html", {
        "seance": seance,
        "risques_hors_appetence": risques_hors_appetence,
        "incidents_periode": incidents_periode,
        "controles_retard": controles_retard,
        "decisions_seance": seance.decisions.select_related("responsable").all(),
        "decisions_en_attente": decisions_en_attente,
        "peut_gerer": peut_gerer_risques(request.user),
    })


@login_required
def ajouter_decision(request, pk):
    seance = get_object_or_404(SeanceComite, pk=pk)
    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour ajouter une décision.")
        return redirect("comite:dossier", pk=pk)

    if request.method == "POST":
        form = DecisionComiteForm(request.POST)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.seance = seance
            decision.save()
            messages.success(request, "Décision ajoutée.")
            return redirect("comite:dossier", pk=pk)
    else:
        form = DecisionComiteForm()

    return render(request, "comite/decision_form.html", {"form": form, "seance": seance})


@login_required
def executer_decision(request, pk):
    decision = get_object_or_404(DecisionComite, pk=pk)
    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour clôturer cette décision.")
        return redirect("comite:dossier", pk=decision.seance_id)

    if request.method == "POST":
        form = ExecuterDecisionForm(request.POST)
        if form.is_valid():
            decision.date_execution = form.cleaned_data["date_execution"]
            decision.save()
            messages.success(request, "Décision marquée comme exécutée.")
            return redirect("comite:dossier", pk=decision.seance_id)
    else:
        form = ExecuterDecisionForm(initial={"date_execution": timezone.now().date()})

    return render(request, "comite/executer_decision_form.html", {"form": form, "decision": decision})

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import peut_gerer_risques
from apps.controles.models import ControleExecution
from apps.incidents.models import Incident
from apps.risks.models import Risk
from .forms import SeanceComiteForm
from .models import SeanceComite


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


def dossier_seance(request, pk):
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

    controles_retard = [e for e in ControleExecution.objects.select_related("controle") if e.en_retard]

    return render(request, "comite/dossier.html", {
        "seance": seance,
        "risques_hors_appetence": risques_hors_appetence,
        "incidents_periode": incidents_periode,
        "controles_retard": controles_retard,
    })

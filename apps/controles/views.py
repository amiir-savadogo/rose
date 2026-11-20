from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import peut_gerer_controles
from apps.accounts.perimetre import FormulaireAvecUtilisateurMixin, objet_ou_404_perimetre
from config.fichiers import reponse_telechargement
from .forms import ControleForm, ProgrammerExecutionForm, RenseignerExecutionForm
from .models import Controle, ControleExecution


class ControleListView(LoginRequiredMixin, ListView):
    model = Controle
    template_name = "controles/controle_list.html"
    context_object_name = "controles"

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        qs = Controle.objects.filter(actif=True).select_related("executant", "superviseur", "risque", "direction")
        return filtrer_par_perimetre(qs, self.request.user, champ="direction")


class ControleCreateView(FormulaireAvecUtilisateurMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Controle
    form_class = ControleForm
    template_name = "controles/controle_form.html"

    def test_func(self):
        return peut_gerer_controles(self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Contrôle créé.")
        return reverse("controles:liste")


class ExecutionListView(LoginRequiredMixin, ListView):
    model = ControleExecution
    template_name = "controles/execution_list.html"
    context_object_name = "executions"
    paginate_by = 30

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        qs = ControleExecution.objects.select_related("controle", "controle__direction").order_by("-date_prevue")
        return filtrer_par_perimetre(qs, self.request.user, champ="controle__direction")


@login_required
def programmer_execution(request, pk):
    controle = objet_ou_404_perimetre(Controle, request.user, pk, champ="direction")
    if not peut_gerer_controles(request.user):
        messages.error(request, "Vous n'avez pas les droits pour programmer un contrôle.")
        return redirect("controles:liste")

    if request.method == "POST":
        form = ProgrammerExecutionForm(request.POST)
        if form.is_valid():
            ControleExecution.objects.create(controle=controle, date_prevue=form.cleaned_data["date_prevue"])
            messages.success(request, "Exécution programmée.")
            return redirect("controles:liste")
    else:
        form = ProgrammerExecutionForm()

    return render(request, "controles/programmer_form.html", {"form": form, "controle": controle})


@login_required
def renseigner_execution(request, pk):
    execution = objet_ou_404_perimetre(ControleExecution, request.user, pk, champ="controle__direction")
    controle = execution.controle
    if not (
        peut_gerer_controles(request.user)
        or request.user.pk in (controle.executant_id, controle.superviseur_id)
    ):
        messages.error(request, "Seuls l'exécutant, le superviseur ou un gestionnaire des contrôles peuvent renseigner cette exécution.")
        return redirect("controles:executions")
    if request.method == "POST":
        form = RenseignerExecutionForm(request.POST, request.FILES, instance=execution)
        if form.is_valid():
            form.save()
            messages.success(request, "Exécution mise à jour.")
            return redirect("controles:executions")
    else:
        form = RenseignerExecutionForm(instance=execution)

    return render(request, "controles/renseigner_form.html", {"form": form, "execution": execution})


from django.views.generic import UpdateView


class ControleUpdateView(FormulaireAvecUtilisateurMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Controle
    form_class = ControleForm
    template_name = "controles/controle_form.html"
    success_url = "/controles/"

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        return filtrer_par_perimetre(Controle.objects.all(), self.request.user, champ="direction")

    def test_func(self):
        return peut_gerer_controles(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Contrôle mis à jour.")
        return super().form_valid(form)


@login_required
def telecharger_preuve(request, pk):
    """Téléchargement d'une preuve de contrôle : authentifié, limité au périmètre, en pièce jointe."""
    execution = objet_ou_404_perimetre(ControleExecution, request.user, pk, champ="controle__direction")
    return reponse_telechargement(execution.preuve)

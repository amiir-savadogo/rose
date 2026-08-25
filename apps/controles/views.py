from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import peut_gerer_controles
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


class ControleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
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
    controle = get_object_or_404(Controle, pk=pk)
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
    execution = get_object_or_404(ControleExecution, pk=pk)
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


class ControleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Controle
    form_class = ControleForm
    template_name = "controles/controle_form.html"
    success_url = "/controles/"

    def test_func(self):
        return peut_gerer_controles(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Contrôle mis à jour.")
        return super().form_valid(form)

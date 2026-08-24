from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import peut_gerer_echeance, peut_gerer_obligations
from .forms import ObligationForm
from .models import Obligation, ObligationOccurrence


class ObligationOccurrenceListView(LoginRequiredMixin, ListView):
    model = ObligationOccurrence
    template_name = "obligations/obligation_list.html"
    context_object_name = "echeances"
    paginate_by = 30

    def get_queryset(self):
        qs = ObligationOccurrence.objects.select_related("obligation", "obligation__responsable").order_by("date_echeance")
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["aujourdhui"] = timezone.now().date()
        return ctx


@login_required
def marquer_realisee(request, pk):
    occurrence = get_object_or_404(ObligationOccurrence, pk=pk)
    if not peut_gerer_echeance(request.user, occurrence):
        messages.error(request, "Vous n'avez pas les droits pour clore cette échéance.")
        return redirect("obligations:liste")
    occurrence.statut = ObligationOccurrence.Statut.REALISEE
    occurrence.date_realisation = timezone.now().date()
    occurrence.save()
    messages.success(request, f"Échéance « {occurrence.obligation} » marquée comme réalisée.")
    return redirect("obligations:liste")


class ObligationDefinitionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Obligation
    template_name = "obligations/obligation_definition_list.html"
    context_object_name = "obligations"

    def test_func(self):
        return peut_gerer_obligations(self.request.user)


class ObligationCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Obligation
    form_class = ObligationForm
    template_name = "obligations/obligation_definition_form.html"
    success_url = "/echeances/definitions/"

    def test_func(self):
        return peut_gerer_obligations(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Obligation créée. Les échéances seront générées par la commande generer_echeances.")
        return super().form_valid(form)

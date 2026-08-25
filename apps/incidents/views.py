from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from .forms import ChangerStatutForm, IncidentForm, PieceJointeForm
from .models import Incident, IncidentCommentaire
from apps.accounts.permissions import peut_traiter_incidents


class IncidentListView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = "incidents/incident_list.html"
    context_object_name = "incidents"
    paginate_by = 20

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        qs = Incident.objects.select_related("declare_par", "assigne_a").all()
        qs = filtrer_par_perimetre(qs, self.request.user, champ="direction")
        statut = self.request.GET.get("statut")
        gravite = self.request.GET.get("gravite")
        if statut:
            qs = qs.filter(statut=statut)
        if gravite:
            qs = qs.filter(gravite=gravite)
        return qs


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = Incident
    template_name = "incidents/incident_detail.html"
    context_object_name = "incident"

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        return filtrer_par_perimetre(Incident.objects.all(), self.request.user, champ="direction")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["commentaires"] = self.object.commentaires.select_related("auteur").all()
        ctx["pieces_jointes"] = self.object.pieces_jointes.all()
        ctx["form_statut"] = ChangerStatutForm(initial={"nouveau_statut": self.object.statut, "assigne_a": self.object.assigne_a})
        ctx["form_piece_jointe"] = PieceJointeForm()
        return ctx


class IncidentCreateView(LoginRequiredMixin, CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = "incidents/incident_form.html"

    def form_valid(self, form):
        form.instance.declare_par = self.request.user
        messages.success(self.request, "Incident déclaré avec succès.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("incidents:detail", kwargs={"pk": self.object.pk})


@login_required
def changer_statut(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if not peut_traiter_incidents(request.user):
        messages.error(request, "Vous n'avez pas les droits pour changer le statut de cet incident.")
        return redirect("incidents:detail", pk=pk)
    if request.method == "POST":
        form = ChangerStatutForm(request.POST)
        if form.is_valid():
            ancien_statut = incident.statut
            incident.statut = form.cleaned_data["nouveau_statut"]
            incident.assigne_a = form.cleaned_data["assigne_a"]
            incident.save()
            if form.cleaned_data["commentaire"] or ancien_statut != incident.statut:
                IncidentCommentaire.objects.create(
                    incident=incident,
                    auteur=request.user,
                    texte=form.cleaned_data["commentaire"] or "Changement de statut.",
                    ancien_statut=ancien_statut,
                    nouveau_statut=incident.statut,
                )
            messages.success(request, "Statut de l'incident mis à jour.")
    return redirect("incidents:detail", pk=pk)


@login_required
def ajouter_piece_jointe(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if request.method == "POST":
        form = PieceJointeForm(request.POST, request.FILES)
        if form.is_valid():
            piece = form.save(commit=False)
            piece.incident = incident
            piece.depose_par = request.user
            piece.save()
            messages.success(request, "Pièce jointe ajoutée.")
    return redirect("incidents:detail", pk=pk)


@login_required
def analyse(request):
    """Analyse agrégée des incidents : pertes cumulées, répartition par catégorie et processus."""
    qs = Incident.objects.all()

    par_categorie = list(
        qs.exclude(categorie_evenement="").values("categorie_evenement").annotate(total=Count("id")).order_by("-total")
    )
    par_processus = list(
        qs.exclude(processus_concerne="").values("processus_concerne").annotate(total=Count("id")).order_by("-total")
    )
    agregats = qs.aggregate(perte_brute=Sum("perte_brute"), recuperation=Sum("recuperation"))
    perte_brute = agregats["perte_brute"] or 0
    recuperation = agregats["recuperation"] or 0

    # Repère les risques sous-cotés : risques faibles/modérés qui accumulent des incidents
    from apps.risks.models import Risk
    risques_sous_cotes = []
    for risque in Risk.objects.filter(statut=Risk.Statut.ACTIF).prefetch_related("evaluations", "incidents"):
        derniere = risque.derniere_evaluation
        nb_incidents = risque.incidents.count()
        if derniere and derniere.niveau_residuel in ("faible", "modere") and nb_incidents >= 1:
            risques_sous_cotes.append({"risque": risque, "nb_incidents": nb_incidents})

    # Traduction lisible des catégories d'événement
    labels = dict(Incident.CategorieEvenement.choices)
    for ligne in par_categorie:
        ligne["label"] = labels.get(ligne["categorie_evenement"], ligne["categorie_evenement"])

    return render(request, "incidents/analyse.html", {
        "total_incidents": qs.count(),
        "par_categorie": par_categorie,
        "par_processus": par_processus,
        "perte_brute": perte_brute,
        "recuperation": recuperation,
        "perte_nette": perte_brute - recuperation,
        "risques_sous_cotes": risques_sous_cotes,
    })

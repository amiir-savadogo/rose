from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from .forms import ChangerStatutForm, IncidentForm, PieceJointeForm
from .models import Incident, IncidentCommentaire, IncidentPieceJointe
from apps.accounts.permissions import peut_traiter_incidents
from apps.accounts.perimetre import FormulaireAvecUtilisateurMixin, filtrer_par_perimetre, objet_ou_404_perimetre
from config.fichiers import reponse_telechargement


class IncidentListView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = "incidents/incident_list.html"
    context_object_name = "incidents"
    paginate_by = 20

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        qs = Incident.objects.select_related("declare_par", "assigne_a", "sous_categorie__categorie").all()
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


class IncidentCreateView(FormulaireAvecUtilisateurMixin, LoginRequiredMixin, CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = "incidents/incident_form.html"

    def get_context_data(self, **kwargs):
        from apps.risks.typologie import exemples_par_sous_categorie
        ctx = super().get_context_data(**kwargs)
        ctx["exemples_json"] = exemples_par_sous_categorie()
        return ctx

    def form_valid(self, form):
        form.instance.declare_par = self.request.user
        messages.success(self.request, "Incident déclaré avec succès.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("incidents:detail", kwargs={"pk": self.object.pk})


@login_required
def changer_statut(request, pk):
    incident = objet_ou_404_perimetre(Incident, request.user, pk, champ="direction")
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
    incident = objet_ou_404_perimetre(Incident, request.user, pk, champ="direction")
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
    qs = filtrer_par_perimetre(Incident.objects.all(), request.user, champ="direction")

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
    risques_visibles = filtrer_par_perimetre(
        Risk.objects.filter(statut=Risk.Statut.ACTIF).prefetch_related("evaluations"), request.user, champ="direction"
    ).annotate(nb_incidents=Count("incidents", distinct=True))
    for risque in risques_visibles:
        derniere = risque.derniere_evaluation
        nb_incidents = risque.nb_incidents
        if derniere and derniere.niveau_residuel in ("faible", "modere") and nb_incidents >= 1:
            risques_sous_cotes.append({"risque": risque, "nb_incidents": nb_incidents})

    par_sous_categorie = list(
        qs.exclude(sous_categorie=None)
        .values("sous_categorie__libelle", "sous_categorie__categorie__libelle")
        .annotate(total=Count("id"), perte=Sum("perte_brute"))
        .order_by("-total", "sous_categorie__libelle")
    )
    sans_sous_categorie = qs.filter(sous_categorie=None).count()

    # Traduction lisible des catégories d'événement
    labels = dict(Incident.CategorieEvenement.choices)
    for ligne in par_categorie:
        ligne["label"] = labels.get(ligne["categorie_evenement"], ligne["categorie_evenement"])

    return render(request, "incidents/analyse.html", {
        "total_incidents": qs.count(),
        "par_categorie": par_categorie,
        "par_processus": par_processus,
        "par_sous_categorie": par_sous_categorie,
        "sans_sous_categorie": sans_sous_categorie,
        "perte_brute": perte_brute,
        "recuperation": recuperation,
        "perte_nette": perte_brute - recuperation,
        "risques_sous_cotes": risques_sous_cotes,
    })


@login_required
def telecharger_piece_jointe(request, pk):
    """Téléchargement d'une pièce jointe : authentifié, limité au périmètre, toujours en pièce jointe."""
    piece = objet_ou_404_perimetre(IncidentPieceJointe, request.user, pk, champ="incident__direction")
    return reponse_telechargement(piece.fichier)

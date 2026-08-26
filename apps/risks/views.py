from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import peut_administrer, peut_gerer_risques
from apps.accounts.perimetre import objet_ou_404_perimetre
from .forms import ActionPlanForm, CampagneForm, ImportRisquesCSVForm, KeyRiskIndicatorForm, RiskCategoryForm, RiskEvaluationForm, RiskForm
from .models import Risk, RiskCategory


class RiskListView(LoginRequiredMixin, ListView):
    model = Risk
    template_name = "risks/risk_list.html"
    context_object_name = "risques"
    paginate_by = 20

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        qs = Risk.objects.select_related("categorie", "direction").prefetch_related("evaluations").all()
        qs = filtrer_par_perimetre(qs, self.request.user, champ="direction")
        statut = self.request.GET.get("statut")
        direction_id = self.request.GET.get("direction")
        categorie_id = self.request.GET.get("categorie")
        recherche = self.request.GET.get("q")
        if statut:
            qs = qs.filter(statut=statut)
        if direction_id:
            qs = qs.filter(direction_id=direction_id)
        if categorie_id:
            qs = qs.filter(categorie_id=categorie_id)
        if recherche:
            qs = qs.filter(titre__icontains=recherche)
        niveau = self.request.GET.get("niveau")
        if niveau:
            qs = [r for r in qs if r.derniere_evaluation and r.derniere_evaluation.niveau_residuel == niveau]
        return qs

    def get_context_data(self, **kwargs):
        from apps.accounts.models import Direction
        ctx = super().get_context_data(**kwargs)
        ctx["toutes_directions"] = Direction.objects.all()
        ctx["toutes_categories"] = RiskCategory.objects.all()
        return ctx


class RiskDetailView(LoginRequiredMixin, DetailView):
    model = Risk
    template_name = "risks/risk_detail.html"
    context_object_name = "risque"

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        return filtrer_par_perimetre(Risk.objects.all(), self.request.user, champ="direction")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["evaluations"] = self.object.evaluations.select_related("evalue_par").all()
        ctx["plans_action"] = self.object.plans_action.select_related("responsable").all()
        ctx["indicateurs"] = self.object.indicateurs.all()
        ctx["peut_gerer"] = peut_gerer_risques(self.request.user)
        return ctx


class RiskCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Risk
    form_class = RiskForm
    template_name = "risks/risk_form.html"

    def test_func(self):
        return peut_gerer_risques(self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Risque créé avec succès.")
        return reverse("risks:detail", kwargs={"pk": self.object.pk})


@login_required
def ajouter_evaluation(request, pk):
    risque = objet_ou_404_perimetre(Risk, request.user, pk, champ="direction")
    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour évaluer ce risque.")
        return redirect("risks:detail", pk=pk)

    if request.method == "POST":
        form = RiskEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.risque = risque
            evaluation.evalue_par = request.user
            evaluation.save()
            messages.success(request, "Nouvelle évaluation enregistrée.")
            return redirect("risks:detail", pk=pk)
    else:
        form = RiskEvaluationForm()

    return render(request, "risks/evaluation_form.html", {"form": form, "risque": risque})


@login_required
def ajouter_plan_action(request, pk):
    risque = objet_ou_404_perimetre(Risk, request.user, pk, champ="direction")
    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour ajouter un plan d'action.")
        return redirect("risks:detail", pk=pk)

    if request.method == "POST":
        form = ActionPlanForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.risque = risque
            action.save()
            messages.success(request, "Plan d'action ajouté.")
            return redirect("risks:detail", pk=pk)
    else:
        form = ActionPlanForm()

    return render(request, "risks/action_plan_form.html", {"form": form, "risque": risque})


@login_required
def vue_matricielle(request):
    """Cartographie croisée processus × entité : pour chaque croisement, le risque
    résiduel le plus élevé parmi les risques actifs correspondants."""
    risques = Risk.objects.filter(statut=Risk.Statut.ACTIF).select_related("direction").prefetch_related("evaluations")

    processus_set, directions_set = [], []
    grille = {}
    for risque in risques:
        derniere = risque.derniere_evaluation
        if not derniere or not risque.processus:
            continue
        direction_nom = risque.direction.nom if risque.direction else "Non affecté"
        if risque.processus not in processus_set:
            processus_set.append(risque.processus)
        if direction_nom not in directions_set:
            directions_set.append(direction_nom)
        cle = (risque.processus, direction_nom)
        score = derniere.score_residuel
        if cle not in grille or score > grille[cle]["score"]:
            grille[cle] = {"score": score, "niveau": derniere.niveau_residuel, "risque": risque}

    lignes = []
    for proc in processus_set:
        cellules = []
        for dirn in directions_set:
            cellules.append(grille.get((proc, dirn)))
        lignes.append({"processus": proc, "cellules": cellules})

    return render(request, "risks/vue_matricielle.html", {
        "directions": directions_set,
        "lignes": lignes,
    })


@login_required
def ajouter_kri(request, pk):
    risque = objet_ou_404_perimetre(Risk, request.user, pk, champ="direction")
    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour ajouter un indicateur.")
        return redirect("risks:detail", pk=pk)

    if request.method == "POST":
        form = KeyRiskIndicatorForm(request.POST)
        if form.is_valid():
            kri = form.save(commit=False)
            kri.risque = risque
            kri.save()
            messages.success(request, "Indicateur clé de risque ajouté.")
            return redirect("risks:detail", pk=pk)
    else:
        form = KeyRiskIndicatorForm()

    return render(request, "risks/kri_form.html", {"form": form, "risque": risque})


@login_required
def maj_kri(request, pk):
    from .models import KeyRiskIndicator
    kri = objet_ou_404_perimetre(KeyRiskIndicator, request.user, pk, champ="risque__direction")
    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour mettre à jour cet indicateur.")
        return redirect("risks:detail", pk=kri.risque_id)

    if request.method == "POST":
        form = KeyRiskIndicatorForm(request.POST, instance=kri)
        if form.is_valid():
            form.save()
            messages.success(request, "Indicateur mis à jour.")
    return redirect("risks:detail", pk=kri.risque_id)


class RiskCategoryListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = RiskCategory
    template_name = "risks/category_list.html"
    context_object_name = "categories"

    def test_func(self):
        return peut_gerer_risques(self.request.user)


class RiskCategoryCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = RiskCategory
    form_class = RiskCategoryForm
    template_name = "risks/category_form.html"
    success_url = "/risques/categories/"

    def test_func(self):
        return peut_gerer_risques(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Catégorie créée.")
        return super().form_valid(form)


class KeyRiskIndicatorListView(LoginRequiredMixin, ListView):
    """Liste transversale de tous les KRI, tous risques confondus."""
    from .models import KeyRiskIndicator
    model = KeyRiskIndicator
    template_name = "risks/kri_list.html"
    context_object_name = "indicateurs"

    def get_queryset(self):
        from .models import KeyRiskIndicator
        from apps.accounts.perimetre import filtrer_par_perimetre
        qs = KeyRiskIndicator.objects.select_related("risque").all()
        qs = filtrer_par_perimetre(qs, self.request.user, champ="risque__direction")
        etat = self.request.GET.get("etat")
        if etat:
            qs = [k for k in qs if k.etat == etat]
        return qs


class ActionPlanListView(LoginRequiredMixin, ListView):
    """Liste transversale de tous les plans d'action, tous risques confondus."""
    from .models import ActionPlan
    model = ActionPlan
    template_name = "risks/action_plan_list.html"
    context_object_name = "actions"

    def get_queryset(self):
        from .models import ActionPlan
        qs = ActionPlan.objects.select_related("risque", "responsable").order_by("echeance")
        statut = self.request.GET.get("statut")
        origine = self.request.GET.get("origine")
        if statut:
            qs = qs.filter(statut=statut)
        if origine:
            qs = qs.filter(origine=origine)
        return qs


class RiskUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Risk
    form_class = RiskForm
    template_name = "risks/risk_form.html"

    def get_queryset(self):
        from apps.accounts.perimetre import filtrer_par_perimetre
        return filtrer_par_perimetre(Risk.objects.all(), self.request.user, champ="direction")

    def test_func(self):
        return peut_gerer_risques(self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Risque mis à jour.")
        return reverse("risks:detail", kwargs={"pk": self.object.pk})


class ActionPlanUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    from .models import ActionPlan
    model = ActionPlan
    form_class = ActionPlanForm
    template_name = "risks/action_plan_edit_form.html"
    success_url = "/risques/plans-action/"

    def test_func(self):
        return peut_gerer_risques(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Plan d'action mis à jour.")
        return super().form_valid(form)


class CampagneListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    from .models import Campagne
    model = Campagne
    template_name = "risks/campagne_list.html"
    context_object_name = "campagnes"

    def test_func(self):
        return peut_administrer(self.request.user)


class CampagneCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    from .models import Campagne
    model = Campagne
    form_class = CampagneForm
    template_name = "risks/campagne_form.html"
    success_url = "/risques/campagnes/"

    def test_func(self):
        return peut_administrer(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Campagne ouverte.")
        return super().form_valid(form)


@login_required
def cloturer_campagne(request, pk):
    from .models import Campagne
    from django.utils import timezone
    campagne = get_object_or_404(Campagne, pk=pk)
    if not peut_administrer(request.user):
        messages.error(request, "Vous n'avez pas les droits pour clôturer une campagne.")
        return redirect("risks:campagnes")
    campagne.statut = Campagne.Statut.CLOTUREE
    campagne.date_cloture = timezone.now().date()
    campagne.save()
    messages.success(request, f"Campagne « {campagne.nom} » clôturée. Ses évaluations sont désormais figées.")
    return redirect("risks:campagnes")


COLONNES_IMPORT = ["titre", "categorie", "direction", "processus", "description"]
EN_TETES_IMPORT = ["Titre du risque", "Catégorie", "Direction / Entité", "Processus", "Description"]
TITRE_EXEMPLE_MODELE = "Défaut de contrepartie sur le portefeuille PME"


@login_required
def modele_import_risques(request):
    """Modèle Excel vierge (avec un exemple rempli) à télécharger avant l'import."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from django.http import HttpResponse

    wb = Workbook()
    ws = wb.active
    ws.title = "Risques à importer"

    ws.append(EN_TETES_IMPORT)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="15313D", end_color="15313D", fill_type="solid")

    ws.append([
        "Défaut de contrepartie sur le portefeuille PME", "Risque de crédit",
        "Direction des engagements", "Octroi et suivi du crédit",
        "Dégradation de la situation financière des emprunteurs (exemple — à remplacer ou supprimer)",
    ])

    largeurs = [45, 22, 28, 25, 55]
    for i, largeur in enumerate(largeurs, start=1):
        ws.column_dimensions[chr(64 + i)].width = largeur

    ws_aide = wb.create_sheet("Lisez-moi")
    ws_aide.append(["Comment remplir ce fichier"])
    ws_aide["A1"].font = Font(bold=True, size=13)
    lignes_aide = [
        "",
        "Une ligne = un risque. Ne modifiez pas les en-têtes de la première feuille.",
        "",
        "Titre du risque : obligatoire. Le nom du risque tel qu'il apparaîtra dans Rose.",
        "Catégorie : obligatoire. Si elle n'existe pas encore dans Rose, elle sera créée automatiquement.",
        "Direction / Entité : optionnel. Si elle n'existe pas encore dans Rose, elle sera créée automatiquement.",
        "Processus : optionnel. Le processus métier concerné (ex: Octroi et suivi du crédit).",
        "Description : optionnel.",
        "",
        "Une fois le fichier rempli, enregistrez-le et importez-le depuis Rose (Paramètres > Importer des risques).",
        "Cet import crée les risques ; les évaluations (inhérent/maîtrise/résiduel) se font ensuite une par une dans Rose.",
    ]
    for ligne in lignes_aide:
        ws_aide.append([ligne])
    ws_aide.column_dimensions["A"].width = 100

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="modele_import_risques_rose.xlsx"'
    wb.save(response)
    return response


@login_required
def exporter_risques_csv(request):
    """Export Excel de la cartographie actuelle — pour reprise dans Excel ou sauvegarde externe."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from django.http import HttpResponse

    wb = Workbook()
    ws = wb.active
    ws.title = "Risques"

    entetes = ["Code", "Titre", "Catégorie", "Direction", "Processus", "Statut", "Inhérent", "Maîtrise", "Résiduel", "Niveau", "Description"]
    ws.append(entetes)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="15313D", end_color="15313D", fill_type="solid")

    for risque in Risk.objects.select_related("categorie", "direction").prefetch_related("evaluations"):
        derniere = risque.derniere_evaluation
        ws.append([
            f"R-{risque.pk:03d}",
            risque.titre,
            risque.categorie.nom,
            risque.direction.nom if risque.direction else "",
            risque.processus,
            risque.get_statut_display(),
            derniere.score_inherent if derniere else None,
            derniere.qualite_dispositif_maitrise if derniere else None,
            derniere.score_residuel if derniere else None,
            derniere.niveau_residuel_display if derniere else "",
            risque.description,
        ])

    for i, largeur in enumerate([10, 40, 20, 25, 22, 12, 10, 10, 10, 12, 50], start=1):
        ws.column_dimensions[chr(64 + i)].width = largeur

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="risques_rose.xlsx"'
    wb.save(response)
    return response


@login_required
def importer_risques_csv(request):
    from openpyxl import load_workbook

    if not peut_gerer_risques(request.user):
        messages.error(request, "Vous n'avez pas les droits pour importer des risques.")
        return redirect("risks:liste")

    resume = None
    if request.method == "POST":
        form = ImportRisquesCSVForm(request.POST, request.FILES)
        if form.is_valid():
            fichier = form.cleaned_data["fichier"]
            try:
                wb = load_workbook(fichier, data_only=True)
            except Exception:
                messages.error(request, "Fichier illisible : vérifiez qu'il s'agit bien d'un fichier .xlsx (utilisez le modèle fourni).")
                return render(request, "risks/import_csv.html", {"form": form})

            ws = wb.worksheets[0]
            lignes = list(ws.iter_rows(values_only=True))
            if not lignes:
                messages.error(request, "Le fichier est vide.")
                return render(request, "risks/import_csv.html", {"form": form})

            # Repère les colonnes par leur en-tête (insensible à la casse/accents),
            # pour tolérer un ordre de colonnes différent du modèle.
            import unicodedata

            def normaliser(texte):
                texte = str(texte or "").strip().lower()
                return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")

            alias_colonnes = {
                "titre": "titre", "titre du risque": "titre",
                "categorie": "categorie", "categorie de risque": "categorie",
                "direction": "direction", "direction / entite": "direction", "entite": "direction",
                "processus": "processus",
                "description": "description",
            }
            entetes = [normaliser(c) for c in lignes[0]]
            index_colonnes = {}
            for i, entete in enumerate(entetes):
                if entete in alias_colonnes:
                    index_colonnes[alias_colonnes[entete]] = i

            if "titre" not in index_colonnes:
                messages.error(request, "Colonne « Titre du risque » introuvable — utilisez le modèle fourni sans modifier les en-têtes.")
                return render(request, "risks/import_csv.html", {"form": form})

            def valeur(ligne, cle):
                idx = index_colonnes.get(cle)
                if idx is None or idx >= len(ligne):
                    return ""
                return str(ligne[idx] or "").strip()

            crees, erreurs = 0, []
            for i, ligne in enumerate(lignes[1:], start=2):
                if ligne is None or not any(ligne):
                    continue
                titre = valeur(ligne, "titre")
                if titre == TITRE_EXEMPLE_MODELE:
                    continue  # ligne d'exemple du modèle, jamais importée même si l'utilisateur a oublié de la retirer
                if not titre or titre.lower().startswith("exemple"):
                    if not titre:
                        erreurs.append(f"Ligne {i} : titre manquant, ignorée.")
                    continue

                nom_categorie = valeur(ligne, "categorie") or "Non classé"
                categorie, _ = RiskCategory.objects.get_or_create(nom=nom_categorie)

                direction = None
                nom_direction = valeur(ligne, "direction")
                if nom_direction:
                    from apps.accounts.models import Direction
                    direction, _ = Direction.objects.get_or_create(nom=nom_direction)

                Risk.objects.create(
                    titre=titre,
                    categorie=categorie,
                    direction=direction,
                    processus=valeur(ligne, "processus"),
                    description=valeur(ligne, "description"),
                    proprietaire=request.user,
                )
                crees += 1

            resume = {"crees": crees, "erreurs": erreurs}
            if crees:
                messages.success(request, f"{crees} risque(s) importé(s).")
    else:
        form = ImportRisquesCSVForm()

    return render(request, "risks/import_csv.html", {"form": form, "resume": resume})

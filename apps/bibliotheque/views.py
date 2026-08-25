from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import peut_gerer_bibliotheque
from .forms import DocumentAttenduForm, DocumentForm, DocumentMetaForm, DocumentVersionForm
from .models import Document, DocumentAttendu, DocumentVersion


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "bibliotheque/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return Document.objects.select_related("responsable").prefetch_related("versions")


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = "bibliotheque/document_detail.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["versions"] = self.object.versions.select_related("deposee_par").all()
        ctx["peut_gerer"] = peut_gerer_bibliotheque(self.request.user)
        return ctx


class DocumentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "bibliotheque/document_form.html"

    def test_func(self):
        return peut_gerer_bibliotheque(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        DocumentVersion.objects.create(
            document=self.object,
            version=form.cleaned_data["version"],
            fichier=form.cleaned_data.get("fichier"),
            date_approbation=form.cleaned_data["date_approbation"],
            revue_prevue=form.cleaned_data["revue_prevue"],
            deposee_par=self.request.user,
        )
        messages.success(self.request, "Document créé.")
        return response

    def get_success_url(self):
        return reverse("bibliotheque:detail", kwargs={"pk": self.object.pk})


class DocumentMetaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modifier titre / nature / responsable — pas le contenu (voir Nouvelle version)."""
    model = Document
    form_class = DocumentMetaForm
    template_name = "bibliotheque/document_meta_form.html"

    def test_func(self):
        return peut_gerer_bibliotheque(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Informations du document mises à jour.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("bibliotheque:detail", kwargs={"pk": self.object.pk})


@login_required
def nouvelle_version(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not peut_gerer_bibliotheque(request.user):
        messages.error(request, "Vous n'avez pas les droits pour ajouter une nouvelle version.")
        return redirect("bibliotheque:detail", pk=pk)

    if request.method == "POST":
        form = DocumentVersionForm(request.POST, request.FILES)
        if form.is_valid():
            version = form.save(commit=False)
            version.document = document
            version.deposee_par = request.user
            version.save()
            messages.success(request, f"Version {version.version} ajoutée. L'ancienne version reste consultable dans l'historique.")
            return redirect("bibliotheque:detail", pk=pk)
    else:
        derniere = document.derniere_version
        initial = {}
        if derniere:
            # Propose la prochaine date de revue par défaut = 1 an après l'ancienne approbation,
            # simple aide à la saisie, librement modifiable.
            import datetime
            initial = {"revue_prevue": derniere.revue_prevue + datetime.timedelta(days=365)}
        form = DocumentVersionForm(initial=initial)

    return render(request, "bibliotheque/version_form.html", {"form": form, "document": document})


class CompletudeView(LoginRequiredMixin, ListView):
    """Confronte le corpus documentaire attendu aux documents réellement présents."""
    model = DocumentAttendu
    template_name = "bibliotheque/completude.html"
    context_object_name = "attendus"

    def get_queryset(self):
        return DocumentAttendu.objects.select_related("document").all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nb_manquants"] = sum(1 for a in ctx["attendus"] if a.etat == "manquant")
        ctx["nb_a_revoir"] = sum(1 for a in ctx["attendus"] if a.etat in ("en_retard", "proche"))
        ctx["peut_gerer"] = peut_gerer_bibliotheque(self.request.user)
        return ctx


class DocumentAttenduCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = DocumentAttendu
    form_class = DocumentAttenduForm
    template_name = "bibliotheque/document_attendu_form.html"
    success_url = "/bibliotheque/completude/"

    def test_func(self):
        return peut_gerer_bibliotheque(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Document attendu ajouté au corpus.")
        return super().form_valid(form)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView

from .forms import DirectionForm, ReinitialiserMotDePasseForm, UserCreateForm, UserUpdateForm
from .models import Direction, Permission as RolePermissionChoices, Role, RolePermission, User
from .permissions import peut_administrer


class DirectionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Direction
    template_name = "accounts/direction_list.html"
    context_object_name = "directions"

    def test_func(self):
        return peut_administrer(self.request.user)


class DirectionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Direction
    form_class = DirectionForm
    template_name = "accounts/direction_form.html"
    success_url = "/parametres/directions/"

    def test_func(self):
        return peut_administrer(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Direction créée.")
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "utilisateurs"

    def test_func(self):
        return peut_administrer(self.request.user)

    def get_queryset(self):
        return User.objects.select_related("direction").order_by("username")


class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    success_url = "/parametres/utilisateurs/"

    def test_func(self):
        return peut_administrer(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Utilisateur créé.")
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"
    success_url = "/parametres/utilisateurs/"

    def test_func(self):
        return peut_administrer(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Utilisateur mis à jour.")
        return super().form_valid(form)


@login_required
def reinitialiser_mot_de_passe(request, pk):
    cible = get_object_or_404(User, pk=pk)
    if not peut_administrer(request.user):
        messages.error(request, "Vous n'avez pas les droits pour réinitialiser ce mot de passe.")
        return redirect("accounts:utilisateurs")

    if request.method == "POST":
        form = ReinitialiserMotDePasseForm(request.POST)
        if form.is_valid():
            cible.set_password(form.cleaned_data["password1"])
            cible.save()
            messages.success(request, f"Mot de passe de {cible.username} réinitialisé.")
            return redirect("accounts:utilisateurs")
    else:
        form = ReinitialiserMotDePasseForm()

    return render(request, "accounts/reinitialiser_form.html", {"form": form, "cible": cible})


from django.contrib.auth import update_session_auth_hash
from .forms import ChangerMotDePasseForm, ProfilForm


@login_required
def mon_profil(request):
    if request.method == "POST":
        form = ProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("accounts:mon_profil")
    else:
        form = ProfilForm(instance=request.user)

    form_mdp = ChangerMotDePasseForm(request.user)
    return render(request, "accounts/mon_profil.html", {"form": form, "form_mdp": form_mdp})


@login_required
def changer_mon_mot_de_passe(request):
    if request.method == "POST":
        form = ChangerMotDePasseForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data["password1"])
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Mot de passe modifié.")
            return redirect("accounts:mon_profil")
    else:
        form = ChangerMotDePasseForm(request.user)

    profil_form = ProfilForm(instance=request.user)
    return render(request, "accounts/mon_profil.html", {"form": profil_form, "form_mdp": form})


class SessionsActivesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vue de supervision : dernières connexions/déconnexions par utilisateur."""
    template_name = "accounts/sessions_actives.html"
    context_object_name = "utilisateurs"

    def test_func(self):
        return peut_administrer(self.request.user)

    def get_queryset(self):
        from apps.audit.models import AuditLogEntry
        resultats = []
        for u in User.objects.all().order_by("username"):
            derniere_connexion = AuditLogEntry.objects.filter(
                utilisateur=u, modele="auth.Connexion"
            ).order_by("-horodatage").first()
            derniere_deconnexion = AuditLogEntry.objects.filter(
                utilisateur=u, modele="auth.Deconnexion"
            ).order_by("-horodatage").first()
            en_ligne = False
            if derniere_connexion and (not derniere_deconnexion or derniere_deconnexion.horodatage < derniere_connexion.horodatage):
                en_ligne = True
            resultats.append({
                "utilisateur": u,
                "derniere_connexion": derniere_connexion.horodatage if derniere_connexion else None,
                "derniere_deconnexion": derniere_deconnexion.horodatage if derniere_deconnexion else None,
                "en_ligne": en_ligne,
            })
        return resultats


ROLES_DELEGABLES = [
    (Role.RISK_MANAGER, "Risk Manager"),
    (Role.CONTROLEUR, "Contrôleur / Auditeur"),
    (Role.AGENT, "Agent opérationnel"),
    (Role.DIRECTION, "Direction"),
]


@login_required
def roles_permissions(request):
    """Matrice éditable des permissions par rôle.

    Administrateur n'apparaît pas dans la matrice : il a toujours tous les
    droits, pour éviter qu'un administrateur ne se retire lui-même l'accès
    par erreur (voir apps/accounts/permissions.py).
    """
    if not peut_administrer(request.user):
        messages.error(request, "Vous n'avez pas les droits pour gérer les permissions.")
        return redirect("dashboard:accueil")

    if request.method == "POST":
        for role, _ in ROLES_DELEGABLES:
            for cle, _ in RolePermissionChoices.choices:
                autorise = request.POST.get(f"{role}__{cle}") == "on"
                RolePermission.objects.update_or_create(
                    role=role, permission=cle, defaults={"autorise": autorise}
                )
        messages.success(request, "Permissions mises à jour.")
        return redirect("accounts:roles")

    existantes = {(rp.role, rp.permission): rp.autorise for rp in RolePermission.objects.all()}
    lignes = []
    for cle, libelle in RolePermissionChoices.choices:
        lignes.append({
            "cle": cle,
            "libelle": libelle,
            "roles": [
                {"role": role, "coche": existantes.get((role, cle), False)}
                for role, _ in ROLES_DELEGABLES
            ],
        })

    return render(request, "accounts/roles_permissions.html", {
        "lignes": lignes,
        "roles": ROLES_DELEGABLES,
    })

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView

from .forms import (
    ChangerMotDePasseForm, DirectionForm, ProfilForm, ReinitialiserMotDePasseForm, UserCreateForm, UserUpdateForm,
)
from .models import Direction, Permission as RolePermissionChoices, Role, RolePermission, User
from .permissions import peut_administrer


def connexion_bloquee(request, identifiant):
    """Vrai si trop de connexions échouées récentes pour cet identifiant ou cette adresse IP.

    S'appuie sur le journal d'audit (qui consigne déjà chaque échec) : pas de dépendance
    supplémentaire, et le compteur est partagé entre tous les processus du serveur.
    Pendant le blocage, les tentatives ne sont plus évaluées ni journalisées : la fenêtre
    n'est donc jamais prolongée par l'attaquant et le blocage expire de lui-même.
    """
    from apps.audit.models import AuditLogEntry
    from apps.audit.signals import adresse_ip

    depuis = timezone.now() - timedelta(minutes=settings.LOGIN_FENETRE_MINUTES)
    echecs = AuditLogEntry.objects.filter(modele="auth.ConnexionEchouee", horodatage__gte=depuis)
    identifiant = (identifiant or "").strip()[:150]
    if identifiant and echecs.filter(
        valeurs_apres__identifiant_saisi__iexact=identifiant
    ).count() >= settings.LOGIN_MAX_ECHECS_PAR_IDENTIFIANT:
        return True
    ip = adresse_ip(request)
    if ip and echecs.filter(valeurs_apres__adresse_ip=ip).count() >= settings.LOGIN_MAX_ECHECS_PAR_IP:
        return True
    return False


class ConnexionProtegeeView(LoginView):
    """Page de connexion avec verrou temporaire après trop d'échecs (anti brute-force)."""
    template_name = "registration/login.html"
    bloque = False

    def post(self, request, *args, **kwargs):
        if connexion_bloquee(request, request.POST.get("username", "")):
            self.bloque = True
            return self.form_invalid(self.get_form())
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bloque"] = self.bloque
        ctx["fenetre_minutes"] = settings.LOGIN_FENETRE_MINUTES
        return ctx


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
        form = ReinitialiserMotDePasseForm(request.POST, user=cible)
        if form.is_valid():
            cible.set_password(form.cleaned_data["password1"])
            cible.save()
            messages.success(request, f"Mot de passe de {cible.username} réinitialisé.")
            return redirect("accounts:utilisateurs")
    else:
        form = ReinitialiserMotDePasseForm(user=cible)

    return render(request, "accounts/reinitialiser_form.html", {"form": form, "cible": cible})


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
        utilisateurs = User.objects.annotate(
            derniere_connexion=Max("actions_journalisees__horodatage", filter=Q(actions_journalisees__modele="auth.Connexion")),
            derniere_deconnexion=Max("actions_journalisees__horodatage", filter=Q(actions_journalisees__modele="auth.Deconnexion")),
        ).order_by("username")
        resultats = []
        for u in utilisateurs:
            en_ligne = bool(u.derniere_connexion) and (
                not u.derniere_deconnexion or u.derniere_deconnexion < u.derniere_connexion
            )
            resultats.append({
                "utilisateur": u,
                "derniere_connexion": u.derniere_connexion,
                "derniere_deconnexion": u.derniere_deconnexion,
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

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("directions/", views.DirectionListView.as_view(), name="directions"),
    path("directions/nouvelle/", views.DirectionCreateView.as_view(), name="direction_creer"),
    path("utilisateurs/", views.UserListView.as_view(), name="utilisateurs"),
    path("utilisateurs/nouveau/", views.UserCreateView.as_view(), name="utilisateur_creer"),
    path("utilisateurs/<int:pk>/modifier/", views.UserUpdateView.as_view(), name="utilisateur_modifier"),
    path("utilisateurs/<int:pk>/mot-de-passe/", views.reinitialiser_mot_de_passe, name="reinitialiser_mot_de_passe"),
    path("mon-profil/", views.mon_profil, name="mon_profil"),
    path("mon-profil/mot-de-passe/", views.changer_mon_mot_de_passe, name="changer_mon_mot_de_passe"),
    path("sessions/", views.SessionsActivesView.as_view(), name="sessions"),
    path("roles/", views.roles_permissions, name="roles"),
]

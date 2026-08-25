from django.urls import path

from . import views

app_name = "comite"

urlpatterns = [
    path("", views.SeanceListView.as_view(), name="seances"),
    path("nouvelle/", views.SeanceCreateView.as_view(), name="creer"),
    path("<int:pk>/dossier/", views.dossier_seance, name="dossier"),
    path("<int:pk>/decision/", views.ajouter_decision, name="ajouter_decision"),
    path("decision/<int:pk>/executer/", views.executer_decision, name="executer_decision"),
]

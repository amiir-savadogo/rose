from django.urls import path

from . import views

app_name = "incidents"

urlpatterns = [
    path("", views.IncidentListView.as_view(), name="liste"),
    path("analyse/", views.analyse, name="analyse"),
    path("nouveau/", views.IncidentCreateView.as_view(), name="creer"),
    path("<int:pk>/", views.IncidentDetailView.as_view(), name="detail"),
    path("<int:pk>/statut/", views.changer_statut, name="changer_statut"),
    path("<int:pk>/piece-jointe/", views.ajouter_piece_jointe, name="ajouter_piece_jointe"),
    path("piece-jointe/<int:pk>/telecharger/", views.telecharger_piece_jointe, name="telecharger_piece_jointe"),
]

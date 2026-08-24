from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("analyse-interactive/", views.analyse_interactive, name="analyse_interactive"),
    path("api/synthese/", views.synthese_api, name="synthese_api"),
]

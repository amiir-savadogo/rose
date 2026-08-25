from django.urls import path

from . import views

app_name = "bibliotheque"

urlpatterns = [
    path("", views.DocumentListView.as_view(), name="liste"),
    path("nouveau/", views.DocumentCreateView.as_view(), name="creer"),
    path("<int:pk>/", views.DocumentDetailView.as_view(), name="detail"),
    path("<int:pk>/informations/", views.DocumentMetaUpdateView.as_view(), name="modifier"),
    path("<int:pk>/nouvelle-version/", views.nouvelle_version, name="nouvelle_version"),
    path("completude/", views.CompletudeView.as_view(), name="completude"),
    path("completude/nouveau/", views.DocumentAttenduCreateView.as_view(), name="completude_ajouter"),
]

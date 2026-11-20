from django.urls import path

from . import views

app_name = "controles"

urlpatterns = [
    path("", views.ControleListView.as_view(), name="liste"),
    path("nouveau/", views.ControleCreateView.as_view(), name="creer"),
    path("<int:pk>/modifier/", views.ControleUpdateView.as_view(), name="modifier"),
    path("executions/", views.ExecutionListView.as_view(), name="executions"),
    path("<int:pk>/programmer/", views.programmer_execution, name="programmer"),
    path("execution/<int:pk>/", views.renseigner_execution, name="renseigner"),
    path("execution/<int:pk>/preuve/", views.telecharger_preuve, name="telecharger_preuve"),
]

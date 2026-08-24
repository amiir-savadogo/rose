from django.urls import path

from . import views

app_name = "obligations"

urlpatterns = [
    path("", views.ObligationOccurrenceListView.as_view(), name="liste"),
    path("<int:pk>/realisee/", views.marquer_realisee, name="marquer_realisee"),
    path("definitions/", views.ObligationDefinitionListView.as_view(), name="definitions"),
    path("definitions/nouvelle/", views.ObligationCreateView.as_view(), name="creer"),
]

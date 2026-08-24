from django.urls import path

from . import views

app_name = "risks"

urlpatterns = [
    path("", views.RiskListView.as_view(), name="liste"),
    path("matrice/", views.vue_matricielle, name="matrice"),
    path("export.xlsx", views.exporter_risques_csv, name="export_xlsx"),
    path("import/", views.importer_risques_csv, name="import_csv"),
    path("import/modele.xlsx", views.modele_import_risques, name="import_modele"),
    path("nouveau/", views.RiskCreateView.as_view(), name="creer"),
    path("categories/", views.RiskCategoryListView.as_view(), name="categories"),
    path("categories/nouvelle/", views.RiskCategoryCreateView.as_view(), name="categorie_creer"),
    path("indicateurs/", views.KeyRiskIndicatorListView.as_view(), name="indicateurs"),
    path("plans-action/", views.ActionPlanListView.as_view(), name="plans_action"),
    path("campagnes/", views.CampagneListView.as_view(), name="campagnes"),
    path("campagnes/nouvelle/", views.CampagneCreateView.as_view(), name="campagne_creer"),
    path("campagnes/<int:pk>/cloturer/", views.cloturer_campagne, name="campagne_cloturer"),
    path("plans-action/<int:pk>/modifier/", views.ActionPlanUpdateView.as_view(), name="plan_action_modifier"),
    path("<int:pk>/", views.RiskDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.RiskUpdateView.as_view(), name="modifier"),
    path("<int:pk>/evaluer/", views.ajouter_evaluation, name="evaluer"),
    path("<int:pk>/plan-action/", views.ajouter_plan_action, name="plan_action"),
    path("<int:pk>/kri/", views.ajouter_kri, name="ajouter_kri"),
    path("kri/<int:pk>/maj/", views.maj_kri, name="maj_kri"),
]

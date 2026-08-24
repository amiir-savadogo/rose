from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("", include("apps.dashboard.urls", namespace="dashboard")),
    path("risques/", include("apps.risks.urls", namespace="risks")),
    path("incidents/", include("apps.incidents.urls", namespace="incidents")),
    path("echeances/", include("apps.obligations.urls", namespace="obligations")),
    path("controles/", include("apps.controles.urls", namespace="controles")),
    path("bibliotheque/", include("apps.bibliotheque.urls", namespace="bibliotheque")),
    path("comite/", include("apps.comite.urls", namespace="comite")),
    path("audit/", include("apps.audit.urls", namespace="audit")),
    path("parametres/", include("apps.accounts.urls", namespace="accounts")),
    path("api-auth/", include("rest_framework.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Rose — Administration"
admin.site.site_title = "Rose"
admin.site.index_title = "Gestion des risques opérationnels"

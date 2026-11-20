from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import include, path

from apps.accounts.views import ConnexionProtegeeView


def sante(request):
    """Sonde de santé (liveness) pour l'hébergeur : aucune donnée, aucune authentification."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", sante, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/login/", ConnexionProtegeeView.as_view(), name="login"),
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Rose — Administration"
admin.site.site_title = "Rose"
admin.site.index_title = "Gestion des risques opérationnels"

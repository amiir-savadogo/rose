from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.accounts.permissions import peut_consulter_audit
from .models import AuditLogEntry


class AuditLogListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AuditLogEntry
    template_name = "audit/audit_list.html"
    context_object_name = "entrees"
    paginate_by = 50

    def test_func(self):
        return peut_consulter_audit(self.request.user)

    def get_queryset(self):
        qs = AuditLogEntry.objects.select_related("utilisateur").order_by("-horodatage")[:300]
        action = self.request.GET.get("action")
        recherche = self.request.GET.get("q")
        if action:
            qs = [e for e in qs if e.action == action]
        if recherche:
            qs = [e for e in qs if recherche.lower() in (e.objet_repr or "").lower()
                  or recherche.lower() in (e.utilisateur.username if e.utilisateur else "système").lower()
                  or recherche.lower() in (e.modele or "").lower()]
        return qs

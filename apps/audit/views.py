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
        qs = AuditLogEntry.objects.select_related("utilisateur").order_by("-horodatage")
        action = self.request.GET.get("action")
        recherche = (self.request.GET.get("q") or "").strip()
        if action:
            qs = qs.filter(action=action)
        if recherche:
            filtre = (
                Q(objet_repr__icontains=recherche)
                | Q(utilisateur__username__icontains=recherche)
                | Q(modele__icontains=recherche)
            )
            if recherche.lower() in "système":  # actions sans utilisateur (système)
                filtre |= Q(utilisateur__isnull=True)
            qs = qs.filter(filtre)
        return qs

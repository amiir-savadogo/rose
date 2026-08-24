"""Connecte automatiquement les modèles métier au journal d'audit.

Chaque création / modification / suppression sur un modèle listé dans
AUDITED_MODELS déclenche l'écriture d'une entrée dans AuditLogEntry.
"""
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, pre_save, post_delete
from django.forms.models import model_to_dict

from .middleware import get_current_user
from .models import AuditLogEntry

# Cache des valeurs "avant" chargées juste avant sauvegarde
_avant_cache = {}


def _serialisable(data):
    import json
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder, default=str))


def capturer_avant(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = sender.objects.get(pk=instance.pk)
            _avant_cache[(sender, instance.pk)] = _serialisable(model_to_dict(ancien))
        except sender.DoesNotExist:
            _avant_cache[(sender, instance.pk)] = None


def journaliser_sauvegarde(sender, instance, created, **kwargs):
    avant = _avant_cache.pop((sender, instance.pk), None)
    apres = _serialisable(model_to_dict(instance))
    AuditLogEntry.objects.create(
        utilisateur=get_current_user() if getattr(get_current_user(), "is_authenticated", False) else None,
        action=AuditLogEntry.Action.CREATION if created else AuditLogEntry.Action.MODIFICATION,
        modele=f"{sender._meta.app_label}.{sender.__name__}",
        objet_id=str(instance.pk),
        objet_repr=str(instance)[:255],
        valeurs_avant=avant,
        valeurs_apres=apres,
    )


def journaliser_suppression(sender, instance, **kwargs):
    AuditLogEntry.objects.create(
        utilisateur=get_current_user() if getattr(get_current_user(), "is_authenticated", False) else None,
        action=AuditLogEntry.Action.SUPPRESSION,
        modele=f"{sender._meta.app_label}.{sender.__name__}",
        objet_id=str(instance.pk),
        objet_repr=str(instance)[:255],
        valeurs_avant=_serialisable(model_to_dict(instance)),
        valeurs_apres=None,
    )


def connecter_modeles_audites():
    from apps.risks.models import Risk, RiskEvaluation, ActionPlan
    from apps.incidents.models import Incident
    from apps.obligations.models import Obligation, ObligationOccurrence
    from apps.controles.models import Controle, ControleExecution
    from apps.bibliotheque.models import Document, DocumentVersion

    modeles_audites = [
        Risk, RiskEvaluation, ActionPlan, Incident, Obligation, ObligationOccurrence,
        Controle, ControleExecution, Document, DocumentVersion,
    ]
    for modele in modeles_audites:
        pre_save.connect(capturer_avant, sender=modele, weak=False)
        post_save.connect(journaliser_sauvegarde, sender=modele, weak=False)
        post_delete.connect(journaliser_suppression, sender=modele, weak=False)


def _adresse_ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def journaliser_connexion_reussie(sender, request, user, **kwargs):
    AuditLogEntry.objects.create(
        utilisateur=user,
        action=AuditLogEntry.Action.CREATION,
        modele="auth.Connexion",
        objet_id="-",
        objet_repr=f"Connexion réussie ({user.username})",
        valeurs_avant=None,
        valeurs_apres={"adresse_ip": _adresse_ip(request)},
    )


def journaliser_connexion_echouee(sender, credentials, request=None, **kwargs):
    identifiant = credentials.get("username", "?")
    AuditLogEntry.objects.create(
        utilisateur=None,
        action=AuditLogEntry.Action.CREATION,
        modele="auth.ConnexionEchouee",
        objet_id="-",
        objet_repr=f"Échec de connexion ({identifiant})",
        valeurs_avant=None,
        valeurs_apres={"identifiant_saisi": identifiant, "adresse_ip": _adresse_ip(request)},
    )


def journaliser_deconnexion(sender, request, user, **kwargs):
    if user is None or not getattr(user, "pk", None):
        return
    AuditLogEntry.objects.create(
        utilisateur=user,
        action=AuditLogEntry.Action.CREATION,
        modele="auth.Deconnexion",
        objet_id="-",
        objet_repr=f"Déconnexion ({user.username})",
        valeurs_avant=None,
        valeurs_apres={"adresse_ip": _adresse_ip(request)},
    )


def connecter_journal_connexions():
    from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
    user_logged_in.connect(journaliser_connexion_reussie, weak=False)
    user_logged_out.connect(journaliser_deconnexion, weak=False)
    user_login_failed.connect(journaliser_connexion_echouee, weak=False)

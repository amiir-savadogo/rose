"""Connecte automatiquement les modèles métier au journal d'audit.

Chaque création / modification / suppression sur un modèle listé dans
AUDITED_MODELS déclenche l'écriture d'une entrée dans AuditLogEntry.
"""
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, pre_save, post_delete
from django.forms.models import model_to_dict

from .middleware import get_current_user
from .models import AuditLogEntry


def _serialisable(data):
    import json
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder, default=str))


def capturer_avant(sender, instance, **kwargs):
    """Mémorise l'état « avant » sur l'instance elle-même (pas dans un cache global partagé
    entre requêtes : pas de fuite mémoire si la sauvegarde échoue, pas de collision)."""
    instance._audit_avant = None
    if instance.pk:
        try:
            ancien = sender.objects.get(pk=instance.pk)
            instance._audit_avant = _serialisable(model_to_dict(ancien))
        except sender.DoesNotExist:
            pass


def journaliser_sauvegarde(sender, instance, created, **kwargs):
    avant = getattr(instance, "_audit_avant", None)
    instance._audit_avant = None
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
    from apps.risks.models import Risk, RiskEvaluation, ActionPlan, CategorieEvenement, SousCategorieEvenement
    from apps.incidents.models import Incident
    from apps.obligations.models import Obligation, ObligationOccurrence
    from apps.controles.models import Controle, ControleExecution
    from apps.bibliotheque.models import Document, DocumentVersion

    modeles_audites = [
        Risk, RiskEvaluation, ActionPlan, Incident, Obligation, ObligationOccurrence,
        Controle, ControleExecution, Document, DocumentVersion,
        CategorieEvenement, SousCategorieEvenement,
    ]
    for modele in modeles_audites:
        pre_save.connect(capturer_avant, sender=modele, weak=False)
        post_save.connect(journaliser_sauvegarde, sender=modele, weak=False)
        post_delete.connect(journaliser_suppression, sender=modele, weak=False)


def adresse_ip(request):
    """Adresse IP du client, résistante à la falsification de X-Forwarded-For.

    Derrière N proxys de confiance (TRUSTED_PROXY_COUNT), seule la N-ième valeur en partant de
    la droite a été ajoutée par un proxy de confiance ; tout ce qui est à sa gauche vient du
    client et ne doit jamais être cru. Hors proxy, on utilise REMOTE_ADDR.
    """
    if not request:
        return None
    if getattr(settings, "BEHIND_PROXY", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        elements = [e.strip() for e in xff.split(",") if e.strip()]
        if elements:
            n = max(1, getattr(settings, "TRUSTED_PROXY_COUNT", 1))
            return elements[-n] if len(elements) >= n else elements[0]
    return request.META.get("REMOTE_ADDR")


_adresse_ip = adresse_ip  # alias de compatibilité


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
    # Tronqué : un utilisateur peut, par erreur, saisir son mot de passe dans le champ identifiant.
    identifiant = str(credentials.get("username", "?"))[:150]
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

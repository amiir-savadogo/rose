from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Journal d'audit"

    def ready(self):
        from .signals import connecter_modeles_audites, connecter_journal_connexions
        connecter_modeles_audites()
        connecter_journal_connexions()

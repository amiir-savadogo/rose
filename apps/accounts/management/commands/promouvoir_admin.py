"""Corrige le rôle métier d'un compte existant en 'Administrateur'.

Utile pour un compte créé via `createsuperuser` avant que cette commande
ne positionne automatiquement role=admin (ou pour promouvoir n'importe
quel autre compte).

Usage : python manage.py promouvoir_admin <username>
"""
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role, User


class Command(BaseCommand):
    help = "Positionne le rôle 'Administrateur' sur le compte utilisateur indiqué."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"Aucun utilisateur nommé « {options['username']} ».")

        user.role = Role.ADMIN
        user.save(update_fields=["role"])
        self.stdout.write(self.style.SUCCESS(f"« {user.username} » est maintenant Administrateur."))

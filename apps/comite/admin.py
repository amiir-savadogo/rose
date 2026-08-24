from django.contrib import admin

from .models import SeanceComite


@admin.register(SeanceComite)
class SeanceComiteAdmin(admin.ModelAdmin):
    list_display = ("libelle", "date_seance", "direction", "statut")
    list_filter = ("statut",)

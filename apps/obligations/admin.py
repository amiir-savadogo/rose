from django.contrib import admin

from .models import Obligation, ObligationOccurrence


class ObligationOccurrenceInline(admin.TabularInline):
    model = ObligationOccurrence
    extra = 0


@admin.register(Obligation)
class ObligationAdmin(admin.ModelAdmin):
    list_display = ("nom", "periodicite", "responsable", "active")
    list_filter = ("periodicite", "active")
    inlines = [ObligationOccurrenceInline]


@admin.register(ObligationOccurrence)
class ObligationOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("obligation", "date_echeance", "statut", "date_realisation")
    list_filter = ("statut",)

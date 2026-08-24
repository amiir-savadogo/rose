from django.contrib import admin

from .models import Incident, IncidentCommentaire, IncidentPieceJointe


class IncidentCommentaireInline(admin.TabularInline):
    model = IncidentCommentaire
    extra = 0


class IncidentPieceJointeInline(admin.TabularInline):
    model = IncidentPieceJointe
    extra = 0


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("titre", "gravite", "statut", "date_survenue", "declare_par", "assigne_a")
    list_filter = ("statut", "gravite")
    search_fields = ("titre", "description")
    filter_horizontal = ("risques_lies",)
    inlines = [IncidentCommentaireInline, IncidentPieceJointeInline]

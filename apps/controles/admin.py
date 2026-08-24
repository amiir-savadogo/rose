from django.contrib import admin

from .models import Controle, ControleExecution


class ControleExecutionInline(admin.TabularInline):
    model = ControleExecution
    extra = 0


@admin.register(Controle)
class ControleAdmin(admin.ModelAdmin):
    list_display = ("nom", "niveau", "frequence", "executant", "superviseur", "actif")
    list_filter = ("niveau", "frequence", "actif")
    inlines = [ControleExecutionInline]


@admin.register(ControleExecution)
class ControleExecutionAdmin(admin.ModelAdmin):
    list_display = ("controle", "date_prevue", "date_realisee", "resultat")
    list_filter = ("resultat",)

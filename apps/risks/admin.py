from django.contrib import admin

from .models import ActionPlan, KeyRiskIndicator, Risk, RiskCategory, RiskEvaluation


class RiskEvaluationInline(admin.TabularInline):
    model = RiskEvaluation
    extra = 0
    readonly_fields = [f.name for f in RiskEvaluation._meta.fields]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ActionPlanInline(admin.TabularInline):
    model = ActionPlan
    extra = 0


class KeyRiskIndicatorInline(admin.TabularInline):
    model = KeyRiskIndicator
    extra = 0


@admin.register(RiskCategory)
class RiskCategoryAdmin(admin.ModelAdmin):
    list_display = ("nom",)


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "direction", "statut", "proprietaire", "modifie_le")
    list_filter = ("statut", "categorie", "direction")
    search_fields = ("titre", "description")
    inlines = [RiskEvaluationInline, ActionPlanInline, KeyRiskIndicatorInline]


@admin.register(RiskEvaluation)
class RiskEvaluationAdmin(admin.ModelAdmin):
    list_display = ("risque", "score_inherent", "score_residuel", "evalue_par", "date_evaluation")
    readonly_fields = [f.name for f in RiskEvaluation._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

from django import forms

from .models import ActionPlan, Campagne, KeyRiskIndicator, Risk, RiskCategory, RiskEvaluation


class RiskForm(forms.ModelForm):
    class Meta:
        model = Risk
        fields = ["titre", "description", "categorie", "direction", "processus", "statut", "proprietaire"]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categorie": forms.Select(attrs={"class": "form-select"}),
            "direction": forms.Select(attrs={"class": "form-select"}),
            "processus": forms.TextInput(attrs={"class": "form-control"}),
            "statut": forms.Select(attrs={"class": "form-select"}),
            "proprietaire": forms.Select(attrs={"class": "form-select"}),
        }


class RiskEvaluationForm(forms.ModelForm):
    class Meta:
        model = RiskEvaluation
        fields = [
            "probabilite_inherente", "impact_inherent", "qualite_dispositif_maitrise",
            "probabilite_residuelle", "impact_residuel", "justification",
        ]
        widgets = {
            "probabilite_inherente": forms.Select(attrs={"class": "form-select"}),
            "impact_inherent": forms.Select(attrs={"class": "form-select"}),
            "qualite_dispositif_maitrise": forms.Select(attrs={"class": "form-select"}),
            "probabilite_residuelle": forms.Select(attrs={"class": "form-select"}),
            "impact_residuel": forms.Select(attrs={"class": "form-select"}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ActionPlanForm(forms.ModelForm):
    class Meta:
        model = ActionPlan
        fields = ["risque", "origine", "description", "responsable", "echeance", "avancement"]
        widgets = {
            "risque": forms.Select(attrs={"class": "form-select"}),
            "origine": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
            "echeance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "avancement": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
        }


class KeyRiskIndicatorForm(forms.ModelForm):
    class Meta:
        model = KeyRiskIndicator
        fields = ["nom", "unite", "sens", "seuil_alerte", "seuil_limite", "valeur_actuelle"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "unite": forms.TextInput(attrs={"class": "form-control"}),
            "sens": forms.Select(attrs={"class": "form-select"}),
            "seuil_alerte": forms.NumberInput(attrs={"class": "form-control"}),
            "seuil_limite": forms.NumberInput(attrs={"class": "form-control"}),
            "valeur_actuelle": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        sens = cleaned_data.get("sens")
        alerte = cleaned_data.get("seuil_alerte")
        limite = cleaned_data.get("seuil_limite")
        if sens and alerte is not None and limite is not None:
            if sens == KeyRiskIndicator.Sens.HAUSSE and limite < alerte:
                raise forms.ValidationError(
                    "Sens « croît avec la valeur » : le seuil limite doit être supérieur ou égal au seuil d'alerte "
                    "(la limite est le franchissement le plus grave, elle vient après l'alerte)."
                )
            if sens == KeyRiskIndicator.Sens.BAISSE and limite > alerte:
                raise forms.ValidationError(
                    "Sens « décroît avec la valeur » : le seuil limite doit être inférieur ou égal au seuil d'alerte "
                    "(la limite est le franchissement le plus grave, elle vient après l'alerte)."
                )
        return cleaned_data


class RiskCategoryForm(forms.ModelForm):
    class Meta:
        model = RiskCategory
        fields = ["nom", "description"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class CampagneForm(forms.ModelForm):
    class Meta:
        model = Campagne
        fields = ["nom", "date_ouverture", "seuil_appetence"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "date_ouverture": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "seuil_appetence": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ImportRisquesCSVForm(forms.Form):
    fichier = forms.FileField(
        label="Fichier Excel (.xlsx)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".xlsx"}),
        help_text="Utilisez le modèle téléchargeable ci-dessus pour être sûr des colonnes attendues.",
    )

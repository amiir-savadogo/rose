from django import forms

from .models import Controle, ControleExecution


class ControleForm(forms.ModelForm):
    class Meta:
        model = Controle
        fields = ["nom", "description", "risque", "direction", "niveau", "frequence", "executant", "superviseur", "actif"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "risque": forms.Select(attrs={"class": "form-select"}),
            "direction": forms.Select(attrs={"class": "form-select"}),
            "niveau": forms.Select(attrs={"class": "form-select"}),
            "frequence": forms.Select(attrs={"class": "form-select"}),
            "executant": forms.Select(attrs={"class": "form-select"}),
            "superviseur": forms.Select(attrs={"class": "form-select"}),
        }


class ProgrammerExecutionForm(forms.Form):
    date_prevue = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}), label="Date prévue")


class RenseignerExecutionForm(forms.ModelForm):
    class Meta:
        model = ControleExecution
        fields = ["date_realisee", "resultat", "preuve", "commentaire"]
        widgets = {
            "date_realisee": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "resultat": forms.Select(attrs={"class": "form-select"}),
            "preuve": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "commentaire": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

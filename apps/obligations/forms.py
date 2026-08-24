from django import forms

from .models import Obligation


class ObligationForm(forms.ModelForm):
    class Meta:
        model = Obligation
        fields = ["nom", "description", "texte_reference", "periodicite", "responsable", "active"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "texte_reference": forms.TextInput(attrs={"class": "form-control"}),
            "periodicite": forms.Select(attrs={"class": "form-select"}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

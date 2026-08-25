from django import forms

from .models import DecisionComite, SeanceComite


class SeanceComiteForm(forms.ModelForm):
    class Meta:
        model = SeanceComite
        fields = ["libelle", "date_seance", "direction", "participants", "ordre_du_jour", "statut"]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "date_seance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "direction": forms.Select(attrs={"class": "form-select"}),
            "participants": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Un participant par ligne"}),
            "ordre_du_jour": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "statut": forms.Select(attrs={"class": "form-select"}),
        }


class DecisionComiteForm(forms.ModelForm):
    class Meta:
        model = DecisionComite
        fields = ["libelle", "responsable", "echeance"]
        widgets = {
            "libelle": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
            "echeance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class ExecuterDecisionForm(forms.Form):
    date_execution = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}), label="Exécutée le")

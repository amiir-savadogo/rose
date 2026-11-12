from django import forms

from apps.risks.typologie import choix_groupes
from .models import Incident, IncidentCommentaire, IncidentPieceJointe


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = [
            "titre", "description", "sous_categorie", "date_survenue", "date_detection",
            "direction", "processus_concerne", "perte_brute", "recuperation", "gravite", "risques_lies",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "sous_categorie": forms.Select(attrs={"class": "form-select"}),
            "date_survenue": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_detection": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "direction": forms.Select(attrs={"class": "form-select"}),
            "processus_concerne": forms.TextInput(attrs={"class": "form-control"}),
            "perte_brute": forms.NumberInput(attrs={"class": "form-control"}),
            "recuperation": forms.NumberInput(attrs={"class": "form-control"}),
            "gravite": forms.Select(attrs={"class": "form-select"}),
            "risques_lies": forms.SelectMultiple(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sous_categorie"].choices = choix_groupes()
        self.fields["sous_categorie"].label = "Type d'événement (Bâle)"


class ChangerStatutForm(forms.Form):
    nouveau_statut = forms.ChoiceField(
        choices=Incident.Statut.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Nouveau statut",
    )
    commentaire = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Commentaire",
        required=False,
    )
    assigne_a = forms.ModelChoiceField(
        queryset=None, required=False, widget=forms.Select(attrs={"class": "form-select"}),
        label="Assigner à",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields["assigne_a"].queryset = User.objects.filter(is_active=True)


class PieceJointeForm(forms.ModelForm):
    class Meta:
        model = IncidentPieceJointe
        fields = ["fichier"]
        widgets = {"fichier": forms.ClearableFileInput(attrs={"class": "form-control"})}

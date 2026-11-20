from django import forms

from config.fichiers import securiser_champ_fichier
from .models import Document, DocumentAttendu, DocumentVersion


class DocumentForm(forms.ModelForm):
    """Création d'un document — sa première version est saisie dans la foulée."""
    version = forms.CharField(label="Version initiale", initial="1.0", widget=forms.TextInput(attrs={"class": "form-control"}))
    fichier = forms.FileField(label="Fichier", required=False, widget=forms.ClearableFileInput(attrs={"class": "form-control"}))
    date_approbation = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    revue_prevue = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))

    class Meta:
        model = Document
        fields = ["titre", "nature", "responsable"]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "nature": forms.Select(attrs={"class": "form-select"}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        securiser_champ_fichier(self, "fichier")


class DocumentMetaForm(forms.ModelForm):
    """Modifier les informations générales du document (pas son contenu)."""
    class Meta:
        model = Document
        fields = ["titre", "nature", "responsable"]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "nature": forms.Select(attrs={"class": "form-select"}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
        }


class DocumentVersionForm(forms.ModelForm):
    class Meta:
        model = DocumentVersion
        fields = ["version", "fichier", "date_approbation", "revue_prevue", "note_revision"]
        widgets = {
            "version": forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: 2.0"}),
            "fichier": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "date_approbation": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "revue_prevue": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "note_revision": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Qu'est-ce qui a changé ?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        securiser_champ_fichier(self, "fichier")


class DocumentAttenduForm(forms.ModelForm):
    class Meta:
        model = DocumentAttendu
        fields = ["titre", "nature", "document"]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "nature": forms.Select(attrs={"class": "form-select"}),
            "document": forms.Select(attrs={"class": "form-select"}),
        }

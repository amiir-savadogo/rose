"""Téléversement et téléchargement sécurisés des fichiers (preuves, pièces jointes, documents).

Principes :
- à l'entrée : liste blanche d'extensions et taille maximale (réglages UPLOAD_*) ;
- à la sortie : les fichiers ne sont jamais exposés par une URL publique, ils sont servis
  par des vues authentifiées, toujours en pièce jointe (jamais interprétés par le
  navigateur), ce qui neutralise le dépôt d'un HTML/SVG/JS piégé.
"""
import os

from django import forms
from django.conf import settings
from django.http import FileResponse, Http404


def valider_fichier_televerse(fichier):
    """Validateur de champ de formulaire : extension autorisée et taille raisonnable."""
    extension = os.path.splitext(fichier.name or "")[1].lower()
    if extension not in settings.UPLOAD_EXTENSIONS_AUTORISEES:
        autorisees = ", ".join(sorted(settings.UPLOAD_EXTENSIONS_AUTORISEES))
        raise forms.ValidationError(
            f"Type de fichier non autorisé ({extension or 'sans extension'}). Formats acceptés : {autorisees}."
        )
    taille = getattr(fichier, "size", 0) or 0
    if taille > settings.UPLOAD_MAX_BYTES:
        mo = settings.UPLOAD_MAX_BYTES // (1024 * 1024)
        raise forms.ValidationError(f"Fichier trop volumineux (maximum {mo} Mo).")


def securiser_champ_fichier(form, nom_champ):
    """Ajoute le validateur de fichier à un champ déjà déclaré du formulaire."""
    champ = form.fields.get(nom_champ)
    if champ is not None and valider_fichier_televerse not in champ.validators:
        champ.validators.append(valider_fichier_televerse)


def reponse_telechargement(champ_fichier):
    """Réponse de téléchargement d'un FileField, en pièce jointe. 404 si le fichier est absent."""
    if not champ_fichier:
        raise Http404("Aucun fichier.")
    try:
        flux = champ_fichier.open("rb")
    except (FileNotFoundError, ValueError, OSError):
        raise Http404("Fichier introuvable.")
    reponse = FileResponse(flux, as_attachment=True, filename=os.path.basename(champ_fichier.name))
    reponse["X-Content-Type-Options"] = "nosniff"
    reponse["Cache-Control"] = "private, no-store"
    return reponse

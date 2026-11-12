"""Aides d'affichage et de rapprochement autour de la typologie des événements."""
import unicodedata

from .models import CategorieEvenement, SousCategorieEvenement


def normaliser(texte):
    """Minuscules sans accents ni espaces superflus, pour comparer des libellés saisis à la main."""
    texte = " ".join(str(texte or "").split()).lower()
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def choix_groupes():
    """Choix d'un <select> regroupé par catégorie : [("", "—"), (catégorie, [(id, sous-catégorie), ...])]."""
    groupes = [("", "---------")]
    for cat in CategorieEvenement.objects.prefetch_related("sous_categories"):
        groupes.append((cat.libelle, [(s.pk, s.libelle) for s in cat.sous_categories.all()]))
    return groupes


def exemples_par_sous_categorie():
    """{id de sous-catégorie: [exemples]} — sert à l'aide contextuelle des formulaires."""
    return {s.pk: s.liste_exemples for s in SousCategorieEvenement.objects.all()}


def trouver_sous_categorie(texte):
    """Retrouve une sous-catégorie à partir d'un texte (import Excel).

    Accepte « Catégorie > Sous-catégorie » (ou « › », « / ») ou le seul libellé de la
    sous-catégorie quand il est unique. « Vol et fraude » existe en fraude interne ET
    externe : seul sur la ligne, il est ambigu. Retourne (sous_categorie | None, message_erreur | "").
    """
    brut = str(texte or "").strip()
    if not brut:
        return None, ""
    candidats = list(SousCategorieEvenement.objects.select_related("categorie"))
    for separateur in (">", "›", "/"):
        if separateur in brut:
            cat_txt, _, sous_txt = brut.partition(separateur)
            cat_n, sous_n = normaliser(cat_txt), normaliser(sous_txt)
            trouves = [
                s for s in candidats
                if normaliser(s.libelle) == sous_n and (
                    normaliser(s.categorie.libelle) == cat_n or normaliser(s.categorie.code) == cat_n
                    or cat_n in normaliser(s.categorie.libelle)
                )
            ]
            if len(trouves) == 1:
                return trouves[0], ""
            return None, f"type d'événement « {brut} » non reconnu"
    cible = normaliser(brut)
    trouves = [s for s in candidats if normaliser(s.libelle) == cible]
    if len(trouves) == 1:
        return trouves[0], ""
    if len(trouves) > 1:
        return None, f"type d'événement « {brut} » ambigu (présent dans plusieurs catégories) : écrire « Catégorie > {brut} »"
    return None, f"type d'événement « {brut} » non reconnu"

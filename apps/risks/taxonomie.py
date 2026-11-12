"""Typologie des événements de pertes opérationnelles.

Source : annexe de la Circulaire n°003-2017/CB/C (Commission Bancaire de l'UMOA),
« Modèle de classification des événements de pertes opérationnelles » —
7 catégories d'événements, 20 sous-catégories, avec exemples.

Les codes des catégories sont ceux de Incident.CategorieEvenement : ils servent
de clé de rapprochement entre le référentiel et le champ historique
Incident.categorie_evenement.

Cette structure alimente le référentiel en base (migration 0006 et commande
`charger_typologie_evenements`). Elle n'est pas lue au fil de l'eau : une fois
chargé, le référentiel est modifiable depuis l'administration.
"""

TYPOLOGIE = [
    {
        "code": "fraude_interne",
        "libelle": "Fraude interne",
        "sous_categories": [
            ("Activité non autorisée", [
                "Transactions non notifiées (intentionnellement)",
                "Transactions de type non autorisé (avec perte financière)",
                "Évaluation (intentionnellement) erronée d'une position",
            ]),
            ("Vol et fraude", [
                "Fraude/fraude au crédit/absence de provisions",
                "Vol/extorsion/détournement de fonds/vol qualifié",
                "Détournement de biens",
                "Destruction malveillante de biens",
                "Contrefaçon",
                "Falsification de chèques",
                "Falsification de dossier de crédit",
                "Contrebande",
                "Usurpation de compte/d'identité/etc.",
                "Fraude/évasion fiscale (délibérée)",
                "Corruption/commissions occultes",
                "Délit d'initié",
            ]),
        ],
    },
    {
        "code": "fraude_externe",
        "libelle": "Fraude externe",
        "sous_categories": [
            ("Vol et fraude", [
                "Vol/vol qualifié/Hold-up",
                "Contrefaçon",
                "Falsification de chèques",
            ]),
            ("Sécurité des systèmes", [
                "Dommages dus au piratage informatique d'informations (avec perte financière)",
            ]),
        ],
    },
    {
        "code": "pratiques_rh",
        "libelle": "Pratiques en matière d'emploi et sécurité sur le lieu de travail",
        "sous_categories": [
            ("Relations de travail", [
                "Questions liées aux rémunérations et aux avantages, à la résiliation du contrat de travail",
                "Activité syndicale",
            ]),
            ("Sécurité du lieu de travail", [
                "Responsabilité civile (chute, etc.)",
                "Violation de la réglementation sur la santé et la sécurité du personnel",
            ]),
            ("Égalité et discrimination", [
                "Plaintes pour tous types de discrimination",
            ]),
        ],
    },
    {
        "code": "clients_produits",
        "libelle": "Pratiques concernant les clients, les produits et l'activité commerciale",
        "sous_categories": [
            ("Conformité, diffusion d'informations et obligation fiduciaire", [
                "Violation de l'obligation fiduciaire/de recommandations (agir dans l'intérêt du client)",
                "Conformité/diffusion d'informations (connaissance de la clientèle, etc.)",
                "Violation de la confidentialité de la clientèle",
                "Atteinte à la vie privée",
                "Vente agressive",
                "Opérations fictives",
                "Utilisation abusive d'informations confidentielles",
            ]),
            ("Pratiques commerciales incorrectes", [
                "Législation antitrust",
                "Pratiques incorrectes",
                "Manipulation du marché",
                "Délit d'initié",
                "Activité sans agrément",
                "Blanchiment d'argent",
            ]),
            ("Défauts de production", [
                "Vices de production (absence d'agrément, etc.)",
                "Erreurs de modèle",
            ]),
            ("Sélection, promotion et exposition", [
                "Insuffisance de l'analyse clientèle",
                "Dépassement des limites d'exposition d'un client",
            ]),
            ("Services-conseil", [
                "Conflits sur l'efficience des prestations",
            ]),
        ],
    },
    {
        "code": "dommages_actifs",
        "libelle": "Dommages occasionnés aux actifs physiques",
        "sous_categories": [
            ("Catastrophes et autres sinistres", [
                "Pertes résultant d'une catastrophe naturelle",
                "Pertes humaines dues à des causes externes (terrorisme, vandalisme)",
            ]),
        ],
    },
    {
        "code": "interruption_si",
        "libelle": "Interruptions d'activités et défaillance des systèmes",
        "sous_categories": [
            ("Systèmes", [
                "Matériel",
                "Logiciel",
                "Télécommunications",
                "Interruptions/perturbations d'un service public",
            ]),
        ],
    },
    {
        "code": "execution_livraison",
        "libelle": "Exécution des opérations, livraison et gestion des processus",
        "sous_categories": [
            ("Saisie, exécution et suivi des transactions", [
                "Problèmes de communication",
                "Erreurs dans la saisie, le suivi ou le chargement",
                "Non-respect de délais ou d'obligations",
                "Erreurs de manipulation du modèle/système",
                "Erreurs comptables/d'affectation d'une entité",
                "Autres erreurs d'exécution",
                "Problèmes de livraison",
                "Fautes dans la gestion des sûretés",
                "Mauvais suivi des données de référence",
            ]),
            ("Surveillance et notification financière", [
                "Manquement à l'obligation de notification",
                "Inexactitudes dans les rapports externes",
            ]),
            ("Admission et documentation clientèle", [
                "Absence d'autorisation clientèle ou de déni de responsabilité",
                "Documents juridiques absents/incomplets",
            ]),
            ("Gestion des comptes clients", [
                "Accès non autorisé aux comptes",
                "Données clients incorrectes (pertes)",
                "Actifs clients perdus ou endommagés par négligence",
            ]),
            ("Contreparties commerciales", [
                "Faute d'une contrepartie hors clientèle",
                "Divers conflits avec une contrepartie hors clientèle",
            ]),
            ("Prestataires", [
                "Externalisation",
                "Conflits avec les prestataires",
            ]),
        ],
    },
]


def charger_typologie(CategorieEvenement, SousCategorieEvenement, RiskCategory=None):
    """Crée ou met à jour le référentiel (idempotent : rejouable sans doublon).

    Reçoit les classes de modèle en paramètre pour fonctionner à la fois depuis
    une migration (modèles historiques) et depuis une commande de gestion.
    Si RiskCategory est fourni, crée aussi (sans doublon) une catégorie de risque
    par catégorie d'événement, pour que la cartographie existante puisse s'y rattacher.
    Retourne (nb_categories, nb_sous_categories).
    """
    nb_cat = nb_sous = 0
    for ordre_cat, cat in enumerate(TYPOLOGIE, start=1):
        categorie, _ = CategorieEvenement.objects.update_or_create(
            code=cat["code"], defaults={"libelle": cat["libelle"], "ordre": ordre_cat},
        )
        nb_cat += 1
        for ordre_sous, (libelle, exemples) in enumerate(cat["sous_categories"], start=1):
            SousCategorieEvenement.objects.update_or_create(
                categorie=categorie, libelle=libelle,
                defaults={"exemples": "\n".join(exemples), "ordre": ordre_sous},
            )
            nb_sous += 1
        if RiskCategory is not None and not RiskCategory.objects.filter(nom=cat["libelle"]).exists():
            RiskCategory.objects.create(
                nom=cat["libelle"],
                description="Catégorie d'événement de risque opérationnel (Circulaire 003-2017/CB/C, annexe).",
            )
    return nb_cat, nb_sous

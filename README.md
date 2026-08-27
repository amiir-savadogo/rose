# Rose — Plateforme de gestion des risques opérationnels

Squelette du backend Django (V1 / MVP), conteneurisé avec Docker dès le départ.

## Modules inclus

- `apps/accounts` — utilisateurs, rôles (Admin, Risk Manager, Contrôleur, Agent, Direction), directions/entités, profil en libre-service (mot de passe, préférences de notification), supervision des sessions actives
- `apps/risks` — cartographie des risques : campagnes de revue (avec gel des évaluations à la clôture), catégories, évaluations historisées (inhérent/maîtrise/résiduel), plans d'action (avancement %, origine, statut auto-calculé), indicateurs clés de risque (KRI), vue matricielle (processus × entité)
- `apps/incidents` — déclaration et workflow de traitement des incidents (entité, catégorie d'événement type Bâle II, délai de détection, pertes/récupérations), page d'analyse agrégée
- `apps/obligations` — obligations réglementaires, génération automatique des échéances (`generer_echeances`), suivi de statut
- `apps/controles` — plan de contrôle (niveau 1/2, fréquence, exécutant/superviseur), programmation et suivi des exécutions (preuve archivée)
- `apps/comite` — séances du comité des risques (libellé, date, entité, participants, ordre du jour) et dossier imprimable généré par séance
- `apps/bibliotheque` — bibliothèque documentaire (chartes, politiques, procédures, plans) avec **historique complet des versions** : chaque révision est archivée séparément (jamais écrasée), la version en vigueur et les versions précédentes restent toutes consultables et téléchargeables
- `apps/audit` — journal d'audit inaltérable (création automatique via signaux sur tous les modèles métier, y compris connexions/déconnexions réussies et échouées), lecture réservée aux profils Contrôleur/Administrateur
- `apps/dashboard` — tableau de bord (risques évalués, hors appétence, contrôles en retard, profil de risque, matrice de chaleur), analyse interactive (graphiques Chart.js filtrables)

Interface complète en templates Django (pas seulement l'admin), avec charte graphique dédiée (sidebar, badges de niveau de risque, panneau d'aide contextuel autonome) et permissions par rôle appliquées à la fois dans l'affichage et côté serveur. Une page de référence (Paramètres → Rôles et permissions) documente ce que chaque rôle peut faire.

## Démarrage avec Docker

```bash
cp .env.example .env          # adapter les valeurs (mot de passe DB, secret key...)
docker compose up --build
```

L'application applique automatiquement les migrations au démarrage (voir `entrypoint.sh`).
Créer un compte administrateur :

```bash
docker compose exec web python manage.py createsuperuser
```

Ce compte est désormais automatiquement reconnu comme Administrateur côté Rose (section « Paramètres » visible dans la navigation). Si vous avez créé un superutilisateur **avant** ce correctif et qu'il n'a pas accès à la section Paramètres, corrigez-le en une commande :

```bash
docker compose exec web python manage.py promouvoir_admin <votre_identifiant>
```

(ou depuis `/admin/`, en éditant votre utilisateur et en positionnant le champ « role » sur « Administrateur »).

Accès à l'interface d'administration : http://localhost:8000/admin/
Accès à l'API de tableau de bord : http://localhost:8000/api/dashboard/synthese/

## Générer les échéances des obligations

À exécuter régulièrement (tâche planifiée quotidienne recommandée) :

```bash
docker compose exec web python manage.py generer_echeances
```

## Comment charger des données pour démarrer

Aucune donnée n'est préchargée : le premier lancement est une base vide. Ordre conseillé :

1. **Paramètres > Directions / Entités** — créez d'abord vos directions/agences (Siège, Direction des engagements...).
2. **Paramètres > Catégories de risques** — vos familles de risques (Risque de crédit, Risque opérationnel...).
3. **Paramètres > Utilisateurs** — créez les comptes de votre équipe et attribuez-leur un rôle.
4. **Paramètres > Campagnes de revue** — ouvrez une campagne (ex. « Revue annuelle 2026 ») avant de commencer à évaluer des risques.
5. **Cartographie des risques** — soit un par un via « + Risque », soit en bloc via **Paramètres > Importer des risques (Excel)** : téléchargez d'abord le modèle (.xlsx avec un exemple rempli et un guide sur l'onglet « Lisez-moi »), remplissez-le, puis importez-le. Les catégories/directions citées mais inconnues sont créées automatiquement. Un export Excel symétrique est disponible depuis la liste des risques.
6. Le reste (contrôles, obligations, bibliothèque, incidents) se saisit au fil de l'eau depuis chaque module.

## Rôles et permissions

Administrateur a toujours tous les droits (garde-fou volontaire, pour ne jamais se bloquer soi-même). Les quatre autres rôles (Risk Manager, Contrôleur, Agent, Direction) ont des droits éditables depuis **Paramètres > Rôles et permissions** : cochez/décochez par rôle qui peut gérer les risques, traiter les incidents, gérer les contrôles/obligations/bibliothèque, ou consulter le journal d'audit. Des valeurs de départ raisonnables sont préchargées à l'installation (migration de données).

## Tests automatisés

Les règles métier critiques (séparation exécutant/superviseur, preuve obligatoire, seuils KRI, gel des campagnes, statut automatique des plans d'action, filtrage par périmètre, journal d'audit inaltérable, versions documentaires, échéances réglementaires, décisions de comité) sont couvertes par 62 tests Django, dans le dépôt (`apps/*/tests.py`), pas seulement vérifiées manuellement lors du développement :

```bash
docker compose exec web python manage.py test
```

## Prochaines étapes suggérées

1. `python manage.py makemigrations` puis `migrate` pour créer le schéma initial.
2. Créer un compte administrateur et quelques catégories de risques de test.
3. Construire les vues/templates (ou une API DRF complète) pour les formulaires de saisie métier — l'admin Django sert de back-office temporaire en attendant.
4. Ajouter l'authentification à deux facteurs et l'intégration OpenID Connect (prévues en V2 dans le cahier des charges).

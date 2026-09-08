# Gestion Boutiques

Plateforme multi-boutiques destinée à centraliser les boutiques, produits, stocks et ventes. Le gestionnaire administre les opérations; les propriétaires consultent uniquement l'activité de leurs boutiques.

## État du projet

Le socle initial comprend :

- un dashboard React et TypeScript responsive raccordé à l'API;
- une API FastAPI avec endpoints de santé et de disponibilité PostgreSQL;
- PostgreSQL 18, des migrations Alembic et une isolation RLS testée;
- une authentification Argon2id/JWT avec renouvellement et révocation;
- les rôles gestionnaire et propriétaire avec une dépendance RBAC;
- le CRUD des boutiques avec recherche, filtres et pagination;
- la gestion des propriétaires et de leurs rattachements aux boutiques;
- un journal d'audit PostgreSQL immuable et consultable par le gestionnaire;
- un catalogue central de catégories et produits avec configuration par boutique;
- des soldes de stock matérialisés et un historique de mouvements immuable;
- des alertes automatiques de stock faible et de rupture;
- des écritures de stock sérialisées qui refusent atomiquement tout solde négatif;
- des ventes multi-produits atomiques avec prix figés, chiffre d'affaires et mouvements de stock liés;
- les règles métier de vente testées: saisie réservée au gestionnaire, fusion des lignes et refus sans écriture partielle;
- un environnement Python local associé au workspace VS Code.

Le dashboard authentifie les gestionnaires et propriétaires, restaure leur session, charge les boutiques accessibles et consolide en temps réel le catalogue, les ventes, les soldes, les mouvements et les alertes. Les gestionnaires peuvent créer, modifier, suspendre et réactiver les boutiques, puis enregistrer une vente multi-produit ou un mouvement de stock depuis l'interface.

## Structure

```text
apps/
  api/       API FastAPI et règles métier
  web/       Dashboard React du gestionnaire
docs/
  decisions/ Décisions fonctionnelles et techniques validées
```

L'application Flutter propriétaire sera ajoutée après stabilisation des contrats de l'API et du parcours web principal.

## Prérequis

- Python 3.12 ou version ultérieure
- Node.js 22 ou version ultérieure
- PostgreSQL 18

## Préparation de PostgreSQL

Le script crée la base et un rôle applicatif non privilégié. Il génère également les secrets dans `apps/api/.env`, qui est ignoré par Git.

```powershell
./scripts/setup-postgres.ps1
Set-Location apps/api
../../.venv/Scripts/python.exe -m alembic upgrade head
```

Le mot de passe administrateur PostgreSQL est demandé de manière masquée et n'est pas enregistré.

Pour créer le premier gestionnaire après la migration :

```powershell
$env:PYTHONPATH = "$PWD/src"
../../.venv/Scripts/python.exe -m gestion_boutiques.bootstrap `
  --organization-name "Mon organisation" `
  --organization-slug "mon-organisation" `
  --email "gestionnaire@example.com" `
  --full-name "Nom du gestionnaire"
```

## Démarrage du dashboard

```powershell
Set-Location apps/web
Copy-Item .env.example .env
npm install
npm run dev
```

Le dashboard est accessible sur `http://localhost:5173`. La variable `VITE_API_URL` permet de cibler une autre URL d'API; sa valeur par défaut est `http://127.0.0.1:8000`.

## Démarrage de l'API

Depuis la racine du projet :

```powershell
Copy-Item apps/api/.env.example apps/api/.env
Set-Location apps/api
../../.venv/Scripts/python.exe -m uvicorn gestion_boutiques.main:app --app-dir src --reload
```

L'API est accessible sur `http://localhost:8000`; sa documentation OpenAPI est disponible sur `http://localhost:8000/docs` en développement.

Endpoints disponibles :

- `GET /health` : état du service;
- `GET /health/ready` : disponibilité de PostgreSQL;
- `POST /api/v1/auth/login` : connexion;
- `POST /api/v1/auth/refresh` : renouvellement des jetons;
- `GET /api/v1/auth/me` : profil authentifié;
- `POST /api/v1/auth/logout-all` : révocation de toutes les sessions.
- `GET|POST /api/v1/stores` : liste et création des boutiques;
- `GET|PATCH /api/v1/stores/{store_id}` : consultation et modification;
- `POST /api/v1/stores/{store_id}/suspend|activate` : changement de statut;
- `GET|POST /api/v1/owners` : liste et création des propriétaires;
- `GET|PATCH /api/v1/owners/{owner_id}` : consultation et modification;
- `POST /api/v1/owners/{owner_id}/suspend|activate` : changement de statut;
- `POST /api/v1/owners/{owner_id}/reset-password` : nouveau mot de passe et révocation;
- `POST|DELETE /api/v1/stores/{store_id}/owners/{owner_id}` : rattachement;
- `GET /api/v1/audit-events` : historique filtrable des actions sensibles.
- `GET|POST /api/v1/catalog/categories` : liste et création des catégories;
- `PATCH /api/v1/catalog/categories/{category_id}` : modification d'une catégorie;
- `GET|POST /api/v1/catalog/products` : catalogue paginé et création des produits;
- `GET|PATCH /api/v1/catalog/products/{product_id}` : détail et modification d'un produit;
- `GET|PUT /api/v1/catalog/stores/{store_id}/products[/{product_id}]` : configuration boutique;
- `GET /api/v1/inventory/stores/{store_id}/balances` : soldes de stock;
- `GET|POST /api/v1/inventory/stores/{store_id}/movements` : historique et mouvement;
- `GET /api/v1/inventory/alerts` : alertes ouvertes ou historiques.
- `GET|POST /api/v1/sales` : historique accessible et saisie atomique d'une vente;
- `GET /api/v1/sales/{sale_id}` : détail d'une vente et de ses lignes.

## Contrôles qualité

```powershell
Set-Location apps/api
../../.venv/Scripts/python.exe -m pytest -q
../../.venv/Scripts/python.exe -m pytest tests/integration -q
../../.venv/Scripts/python.exe -m ruff check src tests migrations

Set-Location ../web
npm run lint
npm run build
```

Les règles MVP sont consignées dans `docs/decisions`.
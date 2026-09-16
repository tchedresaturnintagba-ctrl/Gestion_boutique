# Déploiement sur Render

Cette procédure crée trois ressources dans la région de Francfort :

- `gestion-boutiques-web`, site statique servi par le CDN Render ;
- `gestion-boutiques-api`, service Docker FastAPI ;
- `gestion-boutiques-db`, instance PostgreSQL 18 privée.

Le Blueprint utilise une base et une API payantes minimales. Render affiche le coût avant la création. Les offres gratuites ne conviennent pas à une production durable, notamment pour les sauvegardes et la disponibilité.

## 1. Préparer la livraison

Avant de lancer Render, vérifier que les contrôles locaux passent :

```powershell
Set-Location apps/api
../../.venv/Scripts/python.exe -m pytest -q
../../.venv/Scripts/python.exe -m ruff check src tests migrations

Set-Location ../web
npm run lint
npm run build
```

Enregistrer les changements dans Git et les pousser sur la branche `main`. Render ne peut déployer que les fichiers présents dans le dépôt distant.

## 2. Créer les ressources

1. Ouvrir le [tableau de bord Render](https://dashboard.render.com/).
2. Connecter le compte GitHub qui héberge ce dépôt.
3. Choisir **New > Blueprint** puis sélectionner le dépôt.
4. Conserver `render.yaml` comme chemin du Blueprint.
5. Vérifier le coût et lancer **Deploy Blueprint**.

Le fichier `render.yaml` effectue automatiquement les opérations suivantes :

- génère une clé JWT aléatoire ;
- injecte l'URL PostgreSQL privée dans l'API ;
- injecte les URLs publiques entre l'API et le frontend ;
- exécute `alembic upgrade head` avant chaque démarrage ;
- attend une réponse positive de `/health/ready` ;
- ne déploie automatiquement que lorsque la CI GitHub réussit.

La base n'accepte aucune connexion depuis Internet (`ipAllowList: []`). L'administration ponctuelle doit passer par le Shell Render du service API.

## 3. Créer le premier gestionnaire

Après le premier déploiement réussi, ouvrir le service `gestion-boutiques-api`, puis son onglet **Shell**. Exécuter :

```sh
python -m gestion_boutiques.bootstrap \
  --organization-name "Mon organisation" \
  --organization-slug "mon-organisation" \
  --email "gestionnaire@example.com" \
  --full-name "Nom du gestionnaire"
```

Saisir un mot de passe unique d'au moins 12 caractères dans le terminal. Il n'est ni affiché ni enregistré en clair.

## 4. Vérifier la mise en ligne

Depuis PowerShell, remplacer les deux URLs par celles affichées par Render :

```powershell
$apiUrl = "https://gestion-boutiques-api.onrender.com"
$webUrl = "https://gestion-boutiques-web.onrender.com"

Invoke-RestMethod "$apiUrl/health"
Invoke-RestMethod "$apiUrl/health/ready"
(Invoke-WebRequest -UseBasicParsing $webUrl).StatusCode
```

Les trois réponses attendues sont `status: ok`, `status: ready` et HTTP `200`. Se connecter ensuite au dashboard avec le slug, l'adresse e-mail et le mot de passe créés à l'étape précédente.

## 5. Domaine personnalisé

Render fournit HTTPS automatiquement. Pour utiliser un domaine personnalisé :

1. ajouter le domaine dans les paramètres du site statique ;
2. ajouter le sous-domaine API dans les paramètres du service API ;
3. remplacer la valeur de `VITE_API_URL` par l'URL API personnalisée ;
4. remplacer `GB_CORS_ORIGIN` par l'URL exacte du frontend ;
5. redéployer les deux services.

Ces deux variables sont normalement alimentées automatiquement par le Blueprint avec les domaines `onrender.com`.

## 6. Exploitation

- Surveiller `/health/ready` et les métriques Render.
- Vérifier la politique de sauvegarde et la durée de rétention PostgreSQL dans Render.
- Télécharger un export logique avant toute migration risquée ou suppression de ressource.
- Faire tourner la clé `GB_JWT_SECRET_KEY` en cas de suspicion de fuite ; cette opération invalide les sessions actives.
- Tester régulièrement une restauration de sauvegarde.

Pour revenir à une version antérieure de l'application, utiliser **Rollback** sur les services Render. Une migration de base destructive exige une procédure dédiée ; ne pas compter sur le rollback applicatif pour annuler automatiquement une migration Alembic.
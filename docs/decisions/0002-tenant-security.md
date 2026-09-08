# Décision 0002 - Isolation et authentification

**Statut :** validée
**Date :** 7 septembre 2026

## Décision

- Une organisation constitue la frontière principale du tenant.
- Chaque utilisateur appartient à une organisation.
- Une boutique appartient à une organisation et peut être rattachée à plusieurs propriétaires.
- PostgreSQL applique la Row-Level Security aux organisations, utilisateurs, boutiques et rattachements.
- L'API positionne `app.current_organization_id` dans chaque transaction authentifiée.
- Les mots de passe sont hachés avec Argon2id.
- Les jetons d'accès expirent après 15 minutes et les jetons de renouvellement après 7 jours.
- Une version de jeton stockée sur l'utilisateur permet de révoquer toutes ses sessions.

## Connexion

La connexion demande le slug de l'organisation, l'adresse email et le mot de passe. Cette combinaison permet de conserver la possibilité d'utiliser une même adresse dans des organisations distinctes.

## Défense en profondeur

Le RBAC FastAPI contrôle les opérations autorisées par rôle. La RLS PostgreSQL reste une seconde barrière contre les requêtes qui omettraient accidentellement le filtre d'organisation.
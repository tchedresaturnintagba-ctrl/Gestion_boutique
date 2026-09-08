# Décision 0003 - Boutiques, propriétaires et audit

**Statut :** validée
**Date :** 8 septembre 2026

## Boutiques

- Le gestionnaire crée, modifie, active et suspend les boutiques de son organisation.
- Le gestionnaire voit toutes les boutiques de son organisation.
- Un propriétaire voit uniquement les boutiques auxquelles il est rattaché.
- Une boutique non accessible est présentée comme introuvable afin de ne pas révéler son existence.
- Le code d'une boutique est unique dans son organisation et normalisé en majuscules.

## Propriétaires

- Seul un gestionnaire peut créer, modifier, suspendre ou réactiver un propriétaire.
- Le mot de passe initial et les mots de passe réinitialisés contiennent au moins 12 caractères.
- Une suspension, une réactivation ou une réinitialisation du mot de passe révoque les jetons existants.
- Un rattachement entre organisations distinctes est refusé sans révéler l'utilisateur étranger.

## Audit

- Les créations, modifications, changements de statut, réinitialisations et rattachements sont audités dans la transaction métier.
- L'audit stocke l'acteur, l'action, le type et l'identifiant de l'entité, la date et des métadonnées non sensibles.
- Aucun mot de passe ni jeton n'est journalisé.
- PostgreSQL autorise uniquement l'insertion et la lecture des événements; leur modification et leur suppression directes sont bloquées par RLS.
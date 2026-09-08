# Décision 0001 - Saisie des ventes dans le MVP

**Statut :** validée
**Date :** 7 septembre 2026

## Décision

- Seul le gestionnaire peut saisir une vente dans le MVP.
- Un propriétaire dispose d'un accès en lecture seule aux boutiques auxquelles il est rattaché.
- La validation d'une vente est bloquée si au moins un produit ne dispose pas d'un stock suffisant.
- Une vente refusée ne produit ni mouvement de stock, ni chiffre d'affaires, ni écriture partielle.
- Une future permission explicite pourra autoriser exceptionnellement le stock négatif. Elle est hors MVP et devra être auditée.

## Conséquence technique

La vérification de tous les produits doit précéder les écritures et s'exécuter dans la même transaction PostgreSQL que la vente et ses mouvements de stock. Les lignes de stock concernées devront être verrouillées pendant cette transaction.
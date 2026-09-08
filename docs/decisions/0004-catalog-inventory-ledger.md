# Décision 0004 - Catalogue et registre de stock

**Statut :** validée
**Date :** 8 septembre 2026

## Catalogue

- Les produits appartiennent au catalogue central d'une organisation.
- Le SKU est unique dans l'organisation et normalisé en majuscules.
- Chaque boutique configure son prix FCFA, son seuil de stock faible et son statut.
- Les prix sont stockés en entiers FCFA; les quantités utilisent trois décimales.
- Un propriétaire ne voit que les produits configurés dans ses boutiques.

## Stock

- Le solde courant est matérialisé par produit et boutique pour une lecture rapide.
- Toute variation crée un mouvement immuable avec le solde avant et après l'opération.
- La ligne de solde est verrouillée avec `FOR UPDATE` pendant chaque variation.
- Le solde ne peut jamais devenir négatif; une sortie refusée ne crée aucune écriture.
- Seul un gestionnaire crée des mouvements; les propriétaires disposent d'une lecture seule.

## Alertes

- Un solde nul ouvre une alerte de rupture.
- Un solde positif inférieur ou égal au seuil ouvre une alerte de stock faible.
- Une seule alerte peut être ouverte par produit et boutique.
- L'alerte est résolue quand le stock repasse au-dessus du seuil.

## Sécurité

- Toutes les tables du catalogue et du stock utilisent l'isolation RLS par organisation.
- Les mouvements autorisent uniquement l'insertion et la lecture via les politiques RLS.
- Les écritures de stock et leur événement d'audit sont validés dans la même transaction.
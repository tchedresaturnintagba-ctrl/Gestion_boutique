# KërManager Mobile

Application Flutter destinée aux propriétaires de boutiques. Elle utilise l'API
FastAPI existante pour l'authentification, les boutiques autorisées, le stock,
les alertes et les ventes.

## Lancement local

Depuis `apps/mobile`, avec l'API sur le poste de développement :

```powershell
# Navigateur
flutter run -d chrome --dart-define=API_URL=http://127.0.0.1:8000

# Émulateur Android
flutter run -d emulator --dart-define=API_URL=http://10.0.2.2:8000
```

Pour un téléphone physique, utiliser l'adresse IP locale du poste à la place de
`10.0.2.2` et rendre le port 8000 accessible sur le réseau local. En production,
passer l'URL HTTPS publique avec `--dart-define=API_URL=...`.

## Contrôles

```powershell
flutter analyze
flutter test
flutter build web --dart-define=API_URL=http://127.0.0.1:8000
```

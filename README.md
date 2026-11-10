# Pipeline Data

Pipeline CSV vers un stockage compatible S3, traitements Python et PostgreSQL.

## Démarrage rapide

Prérequis : Docker avec Docker Compose.

```bash
docker compose up --build --abort-on-container-exit --exit-code-from pipeline
```

La commande démarre RustFS et PostgreSQL, génère deux fichiers CSV, les envoie dans S3 et lance le traitement. Une nouvelle exécution ne réinsère pas les fichiers déjà traités.

Pour arrêter les services :

```bash
docker compose down
```

Pour tout effacer, y compris les données persistantes :

```bash
docker compose down -v
```

# Video Factory AI

Usine vidéo multi-agents free-first qui produit automatiquement des documentaires multilingues et des dessins animés pour enfants.

## Stack

- **Frontend**: Next.js (admin dashboard)
- **Backend**: FastAPI (multi-agents orchestrator)
- **Database / Auth / RLS / Storage**: Supabase (Postgres), SQLite en dev
- **Queues / Verrous**: Redis (fakeredis en dev)
- **Docker**: dev + deploy

## Architecture

```
video-factory-ai/
├── backend/            # FastAPI, agents, orchestrator, registries, workers
├── frontend/           # Next.js admin
├── supabase/           # migrations, RLS policies, seed
├── infra/              # docker compose dev/deploy, nginx, backups
├── docs/               # spec, security, providers
└── tests/              # unit, integration, e2e
```

## Démarrage

```bash
# Backend (dev)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 3001

# Frontend (dev)
cd frontend
npm install
npm run dev
```

Ou tout-en-un avec Docker Compose:

```bash
docker compose -f infra/docker-compose.dev.yml up
```

## Base de données & migrations (Alembic)

Le schéma est géré par [Alembic](https://alembic.sqlalchemy.org/). L'URL de la
base est résolue depuis `DATABASE_URL` (`app/core/config.py`), donc la même
configuration fonctionne en dev (SQLite), en test et en production (Postgres).

Au démarrage, le backend applique automatiquement les migrations à jour
(`alembic upgrade head`). Les bases dev créées avant l'introduction d'Alembic
sont adoptées par un `stamp` à head (tables existantes conservées).

Commandes utiles (depuis `backend/`) :

```bash
# Appliquer les migrations (même effet que le démarrage)
alembic upgrade head

# Créer une nouvelle migration après modification des modèles (app/models)
alembic revision --autogenerate -m "description du changement"

# Revenir en arrière d'une migration
alembic downgrade -1

# Voir l'état actuel
alembic current
```

> ⚠️ SQLite a des capacités limitées d'`ALTER TABLE`. Les migrations de schéma
> initial sont identiques sur SQLite et Postgres ; pour toute évolution future de
> colonnes existantes, prévoir une migration manuelle compatible SQLite (batch
> mode) si le dev SQLite doit rester fonctionnel.

## Stockage (streaming)

Le registre de stockage (`app/registries/storage_registry.py`) écrit les assets
**sans jamais charger le fichier entier en mémoire** :

- `StorageRegistry.store_asset_stream(path, src)` accepte des `bytes`, un
  **chemin de fichier** ou un objet fichier-like. La taille et le checksum
  SHA-256 sont calculés en **une seule passe de streaming**, puis la source est
  re-streamée vers chaque backend actif (local, S3/R2/B2/MinIO, Supabase).
- `store_asset(data: bytes)` reste disponible comme raccourci pour les petits
  contenus en mémoire.
- Les adaptateurs implémentent `upload_stream()` : copie fichier→fichier
  (local), `upload_fileobj` (S3), upload chunké (Supabase).

Le quota (`quota_bytes`) est vérifié **avant** l'upload (erreur `507` en cas de
dépassement), et les chemins sont protégés contre le path traversal
(`os.path.commonpath`).

## Notifications (email / Discord / Telegram)

À la fin d'une génération, l'utilisateur peut être notifié par **email**,
**Discord** et/ou **Telegram** — les trois canaux sont indépendants et
optionnels, et **aucun ne bloque jamais le pipeline** (envoi fire-and-forget).
Par défaut, il reçoit une notification **par épisode** puis un **récapitulatif
de série** listant le statut (réussi/échoué) de chaque épisode.

- Le choix des canaux se fait **à chaque lancement** (cases à cocher au moment
  de lancer le pipeline).
- Les identifiants Discord (webhook URL) et Telegram (bot token + chat id) se
  configurent dans **Paramètres** (chiffrés en base, jamais ré-affichés).
- L'email de destination est celui du compte (`user.email`).

### Configuration email (variables d'environnement)

| Variable | Valeur | Rôle |
|---|---|---|
| `EMAIL_PROVIDER` | `resend` \| `sendgrid` \| `smtp` \| vide | Fournisseur actif (vide = désactivé) |
| `EMAIL_FROM` | `Video Factory AI <no-reply@…>` | Expéditeur |
| `RESEND_API_KEY` | … | Clé API Resend |
| `SENDGRID_API_KEY` | … | Clé API SendGrid |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | … | Relais SMTP générique (fonctionne aussi avec Resend/SendGrid) |
| `APP_BASE_URL` | `http://localhost:3000` | Base des liens cliquables dans les notifications |

Sans `EMAIL_PROVIDER`, les notifications email sont simplement ignorées (les
webhooks Discord/Telegram restent actifs). Les webhooks Discord/Telegram sont
gratuits et illimités.

## Documentation

- Spécification: docs/spec.md
- Sécurité: docs/security.md
- Providers: docs/providers.md

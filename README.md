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

## Documentation

- Spécification: docs/spec.md
- Sécurité: docs/security.md
- Providers: docs/providers.md

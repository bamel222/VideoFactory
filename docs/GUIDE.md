# Guide de prise en main — Video Factory AI

Ce guide vous explique pas à pas comment **déployer** l'application, la **prendre en main**,
configurer de **vrais providers** (avec de vrais clés API) et générer votre **première vidéo**
(documentaire ou cartoon). Il couvre aussi la différence entre le flux de développement et le flux de déploiement.

---

## Table des matières

1. [Prérequis](#1-prérequis)
2. [Déployer l'application (pas à pas)](#2-déployer-lapplication-pas-à-pas)
   - 2.1 Mode développement (local)
   - 2.2 Mode production (Docker)
   - 2.3 Options de configuration
3. [Créer et sécuriser le dépôt GitHub](#3-créer-et-sécuriser-le-dépôt-github)
4. [Prendre en main l'application (pas à pas)](#4-prendre-en-main-lapplication-pas-à-pas)
5. [Ajouter de vrais providers et clés API](#5-ajouter-de-vrais-providers-et-clés-api)
   - 5.1 Les clés côté serveur (fichier `.env`)
   - 5.2 Déclarer un provider réel dans l'interface
   - 5.3 Tester le provider
   - 5.4 Résumé des rôles et services recommandés
6. [Générer votre première vidéo (pas à pas)](#6-générer-votre-première-vidéo-pas-à-pas)
7. [Dev vs Deploy : comprendre la différence](#7-dev-vs-deploy--comprendre-la-différence)
8. [Dépannage](#8-dépannage)

---

## 1. Prérequis

| Outil | Nécessité | Version minimale |
|---|---|---|
| Docker + Docker Compose | Oui (dev et prod) | Docker 24+, Compose v2 |
| Git | Oui | — |
| Compte GitHub | Pour héberger et automatiser | — |
| Compte Supabase (optionnel) | Pour Postgres/S3 géré | — |
| Clés API fournisseurs | Pour la génération réelle | voir section 5 |

Aucune connaissance préalable n'est requise au-delà de savoir ouvrir un terminal.

---

## 2. Déployer l'application (pas à pas)

Le projet est un monorepo :

```
video-factory-ai/
├── backend/    # API FastAPI (port 3001)
├── frontend/   # Administration Next.js (port 3000)
├── supabase/   # Migrations SQL et politiques RLS
├── infra/      # Docker Compose, Nginx, sauvegardes
└── docs/       # Spécifications et guides
```

### 2.1 Mode développement (local, sans Docker)

Utilisez ce mode pour travailler confortablement pendant le développement.

**Étape 1 — Copier le fichier d'environnement :**

```bash
cp .env.example .env
```

**Étape 2 — Modifier les secrets dans `.env` (obligatoire en production, recommandé en dev) :**

- `ENCRYPTION_KEY` : une phrase d'au moins 32 caractères (chiffre les clés API en base).
- `JWT_SECRET` : un mot de passe long et aléatoire (signe les jetons d'authentification).

> Ne commitez jamais le fichier `.env` (il est ignoré par Git).

**Étape 3 — Installer le backend :**

```bash
cd backend
pip install -r requirements.txt
python -m app.scripts.seed
```

Le seed crée le schéma SQLite, les comptes de test et les 13 providers factices (mock, gratuits).

**Étape 4 — Installer le frontend :**

```bash
cd ../frontend
npm install
```

**Étape 5 — Démarrer les deux serveurs :**

```bash
cd backend && uvicorn app.main:app --reload --port 3001
cd ../frontend && npm run dev
```

- Administration : http://localhost:3000
- API : http://localhost:3001
- Santé : http://localhost:3001/health

Le frontend proxifie automatiquement `/api` vers le backend : **aucun CORS** à gérer.

### 2.2 Mode production (Docker)

Deux topologies sont fournies dans `infra/` :

| Fichier | Usage | Inclut |
|---|---|---|
| `docker-compose.dev.yml` | Développement | Postgres + Redis + backend (reload) + frontend (reload) |
| `docker-compose.deploy.yml` | Production | Postgres + Redis + backend + worker + Nginx |

**Étape 1 — Préparer le fichier `.env` à la racine** (voir 2.1) et ajouter en plus :

```bash
POSTGRES_USER=vfactory
POSTGRES_PASSWORD=<mot de passe fort>
POSTGRES_DB=video_factory
```

**Étape 2 — Lancer l'environnement de développement :**

```bash
docker compose -f infra/docker-compose.dev.yml up --build
```

Les migrations SQL de `supabase/migrations/` sont appliquées automatiquement au premier démarrage de Postgres.

**Étape 3 — Lancer l'environnement de production :**

```bash
docker compose -f infra/docker-compose.deploy.yml up --build -d
docker compose -f infra/docker-compose.deploy.yml exec backend python -m app.scripts.seed
```

Le service Nginx expose l'application sur le port 80 et sert le frontend compilé.
Le worker (`app.workers.runner`) traite les jobs vidéo en arrière-plan via Redis.

**Étape 4 — Vérifier le déploiement :**

```bash
curl http://localhost/health        # doit répondre {"status":"ok",...}
docker compose -f infra/docker-compose.deploy.yml ps
```

### 2.3 Options de configuration

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `DATABASE_URL` | Connexion base de données | `sqlite:///./video_factory.db` |
| `REDIS_URL` | File de jobs et verrous | `redis://localhost:6379/0` |
| `ENCRYPTION_KEY` | Chiffrement Fernet des secrets | placeholder à changer |
| `JWT_SECRET` | Signature des jetons JWT | placeholder à changer |
| `CORS_ORIGINS` | Origines autorisées | `http://localhost:3000,http://localhost:3001` |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase (Postgres/S3/Auth) | vides |
| `OPENAI_API_KEY`, `DEEPL_API_KEY`, … | Clés des vrais providers | vides |

---

## 3. Créer et sécuriser le dépôt GitHub

Le projet actuel n'a **pas de remote** : tout est en local. Pour l'héberger :

**Étape 1 — Créer un dépôt vide sur GitHub** (ne pas cocher "Add a README").

**Étape 2 — Lier le dépôt local :**

```bash
git remote add origin https://github.com/<VOTRE-COMPTE>/video-factory-ai.git
git branch -M master
git push -u origin master
```

**Étape 3 — Ajouter les secrets GitHub** (pour l'CI/CD) :

- Ouvrez le dépôt → Settings → Secrets and variables → Actions.
- Ajoutez au minimum : `ENCRYPTION_KEY`, `JWT_SECRET`, et vos clés de fournisseurs.

> Ne mettez jamais de vraies clés dans les fichiers du dépôt. Les secrets GitHub Actions
> et le fichier local `.env` sont les bons endroits.

---

## 4. Prendre en main l'application (pas à pas)

Une fois le backend et le frontend démarrés :

**Étape 1 — Se connecter.**

Ouvrez http://localhost:3000 et connectez-vous avec un compte seed :

| Rôle | Email | Mot de passe |
|---|---|---|
| Owner (propriétaire) | `owner@vf.ai` | `password123` |
| Admin | `admin@vf.ai` | `password123` |
| Reviewer (relecteur) | `reviewer@vf.ai` | `password123` |

> Changez ces mots de passe avant toute mise en production (page **Utilisateurs**).

**Étape 2 — Explorer le menu.**

- **Vue d'ensemble** : statistiques globales (séries, jobs, coûts).
- **Séries & Pipelines** : créer et lancer des documentaires / cartoons.
- **Providers** : déclarer les fournisseurs (mock ou réels) et leurs clés.
- **Stockage** : gérer les backends de stockage (local, S3, R2, B2, MinIO, Supabase).
- **Jobs** : état d'avancement des pipelines.
- **Review** : approuver ou renvoyer les épisodes.
- **Monétisation** : prioriser les séries et estimer les budgets.
- **Utilisateurs** : gérer les comptes et les rôles.
- **Audit** : trace immuable des actions (hash chainé).

**Étape 3 — Comprendre le cycle de vie d'une série.**

```
Création (Séries & Pipelines)
   └─> Plan automatique (épisodes → scènes → tâches)
   └─> Dry-run (estimation budget/tâches, sans frais)
   └─> Run (exécution réelle par les providers)
          └─> Review (le Reviewer approuve ou demande une révision)
          └─> Publication (le Owner publie l'épisode)
          └─> SEO + Shorts générés automatiquement
```

**Étape 4 — Tester sans rien dépenser.**

Grâce aux providers `mock://` pré-chargés, chaque étape fonctionne gratuitement :
les images, audios et vidéos sont de vrais fichiers générés localement (via ffmpeg).
C'est le moyen le plus rapide de prendre en main l'application.

---

## 5. Ajouter de vrais providers et clés API

Deux niveaux : les clés **serveur** (dans le `.env` du backend) et la déclaration du **provider réel**
(dans l'interface, avec sa clé et son endpoint).

### 5.1 Les clés côté serveur (fichier `.env`)

Le client réel (`RealProviderClient`) lit des clés dans l'environnement du backend.
Modifiez votre `.env` backend et redémarrez le backend :

```bash
# Génération de texte (script, recherche, SEO, QA)
OPENAI_API_KEY=sk-...

# Traduction multilingue (doublage)
DEEPL_API_KEY=...

# Transcription (sous-titres)
DEEPGRAM_API_KEY=...

# Voix / TTS
ELEVENLABS_API_KEY=...
```

> Ces clés sont à **vous**. Créez-les sur les sites des fournisseurs
> (platform.openai.com, deepl.com, deepgram.com, elevenlabs.io…).
> Ne les partagez jamais et ne les commitez jamais.

### 5.2 Déclarer un provider réel dans l'interface

1. Allez dans **Providers** → **Ajouter un provider**.
2. Renseignez :
   - **Nom** : ex. `OpenAI GPT-4o mini`
   - **Rôle** : le rôle de capacité (voir tableau 5.4).
   - **Endpoint** : URL de l'API (ex. `https://api.openai.com/v1/chat/completions`).
     Une URL qui ne commence pas par `mock://` est traitée comme un provider **réel**.
   - **Clé API** : la clé correspondante (elle est chiffrée avec `ENCRYPTION_KEY` avant stockage).
   - **Priorité** : **plus petit = choisi en premier**. Mettez `1` pour que le provider réel
     soit préféré au mock (priorité 10).
   - **Modèle** : ex. `gpt-4o-mini` (utilisé dans l'appel API).
   - **Quota / coût / langues / formats** : facultatifs mais utiles au sélecteur.
3. Enregistrez.

> Un provider réel **par rôle** suffit : `research`, `script`, `translation`, `tts`,
> `voice`, `music`, `image`, `video`, `assembly`, `seo`, `qa`, `licensing`, `caption`.
> Tous les autres rôles restent sur les mocks si vous n'avez pas de clé pour eux.

### 5.3 Tester le provider

Dans **Providers**, cliquez sur l'icône santé de votre provider :

- **Healthcheck** : vérifie que le provider est actif et joignable.
- **Tester la clé** : vérifie qu'une clé est bien configurée et acceptée.

Si le statut passe à "healthy" et que le test de clé renvoie OK, le sélecteur de providers
pourra l'utiliser automatiquement.

### 5.4 Résumé des rôles et services recommandés

| Rôle | Ce que fait le pipeline | Service recommandé |
|---|---|---|
| `research` | Recherche de faits, plan de série | OpenAI (ChatGPT) |
| `script` | Écriture des scripts d'épisodes | OpenAI (ChatGPT) |
| `translation` | Doublage multilingue | DeepL |
| `transcription` | Sous-titres | Deepgram / Whisper |
| `tts` | Voix off | ElevenLabs / Cartesia |
| `voice` | Identité vocale / clone | ElevenLabs |
| `music` | Musiques et jingles | Suno / Stable Audio |
| `image` | Frames, personnages, décors | OpenAI DALL-E / Stable Diffusion |
| `video` | Clips vidéo | Heygen / Pexels |
| `assembly` | Montage final, encodage | ffmpeg (local) |
| `seo` | Titre, description, tags, shorts | OpenAI |
| `qa` | Contrôle qualité, continuité | OpenAI |
| `licensing` | Vérification des licences | OpenAI |
| `caption` | Sous-titres synchronisés | ffmpeg / Deepgram |

> En production (Docker), pensez à **relayer les clés** au conteneur backend :
> elles doivent figurer dans `environment:` du service `backend` de
> `infra/docker-compose.deploy.yml` (elles y sont déjà déclarées, il suffit de
> les remplir dans votre `.env` racine).

---

## 6. Générer votre première vidéo (pas à pas)

Une fois l'application démarrée et vos providers configurés :

**Étape 1 — Créer la série.**

Dans **Séries & Pipelines**, remplissez :
- **Titre** : ex. `Les océans, notre avenir`.
- **Sujet** (jusqu'à 3000 caractères) : décrivez l'idée globale, le public visé, la tonalité.
  Ex. : *"Documentaire grand public sur l'histoire des océans, du rôle des courants
  à la biodiversité des abysses, avec des interviews fictives et des images d'archives."*
- **Type** : `Documentaire` ou `Cartoon` (pour les enfants, un pack de continuité
  avec personnages est généré automatiquement).
- **Épisodes** : entre 1 et 10.
- **Langue** : `fr`, `en`, `es`, `de`, `it`, `pt`…

Cliquez **Créer**. Le plan de série est généré automatiquement
(bible, épisodes, scènes, segments, graphe de tâches).

**Étape 2 — Lancer le dry-run (sans frais).**

Dans la page de la série, cliquez **Dry run**. Vous obtenez un rapport :
- nombre de tâches et d'épisodes ;
- estimation budgétaire et coûts ;
- vérification que tous les rôles nécessaires ont un provider disponible
  (`ready_to_launch: true`).

> C'est l'étape de sécurité : on vérifie avant de dépenser de l'argent réel.

**Étape 3 — Lancer le pipeline réel.**

Cliquez **Run**. Le master orchestrator exécute les tâches dans l'ordre du graphe :
recherche → script → narration → TTS → musique → images → vidéo → montage → QA →
licences → SEO → shorts → rapport de provenance.

- Les tâches réussies sont **checkpointées** (reprise possible après interruption).
- Vous suivez la progression dans **Jobs**.

**Étape 4 — Vérifier le Continuity Pack (cartoon).**

Le pack de continuité (personnages, règles négatives) est créé au plan de série.
Consultez-le depuis la page de la série : il garantit la cohérence des personnages
et du style d'un épisode à l'autre.

**Étape 5 — Relire et approuver (Reviewer).**

Connectez-vous avec `reviewer@vf.ai` → **Review** :
- consultez le rapport de QA et le package SEO ;
- cliquez **Approuver** (ou **Demander une révision**).

**Étape 6 — Publier (Owner).**

Connectez-vous avec `owner@vf.ai`, ouvrez l'épisode approuvé et cliquez **Publier**.
L'épisode passe au statut `published`.

**Étape 7 — Récupérer vos fichiers.**

Les médias générés sont stockés dans `backend/data/media/<slug>/`
(episode_1_final.mp4, etc.) et répliqués sur les backends de stockage configurés.

**Résultat :** votre première vidéo est générée, contrôlée, approuvée et publiée.
Pour une vraie vidéo utilisable, assurez-vous que les providers `image`, `video`, `tts`
et `music` sont de vrais providers avec des clés valides (sinon les mocks produisent
des fichiers techniques de démonstration).

---

## 7. Dev vs Deploy : comprendre la différence

### Situation actuelle du dépôt

Le dépôt a **une seule branche** (`master`) et **aucun remote** (tout est local).
Il n'existe donc pas encore de branches `dev` ou `deploy`. En revanche, le projet
contient **deux workflows GitHub Actions** dans `.github/workflows/` qui matérialisent
la séparation dev / déploiement :

| Workflow | Déclencheur | Rôle |
|---|---|---|
| `dev.yml` | Push sur `master` + Pull Requests | **CI de développement** : lint, tests backend/frontend, audits de dépendances (`pip-audit`, `npm audit`), génération du SBOM |
| `deploy.yml` | Tag `v*` (ex. `v1.0.0`) ou déclenchement manuel | **Livraison** : build des images Docker, push vers le registre, déploiement sur le serveur cible |

### La bonne pratique recommandée

```
branche dev   → tests et intégration (CI = dev.yml)
branche master → code stable et vérifié
tag v1.0.0     → déclenche la production (workflow deploy.yml)
```

1. **Dev** (branche de travail) : vous poussez vos modifications en continu.
   `dev.yml` tourne à chaque push : si un test ou un lint casse, vous le savez immédiatement.
2. **Master** (branche stable) : une fois une fonctionnalité validée en dev,
   on la fusionne dans `master` (Pull Request + review). `dev.yml` tourne aussi dessus.
3. **Déploiement** : quand master est prêt, on crée un **tag** (`git tag v1.0.0 && git push --tags`).
   `deploy.yml` construit les images, les pousse dans le registre de conteneurs,
   puis déploie sur le serveur (via SSH ou webhook — à compléter dans le workflow
   selon votre infrastructure).

### En résumé

- **Dev = le cycle de développement** : je code, je teste, je corrige (automatisé par `dev.yml`).
- **Deploy = le cycle de mise en production** : je livre une version stable,
  testée et taggée, exécutée par `deploy.yml`.
- Une seule codebase, deux automatismes, zéro surprise en production.

---

## 8. Dépannage

| Problème | Solution |
|---|---|
| `401` à la connexion | Vérifiez l'email/mot de passe ou relancez le seed sur une base vierge |
| Le dry-run dit `ready_to_launch: false` | Un rôle n'a pas de provider actif : ajoutez-en un dans **Providers** (mock accepté) |
| Mon provider réel n'est jamais choisi | Baissez sa **priorité** sous celle du mock et faites son **healthcheck** |
| `Provider ... n'a pas de clé API configurée` | Renseignez la clé correspondante dans le `.env` backend et redémarrez, ou en mode Docker dans le service `backend` |
| `502` sur le frontend | Le backend est arrêté : redémarrez uvicorn |
| La publication est bloquée (409) | L'épisode n'est pas `approved` (ou le rôle n'est pas Owner) |
| Images/vidéos "vides" | Les providers de ce rôle sont en `mock://` : configurez un vrai provider pour des médias réels |
| Le résumé du job ne bouge pas | Vérifiez Redis (`REDIS_URL`) et les logs du worker/backend |

---

Pour toute question, les spécifications complètes sont dans `docs/spec.md`,
la sécurité dans `docs/security.md` et l'inventaire des dépendances dans `docs/sbom.json`.

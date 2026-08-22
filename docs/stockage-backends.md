# Backends de stockage — référence & configuration

Ce document décrit chaque backend de stockage supporté, s'il est réellement
fonctionnel, et la configuration JSON exacte à saisir dans l'application
(Stockage → Ajouter/Modifier).

Tous les backends utilisent déjà des dépendances installées :
- `boto3` → S3 / R2 / B2 / MinIO
- `httpx` → Supabase / pCloud
- système de fichiers local → NAS

**Aucun package supplémentaire n'est nécessaire.**

---

## Tableau récapitulatif

| Backend | Techno | Fonctionnel | Notes |
|---|---|---|---|
| S3 (OVHCloud, AWS…) | boto3 | ✅ | validé en production |
| R2 (Cloudflare) | boto3 (S3-compatible) | ✅ | rien à installer |
| B2 (Backblaze) | boto3 (S3-compatible) | ✅ | rien à installer |
| MinIO (auto-hébergé) | boto3 (S3-compatible) | ✅ | option `verify_ssl` |
| NAS | filesystem local | ✅ | le disque doit être monté |
| Supabase Storage | httpx (REST) | ✅ | clé service role |
| pCloud | httpx (REST) | ✅ | token OAuth2 |

---

## 1. S3 (OVHCloud, AWS, ou tout S3-compatible)

```json
{
  "endpoint_url": "https://s3.eu-west-par.io.cloud.ovh.net",
  "bucket": "nom-du-bucket",
  "access_key": "…",
  "secret_key": "…",
  "region": "eu-west-par"
}
```

- `endpoint_url` : l'URL S3 du fournisseur.
- Pour AWS, omettre `endpoint_url` (ou laisser vide) et utiliser la région AWS.
- Le bucket doit exister et la clé doit avoir les permissions `PutObject`,
  `GetObject`, `ListBucket`, `DeleteObject`.

## 2. R2 (Cloudflare)

```json
{
  "endpoint_url": "https://<account_id>.r2.cloudflarestorage.com",
  "bucket": "nom-du-bucket",
  "access_key": "R2_ACCESS_KEY_ID",
  "secret_key": "R2_SECRET_ACCESS_KEY",
  "region": "auto"
}
```

- `access_key` / `secret_key` sont les **clés API R2** (onglet R2 → Manage API tokens).
- `endpoint_url` contient l'**account_id** (visible dans le dashboard Cloudflare).

## 3. B2 (Backblaze)

```json
{
  "endpoint_url": "https://s3.us-west-004.backblazeb2.com",
  "bucket": "nom-du-bucket",
  "access_key": "keyID",
  "secret_key": "applicationKey",
  "region": "us-west-004"
}
```

- `access_key` = **keyID**, `secret_key` = **applicationKey** (créées dans
  Backblaze B2 → Application Keys).
- L'`endpoint_url` et la `region` dépendent de la région du bucket (visible
  dans l'URL du bucket dans B2).

## 4. MinIO (auto-hébergé)

```json
{
  "endpoint_url": "http://192.168.1.10:9000",
  "bucket": "nom-du-bucket",
  "access_key": "minioadmin",
  "secret_key": "minioadmin",
  "region": "us-east-1",
  "verify_ssl": false
}
```

- **Important** : MinIO est souvent sur une IP/URL **privée** et/ou en HTTP.
  Il faut alors mettre `ALLOW_PRIVATE_STORAGE_ENDPOINTS=true` dans le `.env`
  (sinon le garde-fou SSRF bloque l'endpoint privé).
- `verify_ssl: false` pour un certificat auto-signé (défaut : `true`).

## 5. NAS (dossier monté)

```json
{
  "root": "/mnt/nas/video-factory"
}
```

- Le dossier doit être **monté** sur le serveur (NFS, SMB, disque attaché…)
  avant d'être utilisable.
- Le healthcheck vérifie maintenant que le dossier est **accessible en écriture**.
- Aucun réseau : c'est un simple accès au système de fichiers local.

## 6. Supabase Storage

```json
{
  "url": "https://xyzcompany.supabase.co",
  "service_role_key": "eyJ…",
  "bucket": "assets"
}
```

- `service_role_key` : la clé **service_role** du projet (Settings → API), qui
  contourne les RLS côté serveur. Ne jamais l'exposer côté client.
- `bucket` : le nom du bucket Storage (à créer dans Supabase → Storage).

## 7. pCloud

```json
{
  "api_endpoint": "https://api.pcloud.com",
  "access_token": "…",
  "root": "/video-factory"
}
```

- `api_endpoint` : `https://api.pcloud.com` (US) ou `https://eapi.pcloud.com` (EU).
- `access_token` : un **token OAuth2** pCloud (obtenu via l'app pCloud ou l'API OAuth).
- `root` : dossier racine dans pCloud (créé automatiquement si absent).
- Les sous-dossiers sont créés automatiquement à l'upload.

---

## Le garde-fou SSRF (sécurité)

Par défaut, les endpoints qui pointent vers des **réseaux privés** (IP locale,
loopback, metadata…) sont **bloqués**. C'est voulu (protection SSRF).

- Pour **MinIO local** (endpoint privé), mettre `ALLOW_PRIVATE_STORAGE_ENDPOINTS=true`.
- Les endpoints publics (OVH, R2, B2, Supabase, pCloud) ne sont pas concernés.

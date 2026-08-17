# Spécification — Video Factory AI

> Usine vidéo multi-agents free-first produisant automatiquement des documentaires multilingues et des dessins animés pour enfants.

## Stack obligatoire

- **Next.js** : admin
- **FastAPI** : backend multi-agents
- **Supabase** : Postgres / Auth / RLS / Storage (optionnel)
- **Redis** : queues / verrous
- **Docker** : dev et deploy
- Pas de staging.

## Rôles MVP

- **Owner** : accès total, billing, secrets, suppression, publication finale, gestion des rôles.
- **Admin** : production, providers non critiques, storage, jobs, review opérationnelle, SEO.
- **Reviewer** : lecture, validation qualité, commentaires, demande de révision.

## Modules obligatoires

Provider Registry, Storage Registry, Master Orchestrator, Fallback Engine, Continuity Pack, Dry Run, Budget Forecast, Audit Trail, Licensing Agent, Pipeline documentaire, Pipeline cartoon, Localisation, Shorts, Montage final, SEO, sécurité OWASP ASVS.

## Étapes de développement (1→18)

### 1. Fondation repo et environnements
- Monorepo backend, frontend, infra, docs, tests.
- Docker dev et Docker deploy.
- CI dev et deploy.
- FastAPI, Next.js, Supabase et Redis connectés.
- **Validation** : backend healthcheck, frontend ouvert, DB migrée, Redis connecté.

### 2. Sécurité de base
- Supabase Auth + rôles Owner, Admin, Reviewer.
- RLS par workspace, rôle et action.
- RBAC backend, CORS strict, CSP, HSTS, rate limiting, payload limits.
- Chiffrement des clés API providers côté backend.
- Audit logs pour connexions, modifications sensibles et publications.
- **Validation** : accès refusé hors rôle, headers sécurité présents, secrets invisibles côté frontend.

### 3. Provider Registry admin
- CRUD providers : nom, rôle, API key, endpoint, quota, coût, priorité, statut.
- Langues, formats, limites, modèle, vitesse moyenne, qualité estimée.
- Healthcheck provider et test de clé API.
- Tracking quota consommé / restant.
- **Validation** : deux providers fake, désactiver le premier, vérifier que le second est choisi.

### 4. Storage Registry admin
- CRUD stockages : local, pCloud, Supabase Storage, S3-compatible, R2, B2, MinIO, NAS.
- Priorité, quota, coût, statut, région, réplication, healthcheck.
- Upload, download, signed URLs, checksums, suppression contrôlée.
- **Validation** : même asset sur deux backends, récupéré via interface commune.

### 5. Users et permissions MVP
- Owner / Admin / Reviewer avec écrans et actions dédiés.
- Confirmations fortes sur actions destructives Owner.
- **Validation** : chaque rôle voit seulement ses écrans et actions autorisées.

### 6. Job Planner et micro-tâches
- Sujet → série, épisodes, scènes, segments, tâches.
- Queues par type : script, audio, image, vidéo, montage, SEO, QA.
- Segments de 5–10 s ou blocs testables.
- Chaque tâche liée à un provider role et à un fallback.
- **Validation** : un sujet produit un plan de série complet et des tâches exécutables.

### 7. Dry Run et Budget Forecast
- Simulation avant consommation de providers coûteux.
- Estimation minutes vidéo, caractères TTS, traductions, stockage, GPU, coût, quotas.
- Détection des providers insuffisants.
- Risques : quota trop faible, stockage bas, provider instable, coût GPU probable.
- **Validation** : simulation série → rapport exploitable sans générer de vidéo.

### 8. Checkpoint Store
- Chaque sortie sauvegardée : texte, audio, image, clip, metadata, provider, prompt, coût, hash.
- Tâches idempotentes.
- Checkpoints liés au storage actif et à la scène.
- Version précédente conservée si régénération échoue.
- **Validation** : interrompre un job, relancer, reprendre au dernier checkpoint sans perte.

### 9. Continuity Pack
- Personnages, voix, style, palette, LUT, décors, SFX, musique, prompts, frames validées.
- Pack attaché à chaque série / épisode / scène / segment.
- Règles négatives (ce que le provider ne doit pas changer).
- QA automatisée comparant le résultat au pack.
- **Validation** : provider A commence, provider B reprend avec mêmes personnages, voix et style.

### 10. Pipeline documentaire MVP
- Recherche, fact-check, plan série, script épisode court, narration.
- Cold open, spot d'entrée, montée dramatique, teaser prochain épisode.
- Final spécial si dernier épisode.
- Sources et provenance dans Licensing Agent.
- **Validation** : teaser documentaire 60–120 s prêt à revoir.

### 11. Pipeline cartoon MVP
- Bible série, personnages, voix, décors, règles visuelles, tonalité enfant.
- Chanson d'entrée / sortie, thème musical, jingles, catchphrases.
- Nouvelle série = nouvel univers, nouveaux personnages, nouvelles voix.
- Multilingue dès le départ.
- **Validation** : scène cartoon courte cohérente (voix, style, musique stable).

### 12. Localisation multilingue
- Transcription, traduction, TTS/doublage, sous-titres SRT/VTT.
- Fallback DeepL, NLLB, LibreTranslate, Deepgram, WhisperX, HeyGen, Cartesia, VoiceStudio.
- Contrôle timing, langue, longueur phrases, synchronisation sous-titres.
- **Validation** : deux langues pour un même clip avec sous-titres propres.

### 13. Montage final automatique
- Assemblage segments, voix, musique, SFX, captions, transitions, chapitres, crédits.
- Exports long format 16:9, shorts 9:16, carré 1:1.
- Normalisation audio, vérification durée, encodage, résolution, sous-titres.
- **Validation** : fichier final lisible, durée attendue, audio normalisé, sous-titres synchronisés.

### 14. SEO et shorts
- SEO épisode : titre, description, tags, hashtags, chapitres, miniature, mots-clés.
- Shorts par plateforme : YouTube Shorts, TikTok, Facebook Reels (captions, CTA).
- Metadata JSON par plateforme.
- A/B testing titres, hooks, miniatures.
- **Validation** : package complet par plateforme.

### 15. Droits, licences et provenance
- Tracage sources, images, musiques, voix, vidéos, prompts, assets.
- Licence, origine, usage autorisé, date, lien source, fichier associé.
- Blocage publication si licence inconnue ou risquée.
- **Validation** : chaque export final possède un rapport de provenance complet.

### 16. QA, sécurité avancée et anti-abus
- OWASP ASVS, scan dépendances, SBOM, scan fichiers uploadés, SSRF guard.
- Défense prompt injection.
- Validation fichiers : MIME réel, taille, extension, signed URLs courtes.
- Backups, restauration testée, logs immuables, alertes anomalies.
- **Validation** : checklist sécurité passée, tests d'attaque de base documentés.

### 17. Publication et validation admin
- Écran review : vidéo, shorts, SEO, langues, sources, alertes QA.
- Approuver, demander révision, exporter manuel, publier.
- Historique de validation (utilisateur, date, version, commentaire).
- **Validation** : aucun contenu ne part sans validation explicite.

### 18. Monétisation et optimisation
- Scoring sujets : tendance, concurrence, RPM potentiel, langues, temps de production, risque de droits.
- Priorisation des séries selon potentiel business et coût.
- Analyse performance titres, miniatures, hooks, shorts, langues.
- **Validation** : dashboard priorise les séries les plus rentables.

## Règle de développement

Chaque fonctionnalité doit être **testée et démontrable** avant de passer à la suivante.

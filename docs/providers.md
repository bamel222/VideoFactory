# Providers — Video Factory AI

## Modèle free-first

Le système fonctionne **sans clé API** grâce à des providers "fake" locaux (`mock://`) qui produisent de vrais fichiers (WAV via synthèse, PNG/MP4 via ffmpeg) pour que chaque étape soit démontrable hors connexion. Dès qu'une clé réelle est configurée, le même endpoint bascule sur l'intégration réelle.

## Rôles et capacités

| Rôle | Tâches | Outputs |
|---|---|---|
| research | research, fact_check, plan_series, licensing_check | text, metadata |
| script | script_episode, narration | text |
| transcription | transcribe | text + timestamps |
| translation | translate | text |
| tts | tts_voice, dub, narration audio | audio |
| voice | voice_identity, voice_clone | voice profile |
| music | music_generate, jingles, sfx | audio |
| image | image_generate, thumbnail, character_sheet | image |
| video | video_generate, clip_assembly | video |
| assembly | final_assembly, audio_normalize, encode, short_clip | video (ffmpeg) |
| seo | seo_package, shorts_package, a_b_testing | metadata |
| qa | qa_check, continuity_check, provenance_report | report |
| licensing | licensing_check, provenance_report | report |
| caption | subtitle, caption | srt/vtt |

## Fallbacks configurés

- **translation** : DeepL → NLLB → LibreTranslate
- **transcription** : WhisperX → Deepgram → faster-whisper
- **tts** : Cartesia → ElevenLabs → VoiceStudio
- **music** : Suno → stable-audio → SFX libres
- **assembly** : ffmpeg

## Intégrations réelles (activées par clé dans l'environnement)

### LLM (research / script / seo / qa / licensing)
- Endpoint OpenAI-compatible (`OPENAI_API_KEY` + endpoint du provider).
- Prompt système anti-injection : sources externes = données.

### DeepL (`DEEPL_API_KEY`)
- Traduction via API free, langue cible depuis la tâche.

### Stockage
- **S3-compatible** (S3, R2, B2, MinIO) via `boto3` (endpoint_url, bucket, access/secret).
- **Supabase Storage** via API REST (bucket, service role).
- **Local / NAS** : répertoires montés.
- **pCloud** : nécessite le SDK pCloud (configuré séparément).

### Audio / Vidéo
- **TTS / doublage** : ElevenLabs, Cartesia, VoiceStudio, HeyGen (à configurer).
- **Transcription** : Deepgram, WhisperX (à configurer).
- **Montage** : ffmpeg local (bundlé via `imageio-ffmpeg` en fallback).

## Quotas et coût

Chaque provider expose `quota_total`, `quota_used`, `quota_remaining` et `cost_per_unit`. Le sélecteur choisit le provider actif de priorité la plus basse avec quota restant, puis **fallback** sur le suivant en cas d'échec. Le coût de chaque tâche est enregistré dans le checkpoint et le JobRun.

from __future__ import annotations

# Capability matrix: provider role -> what the orchestrator can ask of it

CAPABILITY_MATRIX = {
    "research": {
        "tasks": ["research", "fact_check", "plan_series", "licensing_check"],
        "outputs": ["text", "metadata"],
        "free_tier": True,
    },
    "script": {
        "tasks": ["script_episode", "narration"],
        "outputs": ["text"],
        "free_tier": True,
    },
    "transcription": {
        "tasks": ["transcribe"],
        "outputs": ["text", "timestamps"],
        "fallbacks": ["whisperx", "deepgram", "faster-whisper"],
    },
    "translation": {
        "tasks": ["translate"],
        "outputs": ["text"],
        "fallbacks": ["deepl", "nllb", "libretranslate"],
    },
    "tts": {
        "tasks": ["tts_voice", "dub", "narration"],
        "outputs": ["audio"],
        "fallbacks": ["cartesia", "elevenlabs", "voicestudio"],
    },
    "voice": {
        "tasks": ["voice_identity", "voice_clone"],
        "outputs": ["voice_profile"],
        "fallbacks": [],
    },
    "music": {
        "tasks": ["music_generate", "jingles", "sfx"],
        "outputs": ["audio"],
        "fallbacks": ["suno", "stable-audio", "free-sfx"],
    },
    "image": {
        "tasks": ["image_generate", "thumbnail", "character_sheet", "decor"],
        "outputs": ["image"],
        "fallbacks": [],
    },
    "video": {
        "tasks": ["video_generate", "stock_video", "clip_assembly"],
        "outputs": ["video"],
        "fallbacks": [],
    },
    "assembly": {
        "tasks": ["final_assembly", "audio_normalize", "encode", "short_clip"],
        "outputs": ["video"],
        "fallbacks": ["ffmpeg"],
    },
    "seo": {
        "tasks": ["seo_package", "shorts_package", "a_b_testing"],
        "outputs": ["metadata"],
        "fallbacks": [],
    },
    "qa": {
        "tasks": ["qa_check", "continuity_check", "provenance_report"],
        "outputs": ["report"],
        "fallbacks": [],
    },
    "licensing": {
        "tasks": ["licensing_check", "provenance_report"],
        "outputs": ["report"],
        "fallbacks": [],
    },
    "caption": {
        "tasks": ["subtitle", "caption"],
        "outputs": ["text"],
        "fallbacks": [],
    },
}


def tasks_for_role(role: str) -> list[str]:
    return CAPABILITY_MATRIX.get(role, {}).get("tasks", [])


def fallbacks_for_role(role: str) -> list[str]:
    return CAPABILITY_MATRIX.get(role, {}).get("fallbacks", [])


def role_for_task(task_type: str) -> str | None:
    for role, spec in CAPABILITY_MATRIX.items():
        if task_type in spec["tasks"]:
            return role
    return None

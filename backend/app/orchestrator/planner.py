from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ContinuityPack, Episode, JobRun, JobTask, Scene, Segment, Series

DOC_BEATS = [
    ("cold_open", "Accroche visuelle forte", 10),
    ("intro", "Introduction du sujet", 15),
    ("build", "Développement dramatique", 20),
    ("climax", "Point culminant / révélation", 15),
    ("teaser", "Teaser du prochain épisode", 10),
]

CARTOON_BEATS = [
    ("song_in", "Chanson d'entrée", 12),
    ("scene_1", "Scène principale 1", 18),
    ("scene_2", "Scène principale 2", 18),
    ("scene_3", "Scène principale 3", 18),
    ("song_out", "Chanson de sortie", 12),
]

# Segment duration (seconds) per generation mode.
# "images" -> stills long enough for Ken Burns; "video" -> short clips.
SEGMENT_DURATION_BY_MODE = {"images": 12, "video": 10}


def _beats_for(kind: str) -> list[tuple[str, str, int]]:
    return DOC_BEATS if kind == "documentary" else CARTOON_BEATS


def _scale_beats(kind: str, target_duration_seconds: int) -> list[tuple[str, str, int]]:
    beats = _beats_for(kind)
    total_weight = sum(d for _, _, d in beats)
    scaled: list[tuple[str, str, int]] = []
    for idx, (beat, title, weight) in enumerate(beats):
        dur = round(target_duration_seconds * weight / total_weight)
        if idx == len(beats) - 1:
            dur = max(1, target_duration_seconds - sum(d for _, _, d in scaled))
        scaled.append((beat, title, max(1, dur)))
    return scaled


def _build_scenes(db: Session, episode: Episode, kind: str, target_duration_seconds: int) -> list[Scene]:
    beats = _scale_beats(kind, target_duration_seconds)
    scenes: list[Scene] = []
    for idx, (beat, title, duration) in enumerate(beats):
        if beat == "teaser" and episode.is_final:
            title = "Final spécial : synthèse de la série"
        scene = Scene(
            episode_id=episode.id,
            order=idx,
            title=title,
            description=title,
            duration_seconds=duration,
            beat=beat,
        )
        db.add(scene)
        db.flush()
        scenes.append(scene)
    return scenes


def _build_segments(db: Session, scene: Scene, mode: str) -> list[Segment]:
    seg_dur = SEGMENT_DURATION_BY_MODE.get(mode, 8)
    segments: list[Segment] = []
    count = max(1, scene.duration_seconds // seg_dur)
    for i in range(count):
        seg = Segment(
            scene_id=scene.id,
            order=i,
            duration_seconds=seg_dur,
            content_type="visual",
            prompt=scene.description,
        )
        db.add(seg)
        db.flush()
        segments.append(seg)
    return segments


def generate_plan(db: Session, series: Series, language: str = "fr", extra_languages: list[str] | None = None) -> Series:
    """Build episodes, scenes, segments and the full task DAG for a series."""
    if not series.continuity_pack_id:
        pack = _create_continuity_pack(db, series)
        series.continuity_pack_id = pack.id

    mode = series.effective_mode()
    target_duration = max(24, series.duration_minutes or 26) * 60

    episodes = [ep for ep in series.episodes] if hasattr(series, "episodes") else []
    if not episodes:
        for n in range(1, series.planned_episodes + 1):
            ep = Episode(
                series_id=series.id,
                number=n,
                title=f"Épisode {n}",
                status="planned",
                is_final=(n == series.planned_episodes),
                target_duration_seconds=target_duration,
            )
            db.add(ep)
            db.flush()
            episodes.append(ep)

    targets = [language] + (extra_languages or [])
    seq = 0
    run = JobRun(series_id=series.id, kind="pipeline", status="pending")
    db.add(run)
    db.flush()
    for ep in episodes:
        scenes = _build_scenes(db, ep, series.kind, target_duration)
        for scene in scenes:
            _build_segments(db, scene, mode)
        seq = _plan_episode_tasks(db, series, run, ep, seq, targets, mode)
    run.total_tasks = seq
    db.commit()
    return series


def _add_task(
    db: Session, run: JobRun, series: Series, task_type: str, queue: str,
    episode_id: int | None, scene_id: int | None, segment_id: int | None,
    sequence: int, depends_on: list[int] | None = None, payload: dict | None = None,
) -> JobTask:
    t = JobTask(
        job_run_id=run.id,
        series_id=series.id,
        episode_id=episode_id,
        scene_id=scene_id,
        segment_id=segment_id,
        task_type=task_type,
        queue=queue,
        status="pending",
        payload=payload or {},
        depends_on=depends_on or [],
        sequence=sequence,
    )
    db.add(t)
    db.flush()
    return t


def _create_continuity_pack(db: Session, series: Series) -> ContinuityPack:
    if series.kind == "cartoon":
        pack = ContinuityPack(
            series_id=series.id,
            name=f"Pack continuité {series.title}",
            characters=[
                {"name": "Pipo le renard", "traits": "curieux, malin", "voice": "PipoVoice", "ref": ""},
                {"name": "Lina la pie", "traits": "espiègle, rapide", "voice": "LinaVoice", "ref": ""},
            ],
            voices=[{"name": "PipoVoice", "provider": "tts", "ref": ""}, {"name": "LinaVoice", "provider": "tts", "ref": ""}],
            style={"art": "2D", "palette": "chaud", "rendering": "simple, adapté enfants"},
            palette=["#f4a261", "#2a9d8f", "#e9c46a", "#264653"],
            lut="",
            decors=["forêt magique", "vallée des étoiles", "atelier de Pipo"],
            sfx=["pas dans les feuilles", "rire de Pipo", "cloche de Lina"],
            music={"song_in": "theme_ludique_120bpm", "song_out": "theme_fin_doux_90bpm"},
            prompts={"default": "style cartoon enfants, contours clairs, couleurs vives"},
            validated_frames=[],
            negative_rules=[
                "Ne pas changer l'apparence de Pipo",
                "Ne pas modifier la voix de Lina",
                "Interdire les scènes violentes ou effrayantes",
            ],
        )
    else:
        pack = ContinuityPack(
            series_id=series.id,
            name=f"Pack documentaire {series.title}",
            characters=[],
            voices=[{"name": "Narrateur", "provider": "tts", "ref": ""}],
            style={"art": "documentaire", "ton": "sobre et sourcé", "rendering": "images réelles ou 3D sobre"},
            palette=["#1d3557", "#457b9d", "#a8dadc", "#f1faee"],
            lut="rec709",
            decors=["plateau", "illustrations de synthèse", "images d'archives sourcées"],
            sfx=["ambiance terrain", "transitions douces"],
            music={"theme": "ambient_calme"},
            prompts={"default": "documentaire factuel, sourcé, aucune invention"},
            validated_frames=[],
            negative_rules=[
                "Ne pas inventer de faits",
                "Toujours citer la source",
                "Interdire les images non sourcées",
            ],
        )
    db.add(pack)
    db.flush()
    return pack


def _plan_episode_tasks(db: Session, series: Series, run: JobRun, ep: Episode, seq: int, targets: list[str], mode: str) -> int:
    pending: list[JobTask] = []
    scene_ids = [s.id for s in db.query(Scene).filter(Scene.episode_id == ep.id).order_by(Scene.order).all()]
    segment_ids = [
        s.id for s in db.query(Segment).filter(Segment.scene_id.in_(scene_ids)).order_by(Segment.id).all()
    ]

    # Script / bible per episode
    if series.kind == "documentary":
        research = _add_task(db, run, series, "research", "research", ep.id, None, None, seq)
        seq += 1
        if series.fact_check_enabled:
            fact_check = _add_task(db, run, series, "fact_check", "qa", ep.id, None, None, seq, [research.id])
            seq += 1
            script_dep = fact_check.id
        else:
            script_dep = research.id
        script = _add_task(db, run, series, "script_episode", "script", ep.id, None, None, seq, [script_dep])
        seq += 1
        narration = _add_task(db, run, series, "narration", "script", ep.id, None, None, seq, [script.id])
        seq += 1
        # Main-language voiceover: narration text -> TTS audio
        narration_tts = _add_task(db, run, series, "tts_voice", "audio", ep.id, None, None, seq, [narration.id],
                                  {"subtype": "narration", "language": series.language})
        seq += 1
        pending = [research, script, narration, narration_tts]
    else:
        bible = _add_task(db, run, series, "plan_series", "research", ep.id, None, None, seq)
        seq += 1
        fact_dep = [bible.id]
        if series.fact_check_enabled:
            fact_check = _add_task(db, run, series, "fact_check", "qa", ep.id, None, None, seq, [bible.id])
            seq += 1
            fact_dep.append(fact_check.id)
        char_sheet = _add_task(db, run, series, "image_generate", "image", ep.id, None, None, seq, [bible.id], {"subtype": "character_sheet"})
        seq += 1
        voice = _add_task(db, run, series, "tts_voice", "audio", ep.id, None, None, seq, [bible.id], {"subtype": "voice_identity"})
        seq += 1
        song_in = _add_task(db, run, series, "music_generate", "audio", ep.id, None, None, seq, [bible.id], {"subtype": "song_in"})
        seq += 1
        song_out = _add_task(db, run, series, "music_generate", "audio", ep.id, None, None, seq, [bible.id], {"subtype": "song_out"})
        seq += 1
        pending = [bible, char_sheet, voice, song_in, song_out]

    # Per-segment media generation, chosen by (kind, mode)
    if series.kind == "cartoon":
        media_task_type = "video_generate" if mode == "video" else "image_generate"
        media_role = "video" if mode == "video" else "image"
    else:
        media_task_type = "stock_video" if mode == "video" else "image_generate"
        media_role = "video" if mode == "video" else "image"

    for sid in segment_ids:
        seg = db.get(Segment, sid)
        media = _add_task(db, run, series, media_task_type, media_role, ep.id, seg.scene_id, sid, seq, [pending[-1].id],
                          {"mode": mode, "prompt": seg.prompt})
        seq += 1
        pending.append(media)

    clip = _add_task(db, run, series, "clip_assembly", "montage", ep.id, None, None, seq,
                     [t.id for t in pending if t.task_type in ("image_generate", "video_generate", "stock_video")],
                     {"mode": mode})
    seq += 1
    subtitles = _add_task(db, run, series, "subtitle", "script", ep.id, None, None, seq, [clip.id], {"language": series.language})
    seq += 1
    final = _add_task(db, run, series, "final_assembly", "montage", ep.id, None, None, seq, [clip.id, subtitles.id], {"mode": mode})
    seq += 1

    # Localization per target language
    for lang in targets:
        ref = narration.id if series.kind == "documentary" else bible.id
        tr = _add_task(db, run, series, "translate", "translation", ep.id, None, None, seq, [ref], {"language": lang})
        seq += 1
        dub = _add_task(db, run, series, "tts_voice", "audio", ep.id, None, None, seq, [tr.id], {"language": lang, "subtype": "dub"})
        seq += 1
        sub = _add_task(db, run, series, "subtitle", "script", ep.id, None, None, seq, [tr.id, dub.id], {"language": lang})
        seq += 1

    seo = _add_task(db, run, series, "seo_package", "seo", ep.id, None, None, seq, [final.id, subtitles.id])
    seq += 1
    shorts = _add_task(db, run, series, "shorts_package", "seo", ep.id, None, None, seq, [seo.id])
    seq += 1
    qa = _add_task(db, run, series, "qa_check", "qa", ep.id, None, None, seq, [final.id, seo.id, shorts.id])
    seq += 1

    pack = db.get(ContinuityPack, series.continuity_pack_id) if series.continuity_pack_id else None
    cont = _add_task(db, run, series, "continuity_check", "qa", ep.id, None, None, seq, [final.id, qa.id],
                     {"pack": {"name": pack.name if pack else "", "negative_rules": pack.negative_rules if pack else []}})
    seq += 1

    lic = _add_task(db, run, series, "licensing_check", "licensing", ep.id, None, None, seq, [final.id])
    seq += 1
    prov = _add_task(db, run, series, "provenance_report", "licensing", ep.id, None, None, seq, [lic.id, qa.id, cont.id])
    seq += 1

    return seq

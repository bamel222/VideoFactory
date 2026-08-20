from __future__ import annotations

import os
import tempfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.ffmpeg_utils import ffmpeg_binary, probe_duration, run_ffmpeg
from app.core.config import get_settings
from app.models import Checkpoint, JobTask

settings = get_settings()
MEDIA_ROOT = os.path.join(settings.data_dir, "media")
STORAGE_ROOT = os.path.join(settings.data_dir, "storage")

SIZE = "1920x1080"
FPS = 24
MEDIA_TASK_TYPES = ("image_generate", "video_generate", "stock_video")
NARRATION_TASK_TYPES = ("tts_voice",)
MUSIC_TASK_TYPES = ("music_generate",)


def _resolve_path(cp: Checkpoint) -> str | None:
    local = (cp.metadata_json or {}).get("local_path")
    if local and os.path.exists(local):
        return local
    ref = cp.content_ref or ""
    if not ref:
        return None
    candidates = [
        ref,
        os.path.join(MEDIA_ROOT, ref),
        os.path.join(STORAGE_ROOT, ref),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _task_output(db: Session, episode_id: int, task_type: str) -> str | None:
    cp = (
        db.query(Checkpoint)
        .join(JobTask, Checkpoint.task_id == JobTask.id)
        .filter(JobTask.episode_id == episode_id, JobTask.task_type == task_type, Checkpoint.valid == True)  # noqa: E712
        .order_by(Checkpoint.id.desc())
        .first()
    )
    return _resolve_path(cp) if cp else None


def collect_episode_media(db: Session, episode_id: int, mode: str) -> dict:
    """Gather all produced media files for an episode, in task order."""
    tasks = (
        db.query(JobTask)
        .filter(JobTask.episode_id == episode_id)
        .order_by(JobTask.sequence.asc())
        .all()
    )
    by_type: dict[str, list] = {"image": [], "video": [], "narration": [], "music": [], "subtitle": []}
    for t in tasks:
        if not t.checkpoint_id:
            continue
        cp = db.get(Checkpoint, t.checkpoint_id)
        if not cp or not cp.valid:
            continue
        path = _resolve_path(cp)
        if not path:
            continue
        if t.task_type in ("image_generate",):
            by_type["image"].append(path)
        elif t.task_type in ("video_generate", "stock_video"):
            by_type["video"].append(path)
        elif t.task_type in NARRATION_TASK_TYPES:
            by_type["narration"].append(path)
        elif t.task_type in MUSIC_TASK_TYPES:
            by_type["music"].append(path)
        elif t.task_type == "subtitle":
            by_type["subtitle"].append(path)
    return {
        "images": by_type["image"],
        "clips": by_type["video"],
        "narration": by_type["narration"],
        "music": by_type["music"],
        "subtitles": by_type["subtitle"],
        "raw": _task_output(db, episode_id, "clip_assembly"),
    }


def _kenburns_clip(image: str, out: str, dur: float, size: str, fps: int, idx: int) -> None:
    frames = max(1, int(dur * fps))
    if idx % 2 == 0:
        zexpr = f"min(1+0.25*on/{frames},1.3)"
    else:
        zexpr = f"max(1.3-0.25*on/{frames},1.0)"
    xexpr = "iw/2-(iw/zoom/2)"
    yexpr = "ih/2-(ih/zoom/2)"
    w, h = size.split("x")
    run_ffmpeg(
        [
            "-y", "-loop", "1", "-framerate", str(fps), "-t", f"{dur}",
            "-i", image,
            "-vf", (
                f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},"
                f"zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}':d=1:s={size}:fps={fps},"
                "setsar=1"
            ),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27",
            "-pix_fmt", "yuv420p", "-t", f"{dur}", out,
        ],
        timeout=600,
    )


def build_slideshow(images: list[str], out: str, dur_each: float, size: str = SIZE, fps: int = FPS) -> str:
    """Assemble still images into a video using a Ken Burns effect."""
    if not images:
        raise RuntimeError("No images available for the slideshow")
    clips: list[str] = []
    tmpdir = tempfile.mkdtemp(prefix="vf_slides_")
    try:
        for i, img in enumerate(images):
            clip = os.path.join(tmpdir, f"clip_{i:04d}.mp4")
            _kenburns_clip(img, clip, dur_each, size, fps, i)
            clips.append(clip)
        with open(os.path.join(tmpdir, "list.txt"), "w") as f:
            for c in clips:
                f.write(f"file '{c}'\n")
        run_ffmpeg(
            ["-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmpdir, "list.txt"),
             "-c", "copy", out],
            timeout=900,
        )
    finally:
        for c in clips:
            if os.path.exists(c):
                os.remove(c)
    return out


def concat_videos(clips: list[str], out: str, size: str = SIZE, fps: int = FPS) -> str:
    """Concatenate video clips (normalized to a common size) into a single video."""
    if not clips:
        raise RuntimeError("No video clips available for assembly")
    w, h = size.split("x")
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", c]
    filter_chain: list[str] = []
    for i in range(len(clips)):
        filter_chain.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}[v{i}]"
        )
    filter_chain.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[vout]")
    run_ffmpeg(
        ["-y", *inputs,
         "-filter_complex", ";".join(filter_chain),
         "-map", "[vout]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
         "-pix_fmt", "yuv420p", out],
        timeout=1800,
    )
    return out


def _escape_subtitles(path: str) -> str:
    return (
        path.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
    )


def mix_audio(
    visual: str,
    narration_paths: list[str],
    music_paths: list[str],
    srt_path: str | None,
    out: str,
    burn_subs: bool = True,
) -> str:
    """Mix narration + music over the visual track and optionally burn subtitles.

    Narration is padded to the full video length and music loops, so the final
    audio always matches the visual duration (no silent tail when the narration
    is shorter than the video).
    """
    inputs = ["-y", "-i", visual]
    for n in narration_paths:
        inputs += ["-i", n]
    for m in music_paths:
        inputs += ["-stream_loop", "-1", "-i", m]

    filters: list[str] = []
    labels: list[str] = []

    # Narration inputs (indices 1..N): pad to full length, full volume.
    idx = 1
    for _ in narration_paths:
        label = f"a{idx - 1}"
        filters.append(f"[{idx}:a]apad,volume=1.0[{label}]")
        labels.append(label)
        idx += 1

    # Music inputs (indices N+1..): looped, low volume.
    for _ in music_paths:
        label = f"a{idx - 1}"
        filters.append(f"[{idx}:a]volume=0.18[{label}]")
        labels.append(label)
        idx += 1

    # Visual: burn subtitles or pass through.
    if burn_subs and srt_path and os.path.exists(srt_path):
        filters.append(f"[0:v]subtitles='{_escape_subtitles(srt_path)}'[vsub]")
        vlabel = "vsub"
    else:
        filters.append("[0:v]null[vnull]")
        vlabel = "vnull"

    # Mix all audio tracks at the longest duration; -shortest caps to the video.
    if labels:
        amix_inputs = "".join(f"[{l}]" for l in labels)
        filters.append(
            f"{amix_inputs}amix=inputs={len(labels)}:duration=longest:normalize=0[amix]"
        )

    cmd = ["-y", *inputs, "-filter_complex", ";".join(filters)]
    cmd += ["-map", f"[{vlabel}]"]
    if labels:
        cmd += ["-map", "[amix]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-pix_fmt", "yuv420p"]

    # Cap the output to the visual duration (narration is padded, music loops).
    duration = probe_duration(visual)
    if duration > 0:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += [out]

    run_ffmpeg(cmd, timeout=1800)
    return out


def build_episode_video(db: Session, episode_id: int, mode: str, raw_out: str, final_out: str, burn_subs: bool = True) -> tuple[str, str]:
    """Full local montage for an episode: visuals (slideshow or clips) then audio+subtitles."""
    media = collect_episode_media(db, episode_id, mode)
    if mode == "images":
        build_slideshow(media["images"], raw_out, dur_each=12.0)
    else:
        concat_videos(media["clips"], raw_out)
    mix_audio(
        raw_out,
        media["narration"],
        media["music"],
        media["subtitles"][0] if media["subtitles"] else None,
        final_out,
        burn_subs=burn_subs,
    )
    return raw_out, final_out

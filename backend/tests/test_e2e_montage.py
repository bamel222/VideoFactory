from __future__ import annotations

import os
import tempfile

import pytest

from app.agents import montage
from app.agents.ffmpeg_utils import ffmpeg_available, generate_image_png, generate_tone_wav, probe_duration
from app.agents.provider_client import MockProviderClient, settings as client_settings
from app.core.db import SessionLocal
from app.models import Checkpoint, Episode, JobRun, JobTask, Provider, Series, Workspace

pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg indisponible")


@pytest.fixture
def db():
    db = SessionLocal()
    yield db
    db.close()


def _mk_task(db, run, series, ep, task_type, sequence, payload=None):
    t = JobTask(
        job_run_id=run.id, series_id=series.id, episode_id=ep.id, task_type=task_type,
        queue="montage", status="pending", payload=payload or {}, sequence=sequence,
    )
    db.add(t)
    db.flush()
    return t


def _checkpoint(db, task, kind, path, provider_name="mock://montage"):
    cps = Checkpoint(
        task_id=task.id, series_id=task.series_id, scene_id=task.scene_id, kind=kind,
        content_ref=path, provider=provider_name, prompt="", cost=0.0,
        metadata_json={"task_type": task.task_type, "local_path": path}, valid=True, hash="h",
    )
    db.add(cps)
    db.flush()
    task.checkpoint_id = cps.id
    db.commit()
    return cps


def test_build_episode_video_full(monkeypatch, client):
    monkeypatch.setattr(client_settings, "montage_enabled", True)
    db = SessionLocal()
    tmp = tempfile.mkdtemp(prefix="vf_e2e_")
    try:
        ws = Workspace(name="E2E WS", owner_id=1)
        db.add(ws)
        db.flush()
        series = Series(title="E2E Full", topic="test", kind="documentary", language="fr",
                        generation_mode="images", duration_minutes=24, fact_check_enabled=True,
                        workspace_id=ws.id)
        db.add(series)
        db.flush()
        ep = Episode(series_id=series.id, number=1, title="Ép 1", status="planned", is_final=True,
                     target_duration_seconds=36)
        db.add(ep)
        db.flush()
        run = JobRun(series_id=series.id, kind="pipeline", status="running")
        db.add(run)
        db.flush()
        prov = Provider(name="mock", role="montage", endpoint="mock://montage", cost_per_unit=0.0, workspace_id=ws.id)
        db.add(prov)
        db.flush()

        seq = 0
        for i in range(3):
            p = os.path.join(tmp, f"img_{i}.png")
            generate_image_png(p, color=f"0x{0x334455 + i * 0x112233:06x}")
            t = _mk_task(db, run, series, ep, "image_generate", seq, {"mode": "images", "prompt": f"seg {i}"})
            seq += 1
            _checkpoint(db, t, "image", p)

        nar = os.path.join(tmp, "narration.wav")
        generate_tone_wav(nar, 6.0)
        t = _mk_task(db, run, series, ep, "tts_voice", seq, {"subtype": "narration"})
        seq += 1
        _checkpoint(db, t, "audio", nar)

        music = os.path.join(tmp, "music.wav")
        generate_tone_wav(music, 6.0, freq=330)
        t = _mk_task(db, run, series, ep, "music_generate", seq, {"subtype": "theme"})
        seq += 1
        _checkpoint(db, t, "audio", music)

        client = MockProviderClient(prov, db)
        raw_out = os.path.join(tmp, "episode_raw.mp4")
        final_out = os.path.join(tmp, "episode_final.mp4")
        montage.build_episode_video(db, ep.id, "images", raw_out, final_out, burn_subs=False)

        assert os.path.exists(raw_out) and os.path.exists(final_out)
        raw_dur = probe_duration(raw_out)
        final_dur = probe_duration(final_out)
        # 3 segments × 12 s
        assert 30 <= raw_dur <= 40, f"durée raw inattendue: {raw_dur}"
        # la narration (6 s) est plus courte que la vidéo (36 s) : la vidéo garde sa durée
        assert 30 <= final_dur <= 40, f"durée final inattendue: {final_dur}"
    finally:
        db.close()

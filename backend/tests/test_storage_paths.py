from __future__ import annotations

from app.agents.base import _slugify, _storage_path
from app.models import JobTask, Series


def test_slugify():
    assert _slugify("L'histoire des océans") == "l-histoire-des-oceans"
    assert _slugify("  Pipo & Lina !  ") == "pipo-lina"
    assert _slugify("") == "serie"
    assert _slugify("ÄÖÜ") == "aou"


def test_storage_path_final_and_short():
    series = Series(title="L'histoire des océans", topic="")
    final_task = JobTask(task_type="final_assembly", episode_id=3, series_id=series.id)
    short_task = JobTask(task_type="shorts_package", episode_id=3, series_id=series.id)
    inter_task = JobTask(task_type="image_generate", episode_id=3, series_id=series.id)

    # final/short use the human-readable path (episode number resolved from DB,
    # so here it falls back to the episode id when no DB row exists).
    assert _storage_path(None, final_task, series, "episode_3_final.mp4").endswith("/final.mp4")
    assert _storage_path(None, short_task, series, "episode_3_short.mp4").endswith("/short.mp4")
    assert _storage_path(None, final_task, series, "x.mp4").startswith("series/l-histoire-des-oceans/episode_3/")

    # intermediate files go under a 'working' prefix
    p = _storage_path(None, inter_task, series, "img_1_frame.png")
    assert "/working/task_" in p

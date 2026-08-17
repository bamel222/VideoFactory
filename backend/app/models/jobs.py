from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

QUEUES = ("script", "audio", "image", "video", "montage", "seo", "qa", "research", "translation", "licensing")
TASK_STATUSES = ("pending", "queued", "running", "succeeded", "failed", "skipped", "retry")

TASK_TYPES = (
    "research", "fact_check", "plan_series", "script_episode", "narration",
    "tts_voice", "music_generate", "image_generate", "video_generate", "clip_assembly",
    "transcribe", "translate", "dub", "subtitle", "caption",
    "final_assembly", "audio_normalize", "encode",
    "seo_package", "shorts_package", "thumbnail",
    "qa_check", "continuity_check", "licensing_check", "provenance_report",
)


class JobTask(Base, TimestampMixin):
    __tablename__ = "job_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), index=True, nullable=False)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True, nullable=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"), index=True, nullable=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), index=True, nullable=True)
    task_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    queue: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(String(2000), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=True)
    checkpoint_id: Mapped[int] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)  # task ids
    sequence: Mapped[int] = mapped_column(Integer, default=0)


class JobRun(Base, TimestampMixin):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), default="pipeline")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|failed|interrupted
    dry_run: Mapped[bool] = mapped_column(default=False, nullable=False)
    error: Mapped[str] = mapped_column(String(2000), default="")
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    done_tasks: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)


class Checkpoint(Base, TimestampMixin):
    __tablename__ = "checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("job_tasks.id"), index=True, nullable=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(30), default="text")  # text|audio|image|clip|metadata
    content_ref: Mapped[str] = mapped_column(String(1000), default="")
    provider: Mapped[str] = mapped_column(String(255), default="")
    prompt: Mapped[str] = mapped_column(default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    hash: Mapped[str] = mapped_column(String(128), default="")
    storage_id: Mapped[int] = mapped_column(ForeignKey("storage_backends.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    previous_id: Mapped[int] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)
    valid: Mapped[bool] = mapped_column(default=True, nullable=False)

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_secret
from app.notifications.emailer import send_email
from app.notifications.webhooks import send_discord, send_telegram

logger = logging.getLogger("video_factory.notifications")

settings = get_settings()


def _safe(fn, *args, **kwargs) -> None:
    """Run a delivery in fire-and-forget mode: failures never propagate."""
    try:
        fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("notification delivery failed: %s", exc)


def _app_series_url(series) -> str:
    base = (settings.app_base_url or "").rstrip("/")
    return f"{base}/dashboard/series/{series.id}" if base else ""


def _episode_download_url(db: Session, episode) -> str | None:
    """Best-effort signed URL to the episode's final video asset (None if unavailable)."""
    try:
        from app.models import Asset, Checkpoint, JobTask
        from app.registries.storage_registry import StorageRegistry

        task = db.scalar(
            select(JobTask)
            .where(JobTask.episode_id == episode.id, JobTask.task_type == "final_assembly", JobTask.status == "succeeded")
            .order_by(JobTask.id.desc())
        )
        if not task or not task.checkpoint_id:
            return None
        cp = db.get(Checkpoint, task.checkpoint_id)
        if not cp or not cp.content_ref:
            return None
        asset = db.scalar(select(Asset).where(Asset.path == cp.content_ref).order_by(Asset.id.desc()))
        if not asset:
            return None
        return StorageRegistry(db, asset.workspace_id).signed_url_for(asset)
    except Exception:  # noqa: BLE001
        return None


def _recipient_emails(user) -> list[str]:
    """Account email + optional secondary notification email, deduplicated."""
    if not user:
        return []
    seen = []
    for addr in (user.email, getattr(user, "notification_email", "") or ""):
        addr = (addr or "").strip().lower()
        if addr and addr not in seen:
            seen.append(addr)
    return seen


def _send_all(db: Session, user, series, subject: str, body: str) -> None:
    """Dispatch a message to every channel enabled on the series (0..3 channels)."""
    if series.notify_email:
        for addr in _recipient_emails(user):
            _safe(send_email, addr, subject, body)

    if series.notify_discord:
        webhook = decrypt_secret(user.discord_webhook_url_encrypted) if user else ""
        if webhook:
            _safe(send_discord, webhook, body)

    if series.notify_telegram:
        token = decrypt_secret(user.telegram_bot_token_encrypted) if user else ""
        chat_id = decrypt_secret(user.telegram_chat_id_encrypted) if user else ""
        if token and chat_id:
            _safe(send_telegram, token, chat_id, body)


def _episode_shorts_platforms(db: Session, episode) -> list[str]:
    """Platforms for which a short was produced for this episode (empty if none)."""
    try:
        from app.models import ShortsPackage

        return sorted({
            s.platform for s in db.scalars(
                select(ShortsPackage).where(ShortsPackage.episode_id == episode.id)
            ).all()
            if s.platform
        })
    except Exception:  # noqa: BLE001
        return []


def notify_episode(db: Session, user, series, episode, ok: bool) -> None:
    subject = f"Épisode {episode.number} {'prêt' if ok else 'en échec'} — {series.title}"
    lines = [
        f"🎬 {subject}",
        f"Épisode {episode.number} : {episode.title or f'Épisode {episode.number}'}",
        f"Statut : {'✅ généré avec succès' if ok else '❌ échec de génération'}",
    ]
    if ok:
        dl = _episode_download_url(db, episode)
        if dl:
            lines.append(f"Télécharger : {dl}")
        platforms = _episode_shorts_platforms(db, episode)
        if platforms:
            lines.append(f"Shorts prêts : {', '.join(platforms)}")
    url = _app_series_url(series)
    if url:
        lines.append(f"Voir : {url}")
    _send_all(db, user, series, subject, "\n".join(lines))


def notify_series_complete(db: Session, user, series, results: list) -> None:
    """`results` is a list of (episode, ok) tuples."""
    ok_count = sum(1 for _, ok in results if ok)
    fail_count = len(results) - ok_count
    subject = f"Série « {series.title} » : {ok_count}/{len(results)} épisodes générés"
    lines = [
        f"🏁 {subject}",
        "Les épisodes sont maintenant disponibles et prêts à être téléchargés ou publiés sur YouTube.",
        "",
        "Récapitulatif :",
    ]
    for ep, ok in results:
        state = "✅ réussi" if ok else "❌ échoué"
        line = f"  {state} — Épisode {ep.number} : {ep.title or f'Épisode {ep.number}'}"
        lines.append(line)
        if ok:
            dl = _episode_download_url(db, ep)
            if dl:
                lines.append(f"     Télécharger : {dl}")
    url = _app_series_url(series)
    if url:
        lines.append("")
        lines.append(f"Voir / publier : {url}")
    _send_all(db, user, series, subject, "\n".join(lines))


def notify_pipeline_outcome(db: Session, user, series, tasks: list) -> None:
    """After a pipeline run, send per-episode notifications then the series recap."""
    from app.models import Episode

    episodes = db.scalars(select(Episode).where(Episode.series_id == series.id).order_by(Episode.number)).all()
    if not episodes:
        return
    results: list = []
    for ep in episodes:
        ep_tasks = [t for t in tasks if t.episode_id == ep.id]
        ok = all(t.status == "succeeded" for t in ep_tasks) if ep_tasks else True
        results.append((ep, ok))
    for ep, ok in results:
        notify_episode(db, user, series, ep, ok)
    notify_series_complete(db, user, series, results)

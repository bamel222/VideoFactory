from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Episode,
    LicenceRecord,
    SEOPackage,
    ShortsPackage,
)


def persist_task_result(db: Session, task) -> None:
    """Write task outputs into the domain tables (episode, seo, shorts, licences)."""
    result = task.result or {}
    if not isinstance(result, dict):
        return

    episode = db.get(Episode, task.episode_id) if task.episode_id else None

    if task.task_type == "script_episode" and episode:
        episode.script = result.get("content") or episode.script

    if task.task_type == "narration" and episode:
        episode.narration = result.get("content") or episode.narration

    if task.task_type == "research":
        for src in result.get("sources", []):
            exists = db.query(LicenceRecord).filter(
                LicenceRecord.asset_ref == src.get("url", ""),
                LicenceRecord.series_id == task.series_id,
            ).first()
            if exists:
                continue
            db.add(LicenceRecord(
                series_id=task.series_id,
                asset_ref=src.get("url", ""),
                kind="source",
                origin=src.get("title", ""),
                license=src.get("license", "unknown"),
                usage="narration/documentaire",
                source_url=src.get("url", ""),
                risk="ok" if src.get("license") in ("CC-BY-4.0", "public-domain", "CC0", "MIT") else "block",
            ))

    if task.task_type == "licensing_check":
        blocked = result.get("blocked", False)
        licenses = result.get("licenses", [])
        unknown = [l for l in licenses if l not in ("CC-BY-4.0", "public-domain", "CC0", "MIT")]
        db.add(LicenceRecord(
            series_id=task.series_id,
            asset_ref="licensing-report",
            kind="report",
            origin="Licensing Agent",
            license=",".join(licenses) if licenses else "unknown",
            usage="publication",
            source_url="",
            risk="block" if blocked or unknown else "ok",
        ))

    if task.task_type == "seo_package" and episode:
        existing = db.query(SEOPackage).filter(SEOPackage.episode_id == episode.id).first()
        if existing is None:
            db.add(SEOPackage(
                episode_id=episode.id,
                language=(task.payload or {}).get("language", "fr"),
                title=result.get("title", ""),
                description=result.get("description", ""),
                tags=result.get("tags", []),
                hashtags=result.get("hashtags", []),
                chapters=result.get("chapters", []),
                thumbnail=result.get("thumbnail", ""),
                keywords=result.get("keywords", []),
                metadata_json=__import__("json").dumps(result),
            ))

    if task.task_type == "shorts_package" and episode:
        for platform, data in (result.get("platforms") or {}).items():
            db.add(ShortsPackage(
                episode_id=episode.id,
                platform=platform,
                captions=data.get("captions", ""),
                cta=data.get("cta", ""),
                metadata_json=__import__("json").dumps(data.get("metadata", {})),
                asset_path=data.get("asset_path", ""),
            ))

    db.commit()

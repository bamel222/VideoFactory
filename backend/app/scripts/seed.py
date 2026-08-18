from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select

from app.core.db import SessionLocal, init_db
from app.core.security import hash_password
from app.models import PasswordHistory, User, Workspace
from app.registries.provider_registry import seed_fake_providers
from app.registries.storage_registry import StorageRegistry


def run() -> None:
    init_db()
    db = SessionLocal()
    count = db.scalar(select(func.count(User.id)))
    if count:
        print("Already seeded. Nothing to do.")
        return

    ws = Workspace(name="Video Factory AI")
    db.add(ws)
    db.flush()

    now = dt.datetime.now(dt.timezone.utc)
    owner = User(email="owner@vf.ai", name="Owner", hashed_password=hash_password("password123"), role="owner", workspace_id=ws.id, password_changed_at=now)
    admin = User(email="admin@vf.ai", name="Admin", hashed_password=hash_password("password123"), role="admin", workspace_id=ws.id, password_changed_at=now)
    reviewer = User(email="reviewer@vf.ai", name="Reviewer", hashed_password=hash_password("password123"), role="reviewer", workspace_id=ws.id, password_changed_at=now)
    db.add_all([owner, admin, reviewer])
    db.flush()
    for u in (owner, admin, reviewer):
        db.add(PasswordHistory(user_id=u.id, hashed_password=u.hashed_password))
    ws.owner_id = owner.id

    seed_fake_providers(db, ws.id)
    StorageRegistry(db, ws.id).create_default_local()
    db.commit()

    print("Seed done. Accounts:")
    print("  owner@vf.ai / password123 (Owner)")
    print("  admin@vf.ai / password123 (Admin)")
    print("  reviewer@vf.ai / password123 (Reviewer)")


if __name__ == "__main__":
    run()

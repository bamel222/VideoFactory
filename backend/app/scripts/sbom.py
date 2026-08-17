from __future__ import annotations

"""Generate a minimal SBOM (SPDX-ish) from backend requirements and frontend lockfile."""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def pypi_packages() -> list[dict]:
    out = []
    req_file = os.path.join(ROOT, "backend", "requirements.txt")
    if not os.path.exists(req_file):
        return out
    for line in open(req_file, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split("==")[0].split(">=")[0].split("<")[0].strip()
        version = ""
        if "==" in line:
            version = line.split("==")[1].strip()
        out.append({"name": name, "version": version, "packageManager": "pip"})
    return out


def npm_packages() -> list[dict]:
    out = []
    lock = os.path.join(ROOT, "frontend", "package-lock.json")
    if not os.path.exists(lock):
        return out
    data = json.load(open(lock, encoding="utf-8"))
    for name, info in (data.get("packages") or {}).items():
        if name and info.get("version"):
            out.append({"name": name.lstrip("node_modules/"), "version": info["version"], "packageManager": "npm"})
    return out


def main() -> None:
    packages = pypi_packages() + npm_packages()
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "name": "video-factory-ai-sbom",
        "documentNamespace": f"https://video-factory.ai/sbom/{hashlib.sha1(str(dt.datetime.now()).encode()).hexdigest()}",
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "creator": ["tool: video-factory-sbom"],
        "packages": packages,
    }
    path = os.path.join(ROOT, "docs", "sbom.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2)
    print(f"SBOM écrit: {path} ({len(packages)} packages)")


if __name__ == "__main__":
    main()

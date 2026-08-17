from __future__ import annotations

import os
import shutil
import subprocess
import wave

FFMPEG_CANDIDATES = [
    shutil.which("ffmpeg"),
    "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2",
    "/usr/lib/python3/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2",
]


def ffmpeg_binary() -> str:
    for candidate in FFMPEG_CANDIDATES:
        if candidate and os.path.exists(candidate):
            return candidate
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("ffmpeg binary not found")


def ffmpeg_available() -> bool:
    try:
        ffmpeg_binary()
        return True
    except Exception:
        return False


def run_ffmpeg(args: list[str], timeout: int = 120) -> None:
    binary = ffmpeg_binary()
    cmd = [binary, "-y", *args]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        stderr = (result.stderr or b"").decode(errors="replace")[-3000:]
        raise RuntimeError(f"ffmpeg failed (rc={result.returncode}): {stderr}")


def generate_tone_wav(path: str, duration_s: float, freq: float = 440.0, sample_rate: int = 44100) -> str:
    """Generate a real sine-wave WAV file (pure python)."""
    import math
    import struct

    os.makedirs(os.path.dirname(path), exist_ok=True)
    frames = int(duration_s * sample_rate)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for i in range(frames):
            val = int(0.6 * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            w.writeframesraw(struct.pack("<h", val))
    return path


def generate_image_png(path: str, color: str = "navy", size: str = "640x360") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    run_ffmpeg(
        ["-f", "lavfi", "-i", f"color=c={color}:s={size}:d=0.1",
         "-frames:v", "1", "-y", path]
    )
    return path


def generate_test_video(path: str, duration_s: float, size: str = "640x360", color: str = "0x2b4c7e") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    run_ffmpeg(
        ["-f", "lavfi", "-i", f"color=c={color}:s={size}:r=24:d={duration_s}",
         "-f", "lavfi", "-i", f"sine=frequency=330:duration={duration_s}",
         "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", path]
    )
    return path


def probe_duration(path: str) -> float:
    import json

    binary = ffmpeg_binary()
    cmd = [binary, "-hide_banner", "-i", path, "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    stderr = result.stderr
    for line in stderr.splitlines():
        if "Duration:" in line and "," in line:
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0

from __future__ import annotations

import os
import tempfile

from app.agents.ffmpeg_utils import generate_image_png, generate_tone_wav, probe_duration
from app.agents import montage


def test_build_slideshow_kenburns():
    if not os.path.exists(montage.ffmpeg_binary()):
        return
    with tempfile.TemporaryDirectory() as tmp:
        img1 = os.path.join(tmp, "a.png")
        img2 = os.path.join(tmp, "b.png")
        generate_image_png(img1, color="0x112233")
        generate_image_png(img2, color="0x445566")
        out = os.path.join(tmp, "slideshow.mp4")
        montage.build_slideshow([img1, img2], out, dur_each=2.0, size="640x360", fps=24)
        dur = probe_duration(out)
        assert 3.5 <= dur <= 5.0, f"durée inattendue: {dur}"


def test_concat_videos():
    if not os.path.exists(montage.ffmpeg_binary()):
        return
    from app.agents.ffmpeg_utils import generate_test_video

    with tempfile.TemporaryDirectory() as tmp:
        c1 = os.path.join(tmp, "c1.mp4")
        c2 = os.path.join(tmp, "c2.mp4")
        generate_test_video(c1, 1.0)
        generate_test_video(c2, 1.0)
        out = os.path.join(tmp, "concat.mp4")
        montage.concat_videos([c1, c2], out, size="640x360", fps=24)
        dur = probe_duration(out)
        assert 1.8 <= dur <= 2.5, f"durée inattendue: {dur}"


def test_mix_audio_keeps_video_duration():
    if not os.path.exists(montage.ffmpeg_binary()):
        return
    with tempfile.TemporaryDirectory() as tmp:
        img1 = os.path.join(tmp, "a.png")
        img2 = os.path.join(tmp, "b.png")
        generate_image_png(img1, color="0x223344")
        generate_image_png(img2, color="0x556677")
        raw = os.path.join(tmp, "raw.mp4")
        montage.build_slideshow([img1, img2], raw, dur_each=2.0, size="640x360", fps=24)
        narration = os.path.join(tmp, "narration.wav")
        generate_tone_wav(narration, 1.0)
        final = os.path.join(tmp, "final.mp4")
        montage.mix_audio(raw, [narration], [], None, final, burn_subs=False)
        dur = probe_duration(final)
        # la narration est plus courte que la vidéo: la vidéo garde sa durée pleine
        assert 3.5 <= dur <= 5.0, f"durée inattendue: {dur}"

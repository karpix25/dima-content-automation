from __future__ import annotations

import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from .config import Settings
from .media_assets import MediaAssetStore
from .storage import ScriptRecord


@dataclass(frozen=True)
class InfographicDeliveryResult:
    video_path: Path
    telegram_message_id: str | None


def create_and_send_infographic_reels(
    *,
    record: ScriptRecord,
    user_id: str,
    settings: Settings,
    asset_store: MediaAssetStore,
) -> InfographicDeliveryResult:
    output_dir = settings.video_output_directory / "infographic_reels"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"gold_card_{record.id}.png"
    video_path = output_dir / f"gold_card_{record.id}.mp4"

    render_gold_card(record, image_path)
    audio_path = choose_audio_track(asset_store, user_id)
    render_five_second_video(image_path=image_path, video_path=video_path, audio_path=audio_path)
    message_id = send_video_to_telegram(
        token=settings.telegram_bot_token,
        chat_id=user_id,
        video_path=video_path,
        caption=f"✅ Золотой фон / инфографика 5 сек.\nСценарий #{record.id}: {record.title or record.hook}",
    )
    return InfographicDeliveryResult(video_path=video_path, telegram_message_id=message_id)


def render_gold_card(record: ScriptRecord, path: Path) -> None:
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), (214, 164, 56))
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, height), fill=(224, 175, 64))
    draw.rectangle((0, 0, width, int(height * 0.18)), fill=(245, 207, 111))
    draw.rectangle((0, int(height * 0.82), width, height), fill=(36, 36, 38))

    margin = 86
    title = clean_text(record.hook or record.title or "Amazon insight")
    subtitle = clean_text(record.angle or record.trigger or record.cta)
    bullets = build_bullets(record)
    cta = clean_text(record.cta or "Save this before your next launch")

    title_font = font(74)
    subtitle_font = font(40)
    bullet_font = font(34)
    cta_font = font(38)

    y = 270
    for line in wrap(title.upper(), 17)[:5]:
        draw.text((margin, y), line, font=title_font, fill=(26, 26, 28))
        y += 92

    y += 38
    for line in wrap(subtitle, 27)[:4]:
        draw.text((margin, y), line, font=subtitle_font, fill=(56, 48, 34))
        y += 56

    y += 80
    for item in bullets[:3]:
        draw.rounded_rectangle((margin, y, margin + 28, y + 28), radius=14, fill=(28, 28, 30))
        for line in wrap(item, 31)[:3]:
            draw.text((margin + 52, y - 10), line, font=bullet_font, fill=(24, 24, 25))
            y += 45
        y += 38

    footer_top = int(height * 0.82)
    draw.text((margin, footer_top + 74), "DIMA CONTENT", font=subtitle_font, fill=(245, 207, 111))
    for line in wrap(cta, 28)[:3]:
        draw.text((margin, footer_top + 138), line, font=cta_font, fill=(250, 250, 250))
        footer_top += 48

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def render_five_second_video(*, image_path: Path, video_path: Path, audio_path: Path | None) -> None:
    if audio_path and audio_path.exists():
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            "5",
            "-i",
            str(image_path),
            "-stream_loop",
            "-1",
            "-i",
            str(audio_path),
            "-t",
            "5",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            "5",
            "-i",
            str(image_path),
            "-f",
            "lavfi",
            "-t",
            "5",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-1600:]}")


def send_video_to_telegram(*, token: str, chat_id: str, video_path: Path, caption: str) -> str | None:
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    with video_path.open("rb") as video_file:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data={"chat_id": chat_id, "caption": caption},
            files={"video": (video_path.name, video_file, "video/mp4")},
            timeout=120,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Telegram sendVideo error {response.status_code}: {response.text[:1000]}")
    payload = response.json()
    return str(payload.get("result", {}).get("message_id") or "") or None


def choose_audio_track(asset_store: MediaAssetStore, user_id: str) -> Path | None:
    tracks = asset_store.list_assets(user_id, "instagram_post_5s_audio")
    if not tracks:
        return None
    selected = random.choice(tracks)
    path = Path(selected.file_path)
    return path if path.exists() else None


def build_bullets(record: ScriptRecord) -> list[str]:
    candidates = [record.trigger, record.angle, record.why_it_works, record.source_basis]
    candidates.extend(re.split(r"(?<=[.!?])\s+", record.voiceover or "")[:3])
    return [clean_text(item) for item in candidates if clean_text(item)]


def clean_text(value: str) -> str:
    return " ".join((value or "").replace("\n", " ").split())


def wrap(value: str, max_chars: int) -> list[str]:
    words = clean_text(value).split()
    lines: list[str] = []
    current = ""
    for word in words:
        next_line = f"{current} {word}".strip()
        if current and len(next_line) > max_chars:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    return lines


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()

from __future__ import annotations

import httpx


def send_discord(webhook_url: str, content: str) -> None:
    """Post a plain message to a Discord channel webhook."""
    if not webhook_url:
        return
    resp = httpx.post(webhook_url, json={"content": content}, timeout=15)
    resp.raise_for_status()


def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    """Send a plain message to a Telegram chat via the Bot API."""
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
    resp.raise_for_status()

"""
MediGuard AI — Telegram Bot

Lightweight Telegram bot that proxies user messages to the /ask endpoint.
Requires ``python-telegram-bot`` (installed via extras ``[telegram]``).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import — only needed when the bot is actually started
_Application = None


def _get_telegram():
    global _Application
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
        _Application = Application
        return Update, Application, CommandHandler, MessageHandler, filters
    except ImportError:
        raise ImportError(
            "python-telegram-bot is required for the Telegram bot. "
            "Install it with: pip install 'mediguard[telegram]' or pip install python-telegram-bot"
        )


class MediGuardTelegramBot:
    """Telegram bot that wraps a ``requests`` call to the API ``/ask`` endpoint."""

    def __init__(
        self,
        token: Optional[str] = None,
        api_base_url: str = "http://localhost:8000",
    ) -> None:
        self._token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._api_base = api_base_url.rstrip("/")

        if not self._token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

    def run(self) -> None:
        """Start the bot (blocking)."""
        import httpx

        Update, Application, CommandHandler, MessageHandler, filters = _get_telegram()

        app = Application.builder().token(self._token).build()

        async def start_handler(update: Update, context) -> None:
            await update.message.reply_text(
                "Welcome to MediGuard AI! Send me a medical question or biomarker values "
                "and I'll provide evidence-based insights.\n\n"
                "Disclaimer: This is not a substitute for professional medical advice."
            )

        async def help_handler(update: Update, context) -> None:
            await update.message.reply_text(
                "Send me:\n"
                "• A medical question (e.g. 'What does high HbA1c mean?')\n"
                "• Biomarker values (e.g. 'My glucose is 180 and HbA1c 8.2')\n\n"
                "I'll provide evidence-based analysis."
            )

        async def message_handler(update: Update, context) -> None:
            user_text = update.message.text or ""
            if not user_text.strip():
                return

            await update.message.reply_text("Analyzing… please wait.")

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self._api_base}/ask",
                        json={"question": user_text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    answer = data.get("answer", "Sorry, I could not generate an answer.")
            except Exception as exc:
                logger.error("Telegram→API call failed: %s", exc)
                answer = "Sorry, I'm having trouble processing your request right now."

            # Telegram max message = 4096 chars
            if len(answer) > 4000:
                answer = answer[:4000] + "\n\n… (truncated)"

            await update.message.reply_text(answer)

        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("help", help_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

        logger.info("Telegram bot starting (polling mode)")
        app.run_polling()

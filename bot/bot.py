from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telegram import Update, Document
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Reuse r_runner from the app package
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.core.r_runner import run_rasch_model  # type: ignore


def read_token() -> str:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi. Iltimos, ENV orqali bering.")
    return token


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Assalomu alaykum! CSV fayl yuboring yoki /calcjson bilan JSON matritsa yuboring."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "\n".join([
            "Foydalanish:",
            "- CSV fayl yuboring (0/1, header yo'q) — natija JSON qaytariladi.",
            "- /calcjson {\"responses\": [[...],[...]]} — natija JSON.",
        ])
    )


async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc: Document | None = update.message.document if update.message else None
    if not doc or not doc.file_name or not doc.file_name.lower().endswith(".csv"):
        return

    tf = tempfile.NamedTemporaryFile(prefix="rasch_csv_", suffix=".csv", delete=False)
    tf_path = Path(tf.name)
    tf.close()

    file = await doc.get_file()
    await file.download_to_drive(custom_path=str(tf_path))

    try:
        result: dict[str, Any] = run_rasch_model(tf_path)
    except Exception as e:
        await update.message.reply_text(f"Hisoblash xatosi: {e}")
        tf_path.unlink(missing_ok=True)
        return

    tf_path.unlink(missing_ok=True)

    out_str = json.dumps(result, ensure_ascii=False)
    # Agar juda uzun bo'lsa, fayl sifatida yuboramiz
    if len(out_str) > 3500:
        bio = io.BytesIO(out_str.encode("utf-8"))
        bio.name = "rasch_result.json"
        await update.message.reply_document(document=bio)
    else:
        await update.message.reply_text(out_str)


async def calcjson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = update.message.text or ""
    payload_str = text.partition(" ")[2].strip()
    if not payload_str:
        await update.message.reply_text("JSON kiritma topilmadi. Misol: /calcjson {\"responses\": [[1,0],[0,1]]}")
        return

    try:
        payload = json.loads(payload_str)
        matrix = payload.get("responses")
        if not isinstance(matrix, list) or not matrix:
            raise ValueError("responses noto'g'ri formatda")
    except Exception as e:
        await update.message.reply_text(f"JSON xato: {e}")
        return

    with tempfile.TemporaryDirectory(prefix="rasch_") as td:
        p = Path(td) / "inp.csv"
        with p.open("w", encoding="utf-8") as f:
            for row in matrix:
                f.write(",".join("" if v is None else str(int(v)) for v in row) + "\n")
        try:
            result = run_rasch_model(p)
        except Exception as e:
            await update.message.reply_text(f"Hisoblash xatosi: {e}")
            return

    out_str = json.dumps(result, ensure_ascii=False)
    if len(out_str) > 3500:
        bio = io.BytesIO(out_str.encode("utf-8"))
        bio.name = "rasch_result.json"
        await update.message.reply_document(document=bio)
    else:
        await update.message.reply_text(out_str)


def main() -> None:
    token = read_token()
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("calcjson", calcjson))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_csv))

    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()

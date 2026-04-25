import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "8741545426"))
API_URL = os.getenv("API_URL", "https://tracklab-ai-production.up.railway.app/api/generate")

# user_id -> dict(title, genre, year, source_path, output_path, state)
sessions = {}


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        u = update.effective_user
        if not u or u.id != OWNER_ID:
            if update.message:
                await update.message.reply_text("👑 Private studio. Access denied.")
            elif update.callback_query:
                await update.callback_query.answer("Access denied.", show_alert=True)
            return
        return await func(update, context)
    return wrapper


@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *TRACKLAB AI*\n\n"
        "Flow:\n"
        "1. Send /new\n"
        "2. Type the song title\n"
        "3. Type the genre\n"
        "4. Type the year\n"
        "5. Upload your MP3\n"
        "6. Approve or regenerate the AI cover\n"
        "7. Get your tagged file back\n\n"
        "Other commands:\n"
        "/cancel — abort current session\n"
        "/download — re-send your last finished track",
        parse_mode="Markdown",
    )


@owner_only
async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    sessions[uid] = {"state": "awaiting_title"}
    await update.message.reply_text(
        "🎤 What's the *title* of this track?",
        parse_mode="Markdown",
    )


@owner_only
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Session cancelled. Send /new to start over.")


@owner_only
async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = sessions.get(uid, {})
    out = s.get("output_path")
    if not out or not os.path.exists(out):
        await update.message.reply_text("No finished track yet. Send /new to make one.")
        return
    title = s.get("title", "Track")
    with open(out, "rb") as f:
        await update.message.reply_audio(
            audio=f,
            title=title,
            performer="BAZRAGOD",
            caption=f"👑 BAZRAGOD — {title}",
        )


@owner_only
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()
    s = sessions.get(uid)
    if not s:
        await update.message.reply_text("Send /new to start a new track.")
        return
    state = s.get("state")

    if state == "awaiting_title":
        s["title"] = text
        s["state"] = "awaiting_genre"
        await update.message.reply_text(
            f"✅ Title: *{text}*\n\nNow what's the *genre*? (Dancehall, Hip-Hop, Reggae, etc.)",
            parse_mode="Markdown",
        )
    elif state == "awaiting_genre":
        s["genre"] = text
        s["state"] = "awaiting_year"
        await update.message.reply_text(
            f"✅ Genre: *{text}*\n\nWhat *year*? (e.g. 2026)",
            parse_mode="Markdown",
        )
    elif state == "awaiting_year":
        try:
            year = int(text)
        except ValueError:
            await update.message.reply_text("Send a valid year like 2026.")
            return
        s["year"] = year
        s["state"] = "awaiting_audio"
        await update.message.reply_text(
            f"✅ Year: *{year}*\n\n🎧 Now upload the MP3.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("Send /new to start a new track.")


@owner_only
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = sessions.get(uid)
    if not s or s.get("state") != "awaiting_audio":
        await update.message.reply_text("Send /new first so I know the title and genre.")
        return

    audio = update.message.audio or update.message.document
    if not audio:
        await update.message.reply_text("Send an MP3 file.")
        return

    file = await audio.get_file()
    src_path = f"/tmp/{uid}_src.mp3"
    await file.download_to_drive(src_path)
    s["source_path"] = src_path

    await update.message.reply_text("📥 Audio received. Generating cover and embedding metadata... ⏳")
    await call_api_and_deliver(update, context, regenerate=False)


async def call_api_and_deliver(update_or_query, context, regenerate=False):
    is_query = hasattr(update_or_query, "data")
    uid = update_or_query.from_user.id if is_query else update_or_query.effective_user.id
    chat_id = (update_or_query.message.chat_id if is_query
               else update_or_query.effective_chat.id)

    s = sessions.get(uid, {})
    src = s.get("source_path")
    if not src or not os.path.exists(src):
        await context.bot.send_message(chat_id=chat_id, text="No source file. Send /new again.")
        return

    try:
        with open(src, "rb") as f:
            res = requests.post(
                API_URL,
                files={"file": (f"{s.get('title','track')}.mp3", f, "audio/mpeg")},
                data={
                    "title": s.get("title", "Untitled"),
                    "genre": s.get("genre", "Dancehall"),
                    "year":  str(s.get("year", 2026)),
                    "regenerate": "true" if regenerate else "false",
                },
                timeout=180,
            )
        if res.status_code != 200:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ API error {res.status_code}. Try /new again."
            )
            return

        out_path = f"/tmp/{uid}_out.mp3"
        with open(out_path, "wb") as f:
            f.write(res.content)
        s["output_path"] = out_path

        # Show preview with Approve / Regenerate / Cancel
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data="approve"),
                InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ])

        with open(out_path, "rb") as f:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=f,
                title=s.get("title", "Track"),
                performer="BAZRAGOD",
                caption=(
                    f"👑 *BAZRAGOD — {s.get('title','Track')}*\n"
                    f"Genre: {s.get('genre')} · Year: {s.get('year')}\n\n"
                    "Approve to keep this version, or regenerate the cover."
                ),
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        s["state"] = "awaiting_approval"

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Error: {e}")


@owner_only
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    s = sessions.get(uid, {})
    data = q.data

    if data == "cancel":
        sessions.pop(uid, None)
        await q.message.reply_text("❌ Cancelled. Send /new to start over.")
        return

    if data == "regenerate":
        await q.message.reply_text("🔄 Regenerating cover...")
        await call_api_and_deliver(q, context, regenerate=True)
        return

    if data == "approve":
        await q.message.reply_text(
            f"✅ Approved. Track saved.\n"
            f"Send /download anytime to re-pull this file, or /new for the next one."
        )
        s["state"] = "done"


@owner_only
async def cmd_regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = sessions.get(uid)
    if not s or not s.get("source_path"):
        await update.message.reply_text("No active session. Send /new to start.")
        return
    await update.message.reply_text("🔄 Regenerating cover...")
    await call_api_and_deliver(update, context, regenerate=True)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("download", cmd_download))
    app.add_handler(CommandHandler("regenerate", cmd_regenerate))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()

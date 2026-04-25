import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

from generator import generate_cover, tag_mp3
from config import BOT_TOKEN, OWNER_ID, ARTIST_NAME, UPLOAD_FOLDER


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
        "1. /new\n"
        "2. Type the title\n"
        "3. Type the genre\n"
        "4. Type the year\n"
        "5. Upload MP3\n"
        "6. Approve or regenerate the AI cover\n"
        "7. Get your tagged file back\n\n"
        "/cancel — abort",
        parse_mode="Markdown",
    )


@owner_only
async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["state"] = "awaiting_title"
    await update.message.reply_text(
        "🎤 What's the *title* of this track?",
        parse_mode="Markdown",
    )


@owner_only
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Send /new to start over.")


@owner_only
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    state = context.user_data.get("state")

    if state == "awaiting_title":
        context.user_data["title"] = text
        context.user_data["state"] = "awaiting_genre"
        await update.message.reply_text(
            f"✅ Title: *{text}*\n\nNow what's the *genre*? (Dancehall, Hip-Hop, Reggae, etc.)",
            parse_mode="Markdown",
        )
    elif state == "awaiting_genre":
        context.user_data["genre"] = text
        context.user_data["state"] = "awaiting_year"
        await update.message.reply_text(
            f"✅ Genre: *{text}*\n\nWhat *year*? (e.g. 2026)",
            parse_mode="Markdown",
        )
    elif state == "awaiting_year":
        try:
            year = int(text)
        except ValueError:
            await update.message.reply_text("Send a valid year, like 2026.")
            return
        context.user_data["year"] = year
        context.user_data["state"] = "awaiting_audio"
        await update.message.reply_text(
            f"✅ Year: *{year}*\n\n🎧 Now upload the MP3.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("Send /new to start.")


@owner_only
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_audio":
        await update.message.reply_text("Send /new first so I know the title and genre.")
        return

    audio = update.message.audio or update.message.document
    if not audio:
        await update.message.reply_text("Send an MP3 file.")
        return

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    user_id = update.effective_user.id
    src_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_src.mp3")

    file = await context.bot.get_file(audio.file_id)
    await file.download_to_drive(src_path)
    context.user_data["src_path"] = src_path

    title = context.user_data["title"]
    genre = context.user_data["genre"]

    await update.message.reply_text("📥 Audio received. Generating cover... ⏳")
    try:
        cover_path = generate_cover(title, genre)
    except Exception as e:
        await update.message.reply_text(f"❌ Cover generation failed: {e}\nTry /new again.")
        context.user_data.clear()
        return

    context.user_data["cover_path"] = cover_path
    context.user_data["state"] = "awaiting_approval"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data="approve"),
            InlineKeyboardButton("🔁 Regenerate", callback_data="regen"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])

    with open(cover_path, "rb") as cf:
        await update.message.reply_photo(
            photo=cf,
            caption=(
                f"🎨 Cover for *{title}* ({genre} · {context.user_data['year']})\n\n"
                "Approve to embed, or regenerate."
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


@owner_only
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if context.user_data.get("state") != "awaiting_approval":
        await q.message.reply_text("Session expired. Send /new to start over.")
        return

    if data == "cancel":
        context.user_data.clear()
        await q.message.reply_text("❌ Cancelled. Send /new to start over.")
        return

    if data == "regen":
        await q.message.reply_text("🔁 Regenerating cover...")
        title = context.user_data["title"]
        genre = context.user_data["genre"]
        try:
            cover_path = generate_cover(title, genre)
        except Exception as e:
            await q.message.reply_text(f"❌ Regen failed: {e}")
            return
        context.user_data["cover_path"] = cover_path

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data="approve"),
                InlineKeyboardButton("🔁 Regenerate", callback_data="regen"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ])
        with open(cover_path, "rb") as cf:
            await q.message.reply_photo(
                photo=cf,
                caption=f"🎨 New version for *{title}*",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        return

    if data == "approve":
        await q.message.reply_text("✅ Approved. Embedding metadata...")
        title = context.user_data["title"]
        genre = context.user_data["genre"]
        year = context.user_data["year"]
        src_path = context.user_data["src_path"]
        cover_path = context.user_data["cover_path"]

        try:
            output_path = tag_mp3(
                input_path=src_path,
                title=title,
                artist=ARTIST_NAME,
                cover_path=cover_path,
                genre=genre,
                year=year,
            )
        except Exception as e:
            await q.message.reply_text(f"❌ Embedding failed: {e}")
            return

        with open(output_path, "rb") as f:
            await q.message.reply_audio(
                audio=f,
                title=title,
                performer=ARTIST_NAME,
                caption=(
                    f"👑 *{ARTIST_NAME} — {title}*\n"
                    f"Genre: {genre} · Year: {year}\n\n"
                    "✅ Cover + metadata embedded\n"
                    "📦 Store-ready."
                ),
                parse_mode="Markdown",
            )
        context.user_data.clear()


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()

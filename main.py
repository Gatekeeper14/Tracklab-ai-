from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from generator import generate_cover, tag_mp3
from config import BOT_TOKEN, PAYPAL_LINK, TERMS_URL, PRIVACY_URL, REFUND_URL, FREE_USES

# Track usage per user
user_uses = {}


def payment_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay with PayPal", url=PAYPAL_LINK)],
        [InlineKeyboardButton("📋 Terms", url=TERMS_URL)],
        [InlineKeyboardButton("🔒 Privacy", url=PRIVACY_URL)],
        [InlineKeyboardButton("↩ Refund Policy", url=REFUND_URL)],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 TrackLab AI\n\nUpload an MP3 to generate artwork + metadata."
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uses = user_uses.get(user_id, 0)

    if uses >= FREE_USES:
        await update.message.reply_text(
            "⚠️ Free limit reached.\n\nUpgrade to continue.",
            reply_markup=payment_buttons()
        )
        return

    audio = update.message.audio
    file = await context.bot.get_file(audio.file_id)

    file_path = f"{user_id}.mp3"
    await file.download_to_drive(file_path)

    title = audio.title or "Untitled Track"
    artist = update.effective_user.username or "TrackLab Artist"

    cover_path = generate_cover(title, artist)

    # Store session
    context.user_data["file"] = file_path
    context.user_data["title"] = title
    context.user_data["artist"] = artist
    context.user_data["cover"] = cover_path

    await update.message.reply_photo(
        photo=open(cover_path, "rb"),
        caption=f"🎨 Generated Cover\n\n{title} — {artist}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Regenerate", callback_data="regen")],
            [InlineKeyboardButton("✅ Approve", callback_data="approve")]
        ])
    )


async def regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    title = context.user_data.get("title")
    artist = context.user_data.get("artist")

    cover_path = generate_cover(title, artist)
    context.user_data["cover"] = cover_path

    await query.message.reply_photo(
        photo=open(cover_path, "rb"),
        caption="🔁 New Cover Generated",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Regenerate", callback_data="regen")],
            [InlineKeyboardButton("✅ Approve", callback_data="approve")]
        ])
    )


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    file_path = context.user_data.get("file")
    cover_path = context.user_data.get("cover")
    title = context.user_data.get("title")
    artist = context.user_data.get("artist")

    tag_mp3(file_path, title, artist, cover_path)

    user_id = query.from_user.id
    user_uses[user_id] = user_uses.get(user_id, 0) + 1

    await query.message.reply_document(
        document=open(file_path, "rb"),
        filename="final_track.mp3",
        caption="✅ Your track is ready with artwork + metadata!"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(regenerate, pattern="^regen$"))
    app.add_handler(CallbackQueryHandler(approve, pattern="^approve$"))

    print("BOT RUNNING...")

    app.run_polling()


if name == "main":
    main()

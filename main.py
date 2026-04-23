from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from generator import generate_cover, tag_mp3
from config import *

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

    file = await context.bot.get_file(update.message.audio.file_id)

    path = f"{user_id}.mp3"
    await file.download_to_drive(path)

    title = update.message.audio.title or "Untitled"
    artist = "TrackLab"

    cover = generate_cover(title, artist)

    context.user_data["file"] = path
    context.user_data["title"] = title
    context.user_data["artist"] = artist
    context.user_data["cover"] = cover

    await update.message.reply_photo(
        photo=open(cover, "rb"),
        caption=f"{title}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Regenerate", callback_data="regen")],
            [InlineKeyboardButton("✅ Approve", callback_data="approve")]
        ])
    )


async def regen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    title = context.user_data["title"]
    artist = context.user_data["artist"]

    cover = generate_cover(title, artist)
    context.user_data["cover"] = cover

    await q.message.reply_photo(
        photo=open(cover, "rb"),
        caption="New version",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Regenerate", callback_data="regen")],
            [InlineKeyboardButton("✅ Approve", callback_data="approve")]
        ])
    )


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    file = context.user_data["file"]
    cover = context.user_data["cover"]
    title = context.user_data["title"]
    artist = context.user_data["artist"]

    tag_mp3(file, title, artist, cover)

    user_id = q.from_user.id
    user_uses[user_id] = user_uses.get(user_id, 0) + 1

    await q.message.reply_document(
        document=open(file, "rb"),
        filename="final.mp3",
        caption="✅ Finished file ready"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(regen, pattern="regen"))
    app.add_handler(CallbackQueryHandler(approve, pattern="approve"))

    print("BOT RUNNING...")
    app.run_polling()


if name == "main":
    main(

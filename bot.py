import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send an MP3 file\n\nCommands:\n/regenerate\n/download"
    )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.audio.get_file()

    file_path = f"/tmp/{update.message.from_user.id}.mp3"
    await file.download_to_drive(file_path)

    await update.message.reply_text("Processing...")

    with open(file_path, "rb") as f:
        res = requests.post(API_URL, files={"file": f})

    if res.status_code == 200:
        output_path = f"/tmp/{update.message.from_user.id}_out.mp3"

        with open(output_path, "wb") as f:
            f.write(res.content)

        user_files[update.message.from_user.id] = output_path

        await update.message.reply_audio(
            audio=open(output_path, "rb"),
            title="Processed Track"
        )
    else:
        await update.message.reply_text("Error processing file.")

async def regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Re-send your MP3 to regenerate.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_files:
        await update.message.reply_text("No file available.")
        return

    await update.message.reply_audio(
        audio=open(user_files[user_id], "rb"),
        title="Download your track"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("regenerate", regenerate))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))

    print("Bot running...")
    app.run_polling()

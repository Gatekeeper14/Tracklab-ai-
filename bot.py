import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://tracklab-ai-production.up.railway.app/api/generate"

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 TRACKLAB AI\n\nSend me an MP3 and I will add artwork and metadata.\n\nCommands:\n/regenerate — regenerate artwork\n/download — download your track")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    file = await update.message.audio.get_file()
    file_path = f"/tmp/{uid}.mp3"
    await file.download_to_drive(file_path)
    await update.message.reply_text("Processing your track... ⏳")
    try:
        with open(file_path, "rb") as f:
            res = requests.post(API_URL, files={"file": f}, timeout=60)
        if res.status_code == 200:
            output_path = f"/tmp/{uid}_out.mp3"
            with open(output_path, "wb") as f:
                f.write(res.content)
            user_sessions[uid] = output_path
            await update.message.reply_audio(
                audio=open(output_path, "rb"),
                title="Your Track — Tracklab AI")
        else:
            await update.message.reply_text(f"Processing error. Try again.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send your MP3 again to regenerate artwork.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid not in user_sessions:
        await update.message.reply_text("No file found. Send an MP3 first.")
        return
    await update.message.reply_audio(
        audio=open(user_sessions[uid], "rb"),
        title="Your Track — Tracklab AI")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("regenerate", regenerate))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.run_polling()

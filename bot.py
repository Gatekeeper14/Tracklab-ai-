import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ✅ YOUR REAL API
API_URL = "https://tracklab-ai-production.up.railway.app"

user_files = {}


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send an MP3 file\n\nCommands:\n/regenerate\n/download"
    )


# HANDLE AUDIO
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id

        tg_file = await update.message.audio.get_file()
        input_path = f"/tmp/{tg_file.file_unique_id}.mp3"
        await tg_file.download_to_drive(input_path)

        await update.message.reply_text("⚙️ Processing...")

        with open(input_path, "rb") as f:
            res = requests.post(
                f"{API_URL}/api/generate",
                files={"file": f},
                timeout=120
            )

        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text[:200])

        if res.status_code != 200:
            await update.message.reply_text(f"❌ API Error:\n{res.text}")
            return

        output_path = f"/tmp/output_{user_id}.mp3"

        with open(output_path, "wb") as out:
            out.write(res.content)

        user_files[user_id] = output_path

        await update.message.reply_audio(
            audio=open(output_path, "rb"),
            title="Processed Track"
        )

    except Exception as e:
        await update.message.reply_text(f"🔥 Crash:\n{str(e)}")


# REGENERATE
async def regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id

        if user_id not in user_files:
            await update.message.reply_text("Send MP3 first.")
            return

        await update.message.reply_text("🔄 Regenerating...")

        with open(user_files[user_id], "rb") as f:
            res = requests.post(
                f"{API_URL}/api/regenerate",
                files={"file": f},
                timeout=120
            )

        if res.status_code != 200:
            await update.message.reply_text(f"❌ API Error:\n{res.text}")
            return

        output_path = f"/tmp/regenerated_{user_id}.mp3"

        with open(output_path, "wb") as out:
            out.write(res.content)

        user_files[user_id] = output_path

        await update.message.reply_audio(
            audio=open(output_path, "rb"),
            title="Regenerated Track"
        )

    except Exception as e:
        await update.message.reply_text(f"🔥 Crash:\n{str(e)}")


# DOWNLOAD
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_files:
        await update.message.reply_text("Nothing to download.")
        return

    await update.message.reply_audio(
        audio=open(user_files[user_id], "rb"),
        title="Your File"
    )


# MAIN
def main():
    print("🤖 Bot running...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("regenerate", regenerate))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))

    app.run_polling()


if __name__ == "__main__":
    main()

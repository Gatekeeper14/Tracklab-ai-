import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "YOUR_BOT_TOKEN"
API_URL = "https://tracklab-ai-production.up.railway.app/api/generate"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send an MP3 file\n\nCommands:\n/regenerate\n/download"
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("⚙️ Processing...")

        file = await update.message.audio.get_file()
        file_path = "/tmp/input.mp3"

        await file.download_to_drive(file_path)

        print("📥 Downloaded file")

        # Send to API
        with open(file_path, "rb") as f:
            response = requests.post(
                API_URL,
                files={"file": f},
                timeout=60
            )

        print("📡 API STATUS:", response.status_code)

        if response.status_code != 200:
            await update.message.reply_text(f"❌ API Error: {response.text}")
            return

        output_path = "/tmp/output.mp3"

        with open(output_path, "wb") as f:
            f.write(response.content)

        print("📤 Sending file back")

        await update.message.reply_audio(audio=open(output_path, "rb"))

    except Exception as e:
        print("🔥 BOT ERROR:", str(e))
        await update.message.reply_text(f"❌ Error: {str(e)}")


def main():
    print("🤖 Bot running...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))

    app.run_polling()


if __name__ == "__main__":
    main()

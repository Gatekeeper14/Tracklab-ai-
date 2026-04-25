import os

# --- Required ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", "8741545426"))

# --- Branding ---
ARTIST_NAME = "BAZRAGOD"
ALBUM_NAME = "BAZRAGOD"

# --- Folders (Railway ephemeral filesystem is fine for temp processing) ---
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

# --- Optional / future use ---
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

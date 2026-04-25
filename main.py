"""
BAZRAGOD AI MASTERING STUDIO BOT
Single-owner Telegram bot: upload audio -> AI cover -> embedded MP3.
Stack: Python 3.11 | python-telegram-bot v20 | Flask | Postgres | OpenAI | mutagen
"""

import os
import io
import logging
import asyncio
import threading
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

from mutagen.id3 import ID3, TIT2, TPE1, TALB, TYER, TCON, APIC
from mutagen.mp3 import MP3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bazragod-studio")

BOT_TOKEN      = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OWNER_ID       = int(os.environ.get("OWNER_ID", "8741545426"))
DATABASE_URL   = os.environ.get("DATABASE_PUBLIC_URL") or os.environ["DATABASE_URL"]
WEBHOOK_URL    = os.environ.get("WEBHOOK_URL", "")
PORT           = int(os.environ.get("PORT", "8080"))
ARTIST_NAME    = "BAZRAGOD"
ALBUM_NAME     = "BAZRAGOD"

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def db_connect():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def db_init():
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id SERIAL PRIMARY KEY,
                owner_id BIGINT NOT NULL,
                title TEXT NOT NULL,
                artist TEXT NOT NULL DEFAULT 'BAZRAGOD',
                genre TEXT,
                year INTEGER,
                audio_file_id TEXT,
                cover_url TEXT,
                final_file_id TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id BIGINT PRIMARY KEY,
                state TEXT,
                title TEXT,
                genre TEXT,
                year INTEGER,
                audio_file_id TEXT,
                cover_url TEXT,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
    log.info("DB initialized.")

def session_get(user_id: int) -> dict:
    with db_connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else {}

def session_set(user_id: int, **fields):
    if not fields:
        return
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM sessions WHERE user_id = %s", (user_id,))
        if cur.fetchone():
            cols = ", ".join(f"{k} = %s" for k in fields.keys())
            vals = list(fields.values()) + [user_id]
            cur.execute(
                f"UPDATE sessions SET {cols}, updated_at = NOW() WHERE user_id = %s",
                vals,
            )
        else:
            keys = ["user_id"] + list(fields.keys())
            placeholders = ", ".join(["%s"] * len(keys))
            vals = [user_id] + list(fields.values())
            cur.execute(
                f"INSERT INTO sessions ({', '.join(keys)}) VALUES ({placeholders})",
                vals,
            )
        conn.commit()

def session_clear(user_id: int):
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
        conn.commit()

def track_save(owner_id, title, genre, year, audio_file_id, cover_url, final_file_id):
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tracks (owner_id, title, artist, genre, year,
                                audio_file_id, cover_url, final_file_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (owner_id, title, ARTIST_NAME, genre, year,
              audio_file_id, cover_url, final_file_id))
        track_id = cur.fetchone()[0]
        conn.commit()
        return track_id

def track_list(owner_id: int, limit: int = 20):
    with db_connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, title, genre, year, created_at
            FROM tracks WHERE owner_id = %s
            ORDER BY created_at DESC LIMIT %s
        """, (owner_id, limit))
        return [dict(r) for r in cur.fetchall()]

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != OWNER_ID:
            if update.message:
                await update.message.reply_text("👑 Private studio. Access denied.")
            elif update.callback_query:
                await update.callback_query.answer("Access denied.", show_alert=True)
            return
        return await func(update, context)
    return wrapper

def build_cover_prompt(title: str, genre: str) -> str:
    return (
        f"Album cover art for a {genre} song titled '{title}' by the artist BAZRAGOD. "
        f"Bold, cinematic, high-contrast, professional music industry quality. "
        f"The title '{title}' should be visually integrated into the artwork as stylized typography. "
        f"Black and gold luxury aesthetic with strong visual storytelling. "
        f"Square format, no watermarks, no extra text beyond the title."
    )

def generate_cover(title: str, genre: str) -> str:
    prompt = build_cover_prompt(title, genre)
    log.info(f"Generating cover: {prompt[:120]}...")
    resp = openai_client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    return resp.data[0].url

def download_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content

def embed_metadata(audio_bytes: bytes, cover_bytes: bytes,
                   title: str, artist: str, album: str,
                   year: int, genre: str) -> bytes:
    buf = io.BytesIO(audio_bytes)
    try:
        audio = MP3(buf, ID3=ID3)
    except Exception as e:
        log.warning(f"MP3 load fallback: {e}")
        buf = io.BytesIO(audio_bytes)
        audio = MP3(buf)
    try:
        if audio.tags is None:
            audio.add_tags()
    except Exception:
        pass
    tags = audio.tags or ID3()
    for frame in ("TIT2", "TPE1", "TALB", "TYER", "TCON", "APIC"):
        tags.delall(frame)
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    tags.add(TALB(encoding=3, text=album))
    tags.add(TYER(encoding=3, text=str(year)))
    tags.add(TCON(encoding=3, text=genre))
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_bytes))
    out = io.BytesIO(audio_bytes)
    tags.save(out, v2_version=3)
    out.seek(0)
    return out.read()
@owner_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👑 *BAZRAGOD AI MASTERING STUDIO*\n\n"
        "Upload raw audio, get back a store-ready product with AI cover art "
        "and embedded metadata.\n\n"
        "Commands:\n"
        "/new — start a new track\n"
        "/list — see your last tracks\n"
        "/cancel — abort current session",
        parse_mode="Markdown",
    )

@owner_only
async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_clear(update.effective_user.id)
    session_set(update.effective_user.id, state="awaiting_title")
    await update.message.reply_text(
        "🎤 What's the *title* of this track?\n(Type the song name exactly as you want it tagged.)",
        parse_mode="Markdown",
    )

@owner_only
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_clear(update.effective_user.id)
    await update.message.reply_text("❌ Session cancelled. Send /new to start over.")

@owner_only
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = track_list(update.effective_user.id)
    if not rows:
        await update.message.reply_text("No tracks yet. Send /new to create one.")
        return
    lines = ["📀 *Your tracks:*"]
    for r in rows:
        lines.append(f"#{r['id']} — {r['title']} ({r['genre']}, {r['year']})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@owner_only
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    sess = session_get(user_id)
    state = sess.get("state")

    if state == "awaiting_title":
        if not text:
            await update.message.reply_text("Send the title as text.")
            return
        session_set(user_id, title=text, state="awaiting_genre")
        await update.message.reply_text(
            f"✅ Title: *{text}*\n\nNow what's the *genre*?\n"
            f"(Examples: Dancehall, Hip-Hop, Reggae, Afrobeats, Trap)",
            parse_mode="Markdown",
        )
        return

    if state == "awaiting_genre":
        if not text:
            await update.message.reply_text("Send the genre as text.")
            return
        session_set(user_id, genre=text, state="awaiting_year")
        await update.message.reply_text(
            f"✅ Genre: *{text}*\n\nWhat *year*? (e.g. 2026)",
            parse_mode="Markdown",
        )
        return

    if state == "awaiting_year":
        try:
            year = int(text)
            if year < 1900 or year > 2100:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Send a valid year, like 2026.")
            return
        session_set(user_id, year=year, state="awaiting_audio")
        await update.message.reply_text(
            f"✅ Year: *{year}*\n\n🎧 Now *upload the audio file* (MP3).",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("Send /new to start, or /list to see your tracks.")

@owner_only
async def on_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sess = session_get(user_id)
    if sess.get("state") != "awaiting_audio":
        await update.message.reply_text(
            "Send /new first, then I'll know what title to tag this audio with."
        )
        return
    msg = update.message
    audio_obj = msg.audio or msg.document or msg.voice
    if not audio_obj:
        await update.message.reply_text("Send an MP3 audio file.")
        return
    file_id = audio_obj.file_id
    session_set(user_id, audio_file_id=file_id, state="generating_cover")
    await update.message.reply_text("📥 Audio received. Generating AI cover art...")
    await generate_and_show_cover(update, context, sess["title"], sess["genre"])

async def generate_and_show_cover(update_or_query, context, title: str, genre: str):
    user_id = (update_or_query.effective_user.id
               if hasattr(update_or_query, "effective_user")
               else update_or_query.from_user.id)
    chat_id = (update_or_query.effective_chat.id
               if hasattr(update_or_query, "effective_chat")
               else update_or_query.message.chat_id)
    try:
        cover_url = await asyncio.to_thread(generate_cover, title, genre)
    except Exception as e:
        log.exception("Cover generation failed")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Cover generation failed: {e}\nTry /new again.",
        )
        session_clear(user_id)
        return
    session_set(user_id, cover_url=cover_url, state="awaiting_approval")
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data="approve"),
            InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=cover_url,
        caption=(
            f"🎨 Cover for *{title}* ({genre})\n\n"
            f"Approve to embed into the track, or regenerate for a new version."
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

@owner_only
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    sess = session_get(user_id)
    if sess.get("state") != "awaiting_approval":
        await query.edit_message_caption("Session expired. Send /new to start over.")
        return
    if data == "cancel":
        session_clear(user_id)
        await query.edit_message_caption("❌ Cancelled. Send /new to start over.")
        return
    if data == "regenerate":
        await query.edit_message_caption("🔄 Regenerating cover...")
        session_set(user_id, state="generating_cover")
        await generate_and_show_cover(query, context, sess["title"], sess["genre"])
        return
    if data == "approve":
        await query.edit_message_caption("✅ Approved. Embedding metadata...")
        await finalize_track(query, context, sess)
        return

async def finalize_track(query, context, sess: dict):
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    title  = sess["title"]
    genre  = sess["genre"]
    year   = sess["year"]
    audio_file_id = sess["audio_file_id"]
    cover_url = sess["cover_url"]
    try:
        tg_file = await context.bot.get_file(audio_file_id)
        audio_bytearray = await tg_file.download_as_bytearray()
        audio_bytes = bytes(audio_bytearray)
        cover_bytes = await asyncio.to_thread(download_bytes, cover_url)
        tagged_bytes = await asyncio.to_thread(
            embed_metadata,
            audio_bytes, cover_bytes,
            title, ARTIST_NAME, ALBUM_NAME, year, genre,
        )
        filename = f"{ARTIST_NAME} - {title}.mp3"
        sent = await context.bot.send_audio(
            chat_id=chat_id,
            audio=InputFile(io.BytesIO(tagged_bytes), filename=filename),
            title=title,
            performer=ARTIST_NAME,
            thumbnail=InputFile(io.BytesIO(cover_bytes), filename="cover.jpg"),
            caption=(
                f"👑 *{ARTIST_NAME} — {title}*\n"
                f"Genre: {genre} · Year: {year}\n\n"
                f"✅ Cover art embedded\n"
                f"✅ ID3 metadata embedded\n"
                f"📦 Store-ready product."
            ),
            parse_mode="Markdown",
        )
        final_file_id = sent.audio.file_id if sent.audio else None
        track_id = track_save(
            owner_id=user_id,
            title=title,
            genre=genre,
            year=year,
            audio_file_id=audio_file_id,
            cover_url=cover_url,
            final_file_id=final_file_id,
        )
        session_clear(user_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💾 Saved as track #{track_id}. Send /new for the next one.",
        )
    except Exception as e:
        log.exception("Finalize failed")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Embedding failed: {e}\nSend /new to try again.",
        )
        session_clear(user_id)

application: Application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(CommandHandler("new", cmd_new))
application.add_handler(CommandHandler("cancel", cmd_cancel))
application.add_handler(CommandHandler("list", cmd_list))
application.add_handler(CallbackQueryHandler(on_callback))
application.add_handler(MessageHandler(
    filters.AUDIO | filters.Document.AUDIO | filters.VOICE, on_audio
))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

flask_app = Flask(__name__)
ptb_loop = asyncio.new_event_loop()

def _start_ptb_loop():
    asyncio.set_event_loop(ptb_loop)
    ptb_loop.run_until_complete(application.initialize())
    ptb_loop.run_until_complete(application.start())
    ptb_loop.run_forever()

threading.Thread(target=_start_ptb_loop, daemon=True).start()

@flask_app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "BAZRAGOD AI Mastering Studio"})

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        asyncio.run_coroutine_threadsafe(application.process_update(update), ptb_loop)
        return jsonify({"ok": True})
    except Exception as e:
        log.exception("Webhook error")
        return jsonify({"ok": False, "error": str(e)}), 500

@flask_app.route("/set_webhook", methods=["GET"])
def set_webhook():
    if not WEBHOOK_URL:
        return jsonify({"ok": False, "error": "WEBHOOK_URL not set"}), 400
    url = f"{WEBHOOK_URL.rstrip('/')}/webhook"
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.set_webhook(url=url), ptb_loop
    )
    result = fut.result(timeout=20)
    return jsonify({"ok": True, "webhook_set_to": url, "telegram_response": result})

db_init()
log.info("BAZRAGOD AI Mastering Studio bot is ready.")

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=PORT)

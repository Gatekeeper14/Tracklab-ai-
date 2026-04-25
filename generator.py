import os
import io
import requests
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TYER, TCON
from mutagen.mp3 import MP3
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

ARTIST_NAME = "BAZRAGOD"
ALBUM_NAME = "BAZRAGOD"


def generate_cover_image(title: str, genre: str = "Dancehall") -> bytes:
    """Generate AI cover art via DALL-E 3. Returns JPEG bytes."""
    if client is None:
        raise RuntimeError("OPENAI_API_KEY not set — cannot generate cover.")

    prompt = (
        f"Album cover art for a {genre} song titled '{title}' by the artist BAZRAGOD. "
        f"Bold, cinematic, high-contrast, professional music industry quality. "
        f"The title '{title}' should be visually integrated as stylized typography. "
        f"Black and gold luxury aesthetic. Square format, no watermarks."
    )

    resp = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    image_url = resp.data[0].url
    img = requests.get(image_url, timeout=60)
    img.raise_for_status()
    return img.content


def process_audio_file(
    input_path,
    output_folder,
    title=None,
    artist=None,
    genre="Dancehall",
    year=2026,
    cover_bytes=None,
):
    """
    Embed ID3 metadata and cover art into an MP3.

    - title: song title (defaults to input filename without extension)
    - artist: defaults to BAZRAGOD
    - genre / year: tagged into the file
    - cover_bytes: pre-supplied JPEG bytes; if None, generated via DALL-E 3
    Returns: output_path (string)
    """
    try:
        # Derive title from filename if not provided
        if not title:
            base = os.path.basename(input_path)
            title = os.path.splitext(base)[0]
        if not artist:
            artist = ARTIST_NAME

        # Build a clean output filename based on title
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
        output_filename = f"{artist} - {safe_title}.mp3"
        output_path = os.path.join(output_folder, output_filename)

        # Make sure output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Copy input -> output FIRST, so we tag the copy, not the original
        with open(input_path, "rb") as src, open(output_path, "wb") as dst:
            dst.write(src.read())

        # Load the copy for tagging
        audio = MP3(output_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        # Wipe any existing frames we're about to set (avoid duplicates)
        for frame in ("TIT2", "TPE1", "TALB", "TYER", "TCON", "APIC"):
            audio.tags.delall(frame)

        # Text frames
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TALB(encoding=3, text=ALBUM_NAME))
        audio.tags.add(TYER(encoding=3, text=str(year)))
        audio.tags.add(TCON(encoding=3, text=genre))

        # Cover art — generate if not supplied
        if cover_bytes is None:
            cover_bytes = generate_cover_image(title, genre)

        audio.tags.add(APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,           # 3 = front cover
            desc="Cover",
            data=cover_bytes, # ← REAL image bytes, not the audio file
        ))

        # Save as ID3v2.3 for max compatibility (iOS, Android, players)
        audio.save(v2_version=3)

        return output_path

    except Exception as e:
        print(f"Generator error: {e}")
        raise

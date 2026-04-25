import os
import requests
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TYER, TCON
from mutagen.mp3 import MP3
from openai import OpenAI

from config import OPENAI_API_KEY, ARTIST_NAME, ALBUM_NAME, OUTPUT_FOLDER

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_cover(title: str, genre: str = "Dancehall") -> str:
    """
    Generate AI cover via DALL-E 3, save as JPEG to OUTPUT_FOLDER,
    return local file path.
    """
    if _client is None:
        raise RuntimeError("OPENAI_API_KEY not set — cannot generate cover.")

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    prompt = (
        f"Album cover art for a {genre} song titled '{title}' by the artist {ARTIST_NAME}. "
        f"Bold, cinematic, high-contrast, professional music industry quality. "
        f"The title '{title}' should be visually integrated as stylized typography. "
        f"Black and gold luxury aesthetic. Square format, no watermarks."
    )

    resp = _client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    image_url = resp.data[0].url
    img_bytes = requests.get(image_url, timeout=60).content

    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    cover_path = os.path.join(OUTPUT_FOLDER, f"cover_{safe_title}.jpg")
    with open(cover_path, "wb") as f:
        f.write(img_bytes)
    return cover_path


def tag_mp3(input_path: str, title: str, artist: str, cover_path: str,
            genre: str = "Dancehall", year: int = 2026,
            album: str = None) -> str:
    """
    Embed ID3v2 tags + APIC cover into the MP3.
    Writes a fresh tagged copy to OUTPUT_FOLDER and returns its path.
    Original input file is left untouched.
    """
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    if album is None:
        album = ALBUM_NAME

    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    output_path = os.path.join(OUTPUT_FOLDER, f"{artist} - {safe_title}.mp3")

    # Copy first, tag the copy
    with open(input_path, "rb") as src, open(output_path, "wb") as dst:
        dst.write(src.read())

    audio = MP3(output_path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()

    # Wipe existing frames before writing new ones
    for frame in ("TIT2", "TPE1", "TALB", "TYER", "TCON", "APIC"):
        audio.tags.delall(frame)

    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))
    audio.tags.add(TYER(encoding=3, text=str(year)))
    audio.tags.add(TCON(encoding=3, text=genre))

    # Read REAL image bytes (not the audio file — that was the old bug)
    with open(cover_path, "rb") as cf:
        cover_bytes = cf.read()

    audio.tags.add(APIC(
        encoding=3,
        mime="image/jpeg",
        type=3,           # 3 = front cover
        desc="Cover",
        data=cover_bytes,
    ))

    # ID3v2.3 = max compatibility (iOS, Android, players)
    audio.save(v2_version=3)
    return output_path

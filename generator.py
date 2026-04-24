import os
import base64
from io import BytesIO
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC
from mutagen.mp3 import MP3
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# ---------------------------
# METADATA
# ---------------------------
def extract_metadata(filename):
    name = os.path.splitext(filename)[0]

    clean = name.replace("_", " ").replace("-", " ").strip()

    return {
        "title": clean.title(),
        "artist": "Miserbot",
        "album": "Miserbot Collection",
        "year": "2026"
    }


# ---------------------------
# GENERATE COVER
# ---------------------------
def generate_cover(title):
    if not client:
        raise Exception("OPENAI_API_KEY not set")

    prompt = f"""
    High quality album cover artwork.
    Title: {title}
    Style: dark, hip-hop, cinematic, premium, bold typography, centered layout.
    No blurry images. Clean professional design.
    """

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    img_base64 = result.data[0].b64_json
    return base64.b64decode(img_base64)


# ---------------------------
# EMBED COVER + METADATA
# ---------------------------
def embed_cover(mp3_path, cover_bytes, metadata):
    audio = MP3(mp3_path, ID3=ID3)

    # wipe old tags (important)
    audio.delete()
    audio.tags = ID3()

    # TEXT TAGS
    audio.tags.add(TIT2(encoding=3, text=metadata["title"]))
    audio.tags.add(TPE1(encoding=3, text=metadata["artist"]))
    audio.tags.add(TALB(encoding=3, text=metadata["album"]))
    audio.tags.add(TDRC(encoding=3, text=metadata["year"]))

    # ensure JPEG (iOS fix)
    image = Image.open(BytesIO(cover_bytes)).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    img_data = buffer.getvalue()

    # COVER ART
    audio.tags.add(
        APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=img_data
        )
    )

    # 🔥 CRITICAL FOR iOS
    audio.save(v2_version=3)

    return mp3_path


# ---------------------------
# MAIN PROCESS
# ---------------------------
def process_song(file_path, filename):
    metadata = extract_metadata(filename)

    cover = generate_cover(metadata["title"])

    final_path = embed_cover(file_path, cover, metadata)

    return final_path, metadata

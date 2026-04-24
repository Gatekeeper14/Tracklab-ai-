import os
from io import BytesIO
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC
from mutagen.mp3 import MP3
from openai import OpenAI
from PIL import Image

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Safe client init (prevents crash if key missing)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# ---------------------------
# METADATA EXTRACTION
# ---------------------------
def extract_metadata(filename):
    base = os.path.splitext(filename)[0]

    # Clean name
    clean = base.replace("_", " ").replace("-", " ").strip()

    return {
        "title": clean.title(),
        "artist": "Miserbot",
        "album": "Miserbot Collection",
        "year": "2026"
    }


# ---------------------------
# GENERATE COVER (AI)
# ---------------------------
def generate_cover(title):
    if not client:
        raise Exception("OpenAI API key missing")

    prompt = f"""
    Professional album cover artwork.
    Title: {title}
    Style: modern hip hop, dark aesthetic, high quality, centered text, clean layout.
    """

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    image_bytes = result.data[0].b64_json
    import base64
    img_data = base64.b64decode(image_bytes)

    return img_data


# ---------------------------
# SAVE MP3 WITH METADATA + COVER
# ---------------------------
def embed_cover(mp3_path, cover_bytes, metadata):
    audio = MP3(mp3_path, ID3=ID3)

    # Clear old tags (important for iOS)
    audio.delete()

    audio.tags = ID3()

    # TEXT TAGS
    audio.tags.add(TIT2(encoding=3, text=metadata["title"]))
    audio.tags.add(TPE1(encoding=3, text=metadata["artist"]))
    audio.tags.add(TALB(encoding=3, text=metadata["album"]))
    audio.tags.add(TDRC(encoding=3, text=metadata["year"]))

    # Ensure JPEG format
    image = Image.open(BytesIO(cover_bytes)).convert("RGB")
    img_buffer = BytesIO()
    image.save(img_buffer, format="JPEG")
    img_data = img_buffer.getvalue()

    # COVER TAG (CRITICAL FOR iOS)
    audio.tags.add(
        APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,  # front cover
            desc='Cover',
            data=img_data
        )
    )

    # 🔥 FORCE iOS COMPATIBILITY
    audio.save(v2_version=3)

    return mp3_path


# ---------------------------
# FULL PIPELINE
# ---------------------------
def process_song(file_path, filename):
    metadata = extract_metadata(filename)

    cover = generate_cover(metadata["title"])

    final_path = embed_cover(file_path, cover, metadata)

    return final_path, metadata

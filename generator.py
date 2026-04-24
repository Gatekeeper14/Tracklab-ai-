import os
import base64
from io import BytesIO
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC
from mutagen.mp3 import MP3
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def clean_title(filename):
    name = os.path.splitext(filename)[0]
    return name.replace("_", " ").replace("-", " ").title()


def generate_cover(title, artist):
    if not client:
        raise Exception("OPENAI_API_KEY not set")

    prompt = f"""
    Professional album cover artwork.
    Title: {title}
    Artist: {artist}
    Style: modern hip hop, dark, cinematic, premium, bold text.
    """

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    return base64.b64decode(result.data[0].b64_json)


def embed(mp3_path, cover_bytes, title, artist, album):
    audio = MP3(mp3_path, ID3=ID3)

    audio.delete()
    audio.tags = ID3()

    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))
    audio.tags.add(TDRC(encoding=3, text="2026"))

    # convert to JPEG
    image = Image.open(BytesIO(cover_bytes)).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    audio.tags.add(APIC(
        encoding=3,
        mime="image/jpeg",
        type=3,
        desc="Cover",
        data=buffer.getvalue()
    ))

    audio.save(v2_version=3)

    return mp3_path


def process_song(file_path, filename, artist, album):
    title = clean_title(filename)

    cover = generate_cover(title, artist)

    final = embed(file_path, cover, title, artist, album)

    return final, title

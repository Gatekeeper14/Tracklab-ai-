import os
from PIL import Image, ImageDraw
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from mutagen.mp3 import MP3
import random

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

def generate_cover(filename):
    title = os.path.splitext(filename)[0]

    # Create cover image
    img = Image.new("RGB", (1024, 1024), (
        random.randint(0,255),
        random.randint(0,255),
        random.randint(0,255)
    ))

    draw = ImageDraw.Draw(img)
    draw.text((100, 450), title[:20], fill="white")

    cover_name = f"{title}.png"
    cover_path = os.path.join(OUTPUT_FOLDER, cover_name)
    img.save(cover_path)

    # Embed metadata into MP3
    mp3_path = os.path.join(UPLOAD_FOLDER, filename)

    audio = MP3(mp3_path, ID3=ID3)

    try:
        audio.add_tags()
    except:
        pass

    with open(cover_path, "rb") as img_file:
        audio.tags.add(
            APIC(
                encoding=3,
                mime="image/png",
                type=3,
                desc="Cover",
                data=img_file.read()
            )
        )

    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text="Your Artist Name"))

    audio.save()

    return cover_name

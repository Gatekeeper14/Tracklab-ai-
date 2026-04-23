import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from PIL import Image
from openai import OpenAI
import requests
from io import BytesIO
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def extract_metadata(mp3_path):
    audio = MP3(mp3_path)
    title = "Unknown Title"
    artist = "Unknown Artist"

    try:
        tags = ID3(mp3_path)
        title = tags.get("TIT2", title).text[0]
        artist = tags.get("TPE1", artist).text[0]
    except:
        pass

    return title, artist


def generate_cover(prompt):
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    image_url = response.data[0].url
    img_data = requests.get(image_url).content
    return Image.open(BytesIO(img_data))


def save_cover(image, filename):
    path = f"outputs/{filename}.png"
    image.save(path)
    return path


def embed_cover(mp3_path, cover_path, title, artist):
    audio = ID3(mp3_path)

    with open(cover_path, "rb") as img:
        audio.add(APIC(
            encoding=3,
            mime='image/png',
            type=3,
            desc='Cover',
            data=img.read()
        ))

    audio.add(TIT2(encoding=3, text=title))
    audio.add(TPE1(encoding=3, text=artist))

    audio.save()

import random
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from PIL import Image, ImageDraw


def generate_cover(title, artist):
    colors = [(0,0,0),(20,0,40),(0,20,40),(40,10,10)]
    img = Image.new("RGB", (1000,1000), color=random.choice(colors))
    draw = ImageDraw.Draw(img)

    draw.text((100,400), title, fill=(255,255,255))
    draw.text((100,500), artist, fill=(180,180,180))

    path = f"cover_{random.randint(1000,9999)}.jpg"
    img.save(path)
    return path


def tag_mp3(file_path, title, artist, cover_path):
    try:
        audio = EasyID3(file_path)
    except:
        audio = EasyID3()

    audio["title"] = title
    audio["artist"] = artist
    audio.save(file_path)

    audio = ID3(file_path)
    with open(cover_path, "rb") as img:
        audio.add(APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=img.read()
        ))
    audio.save(file_path)

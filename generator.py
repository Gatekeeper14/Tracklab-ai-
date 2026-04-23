import os
from PIL import Image, ImageDraw, ImageFont
import random

OUTPUT_FOLDER = "outputs"

def generate_cover(filename):
    title = os.path.splitext(filename)[0]

    # Create simple cover
    img = Image.new("RGB", (1024, 1024), (
        random.randint(0,255),
        random.randint(0,255),
        random.randint(0,255)
    ))

    draw = ImageDraw.Draw(img)

    text = title[:20]

    draw.text((100, 450), text, fill="white")

    output_name = f"{title}.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_name)

    img.save(output_path)

    return output_name

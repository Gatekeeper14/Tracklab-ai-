import os
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from mutagen.mp3 import MP3

def process_audio_file(input_path, output_folder):
    try:
        output_path = os.path.join(output_folder, "output.mp3")
        audio = MP3(input_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags["TIT2"] = TIT2(encoding=3, text="Tracklab AI")
        audio.tags["TPE1"] = TPE1(encoding=3, text="Miserbot")
        with open(input_path, "rb") as f:
            audio.tags.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=f.read()
            ))
        audio.save()
        os.rename(input_path, output_path)
        return output_path
    except Exception as e:
        print(f"Generator error: {e}")
        raise e

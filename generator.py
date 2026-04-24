import os
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from mutagen.mp3 import MP3


def process_audio(input_path, output_path):
    try:
        print("🔧 Processing:", input_path)

        audio = MP3(input_path, ID3=ID3)

        if audio.tags is None:
            audio.add_tags()

        # Metadata
        audio.tags["TIT2"] = TIT2(encoding=3, text="Tracklab AI")
        audio.tags["TPE1"] = TPE1(encoding=3, text="Miserbot")

        # Temporary simple artwork (uses same file to avoid crashes)
        with open(input_path, "rb") as f:
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=f.read()
                )
            )

        audio.save()

        os.rename(input_path, output_path)

        print("✅ Done:", output_path)

        return output_path

    except Exception as e:
        print("🔥 GENERATOR ERROR:", str(e))
        raise e

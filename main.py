from flask import Flask, request, send_file, render_template
import os
import zipfile
from generator import process_song

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")

    artist = request.form.get("artist") or "Miserbot"
    album = request.form.get("album") or "Miserbot Collection"

    if not files:
        return "No files uploaded"

    processed_files = []

    for file in files:
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        processed_path, _ = process_song(
            path,
            file.filename,
            artist,
            album
        )

        processed_files.append(processed_path)

    # Create ZIP
    zip_path = os.path.join(UPLOAD_FOLDER, "package.zip")

    with zipfile.ZipFile(zip_path, "w") as z:
        for file_path in processed_files:
            z.write(file_path, os.path.basename(file_path))

    return send_file(zip_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

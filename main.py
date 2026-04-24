from flask import Flask, request, send_file, render_template
import os
from generator import process_song

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

current_file = None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    global current_file

    file = request.files.get("file")

    if not file:
        return "No file uploaded"

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    processed_path, metadata = process_song(path, file.filename)

    current_file = processed_path

    return f"""
    <h2>Processed</h2>
    <p>{metadata}</p>
    <a href="/download">Download MP3</a><br><br>
    <a href="/">Back</a>
    """


@app.route("/download")
def download():
    if not current_file:
        return "No file"

    return send_file(current_file, as_attachment=True)


@app.route("/regenerate", methods=["POST"])
def regenerate():
    global current_file

    if not current_file:
        return "Upload first"

    filename = os.path.basename(current_file)

    processed_path, metadata = process_song(current_file, filename)

    current_file = processed_path

    return f"""
    <h2>Regenerated</h2>
    <p>{metadata}</p>
    <a href="/download">Download MP3</a><br><br>
    <a href="/">Back</a>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

import os
from flask import Flask, request, render_template, send_file, abort

from generator import generate_cover, tag_mp3
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, ARTIST_NAME

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    title = (request.form.get("title") or "Untitled").strip()
    genre = (request.form.get("genre") or "Dancehall").strip()
    try:
        year = int(request.form.get("year") or 2026)
    except ValueError:
        year = 2026
    artist = (request.form.get("artist") or ARTIST_NAME).strip()

    file = request.files.get("file")
    if not file or not file.filename:
        return "No file uploaded", 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    src_path = os.path.join(UPLOAD_FOLDER, f"web_{safe_title}.mp3")
    file.save(src_path)

    try:
        cover_path = generate_cover(title, genre)
        output_path = tag_mp3(
            input_path=src_path,
            title=title,
            artist=artist,
            cover_path=cover_path,
            genre=genre,
            year=year,
        )
    except Exception as e:
        return f"Processing error: {e}", 500

    output_filename = os.path.basename(output_path)
    cover_filename = os.path.basename(cover_path)
    return render_template(
        "result.html",
        title=title,
        artist=artist,
        genre=genre,
        year=year,
        output_filename=output_filename,
        cover_filename=cover_filename,
    )


@app.route("/download/<path:filename>", methods=["GET"])
def download(filename):
    full = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(full):
        abort(404)
    return send_file(full, as_attachment=True)


@app.route("/cover/<path:filename>", methods=["GET"])
def cover(filename):
    full = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(full):
        abort(404)
    return send_file(full, mimetype="image/jpeg")


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

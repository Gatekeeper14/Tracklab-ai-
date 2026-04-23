import os
from flask import Flask, request, render_template, send_file, jsonify
from generator import extract_metadata, generate_cover, save_cover, embed_cover
from config import UPLOAD_FOLDER, OUTPUT_FOLDER

app = Flask(__name__)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

sessions = {}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    title, artist = extract_metadata(path)

    prompt = f"album cover art for a song titled '{title}' by {artist}, modern, high quality"

    image = generate_cover(prompt)
    cover_path = save_cover(image, file.filename)

    sessions[file.filename] = {
        "mp3": path,
        "cover": cover_path,
        "title": title,
        "artist": artist,
        "prompt": prompt
    }

    return jsonify({
        "cover": cover_path,
        "title": title,
        "artist": artist
    })


@app.route("/regenerate", methods=["POST"])
def regenerate():
    name = request.json["file"]
    session = sessions[name]

    image = generate_cover(session["prompt"])
    cover_path = save_cover(image, f"{name}_regen")

    session["cover"] = cover_path

    return jsonify({"cover": cover_path})


@app.route("/download", methods=["POST"])
def download():
    name = request.json["file"]
    session = sessions[name]

    embed_cover(
        session["mp3"],
        session["cover"],
        session["title"],
        session["artist"]
    )

    return send_file(session["mp3"], as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

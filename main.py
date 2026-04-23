import os
from flask import Flask, request, render_template, send_file, jsonify
from generator import extract_metadata, generate_cover, save_cover, embed_cover

# Initialize app
app = Flask(__name__)

# Folders
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# In-memory session storage
sessions = {}

# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# UPLOAD MP3
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Extract metadata
    title, artist = extract_metadata(filepath)

    # Generate prompt
    prompt = f"album cover art for a song titled '{title}' by {artist}, modern, high quality"

    # Generate image
    image = generate_cover(prompt)
    cover_path = save_cover(image, file.filename)

    # Store session
    sessions[file.filename] = {
        "mp3": filepath,
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


# -----------------------------
# REGENERATE COVER
# -----------------------------
@app.route("/regenerate", methods=["POST"])
def regenerate():
    data = request.get_json()
    name = data.get("file")

    if name not in sessions:
        return jsonify({"error": "Session not found"}), 404

    session = sessions[name]

    image = generate_cover(session["prompt"])
    cover_path = save_cover(image, f"{name}_regen")

    session["cover"] = cover_path

    return jsonify({"cover": cover_path})


# -----------------------------
# DOWNLOAD FINAL MP3
# -----------------------------
@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    name = data.get("file")

    if name not in sessions:
        return jsonify({"error": "Session not found"}), 404

    session = sessions[name]

    # Embed cover into MP3
    embed_cover(
        session["mp3"],
        session["cover"],
        session["title"],
        session["artist"]
    )

    return send_file(
        session["mp3"],
        as_attachment=True,
        download_name="final.mp3"
    )


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health")
def health():
    return {"status": "running"}


# -----------------------------
# RUN APP (RAILWAY FIXED)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port)

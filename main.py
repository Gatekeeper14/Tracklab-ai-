import os
import uuid
from flask import Flask, request, render_template, send_file

from generator import process_audio_file

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store last generated file (simple session handling)
LAST_FILE = {}


# =========================
# HOME PAGE
# =========================
@app.route("/")
def index():
    return render_template("index.html")


# =========================
# UPLOAD FROM WEBSITE
# =========================
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    input_path = os.path.join(session_folder, file.filename)
    file.save(input_path)

    output_path = process_audio_file(input_path, session_folder)

    LAST_FILE["path"] = output_path

    return render_template("index.html", success=True)


# =========================
# REGENERATE
# =========================
@app.route("/regenerate")
def regenerate():
    if "path" not in LAST_FILE:
        return "No file yet"

    old_path = LAST_FILE["path"]
    folder = os.path.dirname(old_path)

    # regenerate using same original input
    input_files = [f for f in os.listdir(folder) if f.endswith(".mp3")]
    if not input_files:
        return "No input file found"

    input_path = os.path.join(folder, input_files[0])

    new_output = process_audio_file(input_path, folder)
    LAST_FILE["path"] = new_output

    return render_template("index.html", regenerated=True)


# =========================
# DOWNLOAD
# =========================
@app.route("/download")
def download():
    if "path" not in LAST_FILE:
        return "No file available"

    return send_file(LAST_FILE["path"], as_attachment=True)


# =========================
# API FOR TELEGRAM BOT
# =========================
@app.route("/api/generate", methods=["POST"])
def api_generate():
    if "file" not in request.files:
        return {"error": "No file"}, 400

    file = request.files["file"]

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    input_path = os.path.join(session_folder, file.filename)
    file.save(input_path)

    output_path = process_audio_file(input_path, session_folder)

    return send_file(output_path, as_attachment=True)


# =========================
# POLICY PAGE (STRIPE SAFE)
# =========================
@app.route("/policy")
def policy():
    return render_template("policy.html")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

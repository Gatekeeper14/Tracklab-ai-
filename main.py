import os
import uuid
from flask import Flask, request, render_template, send_file, jsonify
from generator import process_audio_file

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LAST_FILE = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)
    input_path = os.path.join(session_folder, file.filename)
    file.save(input_path)
    output_path = process_audio_file(input_path, session_folder)
    LAST_FILE["path"] = output_path
    return jsonify({"mp3_url": "/download", "cover_url": "/static/cover.jpg"})

@app.route("/regenerate")
def regenerate():
    if "path" not in LAST_FILE:
        return jsonify({"error": "No file yet"}), 400
    old_path = LAST_FILE["path"]
    folder = os.path.dirname(old_path)
    input_files = [f for f in os.listdir(folder) if f.endswith(".mp3")]
    if not input_files:
        return jsonify({"error": "No input file found"}), 400
    input_path = os.path.join(folder, input_files[0])
    new_output = process_audio_file(input_path, folder)
    LAST_FILE["path"] = new_output
    return jsonify({"mp3_url": "/download"})

@app.route("/download")
def download():
    if "path" not in LAST_FILE:
        return jsonify({"error": "No file available"}), 400
    return send_file(LAST_FILE["path"], as_attachment=True)

@app.route("/api/generate", methods=["POST"])
def api_generate():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["file"]
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)
    input_path = os.path.join(session_folder, file.filename or "upload.mp3")
    file.save(input_path)
    output_path = process_audio_file(input_path, session_folder)
    return send_file(output_path, as_attachment=True)

@app.route("/policy")
def policy():
    return render_template("policy.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

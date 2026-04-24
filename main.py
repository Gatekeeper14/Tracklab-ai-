import os
import uuid
import traceback
from flask import Flask, request, send_file, jsonify

from generator import process_audio_file

app = Flask(__name__)

# Health check
@app.route("/")
def home():
    return "API is running"

# MAIN GENERATE ENDPOINT
@app.route("/api/generate", methods=["POST"])
def api_generate():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        # Create temp session folder
        session_id = str(uuid.uuid4())
        session_folder = os.path.join("/tmp", session_id)
        os.makedirs(session_folder, exist_ok=True)

        input_path = os.path.join(session_folder, file.filename)
        file.save(input_path)

        print("📥 File received:", input_path)

        # Process file
        output_path = process_audio_file(input_path, session_folder)

        print("✅ Output ready:", output_path)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        print("🔥 ERROR:", str(e))
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# REGENERATE (same logic, different endpoint)
@app.route("/api/regenerate", methods=["POST"])
def api_regenerate():
    return api_generate()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting API on port {port}")
    app.run(host="0.0.0.0", port=port)

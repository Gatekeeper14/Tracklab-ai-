from flask import Flask, request, send_file, jsonify
import os

from generator import process_audio  # ✅ MATCHES generator.py

app = Flask(__name__)


@app.route("/")
def home():
    return "Tracklab API running"


@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        print("📩 Request received")

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        input_path = "/tmp/input.mp3"
        output_path = "/tmp/output.mp3"

        file.save(input_path)

        print("📁 File saved:", input_path)

        process_audio(input_path, output_path)

        print("📤 Sending file back")

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        print("🔥 API ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

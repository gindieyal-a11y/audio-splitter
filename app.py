import os
import subprocess
import uuid
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def split_audio_direct(input_path, output_prefix):
    # מפצל ישירות את הקובץ המקורי לקטעים של 8 דקות (480 שניות)
    # בלי המרה ל-MP3, כדי לחסוך זמן עיבוד
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-f", "segment",
        "-segment_time", "480",
        "-c", "copy",
        f"{output_prefix}_%03d.wav"
    ], check=True)


@app.route("/process", methods=["POST"])
def process_audio():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file = request.files["file"]
    file_id = str(uuid.uuid4())

    original_name = file.filename or "audio.wav"
    input_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{original_name}")

    file.save(input_path)

    split_prefix = os.path.join(OUTPUT_FOLDER, file_id)
    split_audio_direct(input_path, split_prefix)

    chunk_files = sorted([
        f for f in os.listdir(OUTPUT_FOLDER)
        if f.startswith(file_id) and f.endswith(".wav")
    ])

    base_url = request.host_url.rstrip("/")

    chunks = []
    for chunk in chunk_files:
        chunks.append({
            "fileName": chunk,
            "url": f"{base_url}/files/{chunk}"
        })

    return jsonify({
        "originalFileName": original_name,
        "chunksCount": len(chunks),
        "chunks": chunks
    })


@app.route("/files/<filename>", methods=["GET"])
def serve_file(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=True)


@app.route("/")
def home():
    return "audio splitter is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

from flask import Flask, request, jsonify
import os
import subprocess
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def convert_to_mp3(input_path, output_path):
    subprocess.run([
        "ffmpeg",
        "-i", input_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "64k",
        output_path
    ], check=True)

def split_audio(input_path, output_prefix):
    subprocess.run([
        "ffmpeg",
        "-i", input_path,
        "-f", "segment",
        "-segment_time", "600",
        "-c", "copy",
        f"{output_prefix}_%03d.mp3"
    ], check=True)

@app.route("/process", methods=["POST"])
def process_audio():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file = request.files["file"]
    file_id = str(uuid.uuid4())

    input_path = os.path.join(UPLOAD_FOLDER, file_id + "_" + file.filename)
    mp3_path = os.path.join(OUTPUT_FOLDER, file_id + ".mp3")

    file.save(input_path)

    convert_to_mp3(input_path, mp3_path)

    split_prefix = os.path.join(OUTPUT_FOLDER, file_id)

    split_audio(mp3_path, split_prefix)

    files = sorted([f for f in os.listdir(OUTPUT_FOLDER) if f.startswith(file_id)])

    return jsonify({
        "chunks": files
    })

@app.route("/")
def home():
    return "Audio splitter service running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

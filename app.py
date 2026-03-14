import os
import subprocess
import uuid
import threading
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# שמירת סטטוסים בזיכרון
jobs = {}


def split_audio_direct(input_path, output_prefix):
    # מפצל ישירות את הקובץ המקורי לקטעים של 8 דקות
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-f", "segment",
        "-segment_time", "480",
        "-c", "copy",
        f"{output_prefix}_%03d.wav"
    ], check=True)


def process_job(job_id, input_path, original_name):
    try:
        jobs[job_id]["status"] = "processing"

        split_prefix = os.path.join(OUTPUT_FOLDER, job_id)
        split_audio_direct(input_path, split_prefix)

        chunk_files = sorted([
            f for f in os.listdir(OUTPUT_FOLDER)
            if f.startswith(job_id) and f.endswith(".wav")
        ])

        base_url = jobs[job_id]["base_url"].rstrip("/")

        chunks = []
        for chunk in chunk_files:
            chunks.append({
                "fileName": chunk,
                "url": f"{base_url}/files/{chunk}"
            })

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["chunks"] = chunks
        jobs[job_id]["chunksCount"] = len(chunks)
        jobs[job_id]["originalFileName"] = original_name

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.route("/process", methods=["POST"])
def process_audio():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file = request.files["file"]
    job_id = str(uuid.uuid4())

    original_name = file.filename or "audio.wav"
    input_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{original_name}")
    file.save(input_path)

    jobs[job_id] = {
        "status": "queued",
        "chunks": [],
        "chunksCount": 0,
        "originalFileName": original_name,
        "base_url": request.host_url
    }

    thread = threading.Thread(
        target=process_job,
        args=(job_id, input_path, original_name),
        daemon=True
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "queued"
    })


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "job not found"}), 404

    job = jobs[job_id]
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "chunksCount": job.get("chunksCount", 0),
        "originalFileName": job.get("originalFileName"),
        "chunks": job.get("chunks", []),
        "error": job.get("error")
    })


@app.route("/files/<filename>", methods=["GET"])
def serve_file(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=True)


@app.route("/")
def home():
    return "audio splitter async service is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

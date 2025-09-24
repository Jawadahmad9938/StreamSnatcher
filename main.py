from flask import Flask, render_template, request, Response, jsonify
import yt_dlp
import os
import uuid
import tempfile
import shutil
import imageio_ffmpeg as iio_ffmpeg

app = Flask(__name__)

# ---- Config ----
# Local testing ke liye env var set karlo: USE_IMAGEIO_FFMPEG=true
USE_IMAGEIO_FFMPEG = os.environ.get("USE_IMAGEIO_FFMPEG", "false").lower() == "true"


def get_ffmpeg_path():
    if USE_IMAGEIO_FFMPEG:
        try:
            return iio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"
    return "ffmpeg"   # Production (Aptfile ffmpeg installed)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "http_chunk_size": 10485760,
            "concurrent_fragment_downloads": 5,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "source": info.get("extractor")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["GET", "POST"])
def download():
    video_url = request.json.get("url") if request.method == "POST" else request.args.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ffmpeg_location = get_ffmpeg_path()

        tmpdir = tempfile.mkdtemp(prefix="yt_")
        unique_id = str(uuid.uuid4())
        file_path_template = os.path.join(tmpdir, f"{unique_id}.%(ext)s")

        ydl_opts = {
            "outtmpl": file_path_template,
            "format": "bestvideo+bestaudio/best",
            "ffmpeg_location": ffmpeg_location,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "http_chunk_size": 10485760,
            "concurrent_fragment_downloads": 5,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            final_file_path = ydl.prepare_filename(info_dict)

        if not os.path.exists(final_file_path):
            shutil.rmtree(tmpdir, ignore_errors=True)
            return jsonify({"error": "Download failed"}), 500

        def generate():
            with open(final_file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
            shutil.rmtree(tmpdir, ignore_errors=True)

        file_size = os.path.getsize(final_file_path)
        title = info_dict.get("title", "video").replace(" ", "_")
        headers = {
            "Content-Disposition": f"attachment; filename={title}.mp4",
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4",
        }

        return Response(generate(), headers=headers)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import imageio_ffmpeg as iio_ffmpeg
import uuid

app = Flask(__name__)

# ---- Settings ----
SYSTEM_FFMPEG_PATH = "/usr/bin/ffmpeg"
USE_IMAGEIO_FFMPEG = True


# ---- Helper Functions ----
def get_ffmpeg_path():
    """Return correct ffmpeg path (system or imageio)."""
    ffmpeg_location = SYSTEM_FFMPEG_PATH
    if USE_IMAGEIO_FFMPEG:
        try:
            if not os.path.exists(SYSTEM_FFMPEG_PATH):
                ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
    return ffmpeg_location


def base_ydl_opts(extra=None):
    """Base yt-dlp options (public videos only, no cookies)."""
    opts = {
        "quiet": True,
        "nocheckcertificate": True,   # ignore SSL errors
        "ignoreerrors": True,         # skip broken formats
    }
    if extra:
        opts.update(extra)
    return opts


# ---- Routes ----
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ydl_opts = base_ydl_opts({"skip_download": True})
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "source": info.get("extractor")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["GET"])
def download():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")

        # Formats: try best mp4 first, fallback to any best
        ydl_opts = base_ydl_opts({
            "merge_output_format": "mp4",
            "outtmpl": output_path,
            "ffmpeg_location": get_ffmpeg_path(),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{info.get('title','video')}.mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Main ----
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

from flask import Flask, render_template, request, Response, jsonify
import yt_dlp
import os
import uuid
import tempfile
import imageio_ffmpeg as iio_ffmpeg

app = Flask(__name__)

def get_ffmpeg_path():
    try:
        return iio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Temporary folder for yt-dlp to write chunks
        tmpdir = tempfile.mkdtemp()
        unique_id = str(uuid.uuid4())
        outtmpl = os.path.join(tmpdir, f"{unique_id}.%(ext)s")

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "quiet": True,
            "ignoreerrors": True,
            "no_warnings": True
        }

        # Download video fully first (yt-dlp doesn't natively stream)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            if not info:
                return jsonify({"error": "Download failed - no info returned"}), 500

            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                return jsonify({"error": "Download failed - file not created"}), 500

        # Streaming generator
        def generate():
            with open(filename, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        response = Response(generate(), mimetype="video/mp4")
        response.headers.set(
            "Content-Disposition", "attachment", filename=f"{info.get('title', 'video')}.mp4"
        )
        return response

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)

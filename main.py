from flask import Flask, render_template, request, Response, jsonify
import yt_dlp
import os
import uuid
import tempfile
import glob
import shutil
import imageio_ffmpeg as iio_ffmpeg

app = Flask(__name__)

def get_ffmpeg_path():
    try:
        return iio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

class SimpleLogger:
    def debug(self, msg): pass
    def warning(self, msg): print("[yt-dlp warning]", msg)
    def error(self, msg): print("[yt-dlp error]", msg)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    tmpdir = tempfile.mkdtemp(prefix="yt_download_")
    unique_id = str(uuid.uuid4())
    outtmpl = os.path.join(tmpdir, f"{unique_id}.%(ext)s")

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "ffmpeg_location": get_ffmpeg_path(),
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": False,
        "noplaylist": True,  # 👈 fix playlist issue
        "logger": SimpleLogger(),
        "paths": {"temp": tmpdir},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            if not info:
                return jsonify({"error": "yt-dlp returned no info for the URL"}), 500

            entry = info["entries"][0] if "entries" in info and info["entries"] else info

            try:
                possible_filename = ydl.prepare_filename(entry)
            except Exception:
                possible_filename = None

            final_path = None
            if possible_filename and os.path.exists(possible_filename):
                final_path = possible_filename
            else:
                matches = glob.glob(os.path.join(tmpdir, f"{unique_id}.*"))
                if matches:
                    mp4s = [m for m in matches if m.lower().endswith(".mp4")]
                    final_path = mp4s[0] if mp4s else matches[0]

            if not final_path or not os.path.exists(final_path):
                return jsonify({
                    "error": "Download finished but output file not found",
                    "tmpdir_contents": os.listdir(tmpdir)
                }), 500

            def generate(path):
                try:
                    with open(path, "rb") as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            yield chunk
                finally:
                    try:
                        shutil.rmtree(tmpdir)
                    except Exception:
                        pass

            title = entry.get("title") or "video"
            safe_name = "".join(c for c in title if c.isalnum() or c in " ._-")[:200]
            response = Response(generate(final_path), mimetype="video/mp4")
            response.headers.set("Content-Disposition", "attachment", filename=f"{safe_name}.mp4")
            return response

    except yt_dlp.utils.DownloadError as de:
        return jsonify({"error": "yt-dlp download error", "detail": str(de)}), 500
    except Exception as e:
        return jsonify({"error": "Download failed", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

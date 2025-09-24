from flask import Flask, render_template, request, Response, jsonify
import yt_dlp
import os
import uuid
import tempfile
import glob
import shutil
import mimetypes

app = Flask(__name__)

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
        "format": "bestvideo+bestaudio/best",   # try best combo, else fallback
        "merge_output_format": "mp4",           # always merge into mp4
        "outtmpl": outtmpl,
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": False,
        "noplaylist": True,
        "logger": SimpleLogger(),
        "paths": {"temp": tmpdir},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            if not info:
                shutil.rmtree(tmpdir, ignore_errors=True)
                return jsonify({"error": "yt-dlp returned no info for the URL"}), 500

            entry = info["entries"][0] if "entries" in info and info["entries"] else info

        # find final merged file
        matches = glob.glob(os.path.join(tmpdir, f"{unique_id}.*"))
        final_path = matches[0] if matches else None

        if not final_path or not os.path.exists(final_path):
            contents = os.listdir(tmpdir)
            shutil.rmtree(tmpdir, ignore_errors=True)
            return jsonify({
                "error": "Download finished but output file not found",
                "tmpdir_contents": contents
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
                shutil.rmtree(tmpdir, ignore_errors=True)

        title = entry.get("title") or "video"
        safe_name = "".join(c for c in title if c.isalnum() or c in " ._-")[:200]
        ext = os.path.splitext(final_path)[1] or ".mp4"

        mtype, _ = mimetypes.guess_type(final_path)
        if not mtype:
            mtype = "application/octet-stream"

        response = Response(generate(final_path), mimetype=mtype)
        response.headers.set(
            "Content-Disposition",
            "attachment",
            filename=f"{safe_name}{ext}"
        )
        return response

    except yt_dlp.utils.DownloadError as de:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "yt-dlp download error", "detail": str(de)}), 500
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Download failed", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

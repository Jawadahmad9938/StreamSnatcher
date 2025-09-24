from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid
import io
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


@app.route("/preview", methods=["POST"])
def preview():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # First attempt → normal metadata extraction
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
            "no_warnings": True
        }

        info = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
        except Exception as e1:
            print("First attempt failed:", str(e1))

        # Fallback → extract_flat only
        if not info:
            try:
                ydl_opts_flat = {
                    "quiet": True,
                    "skip_download": True,
                    "ignoreerrors": True,
                    "extract_flat": True
                }
                with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
                    info = ydl.extract_info(video_url, download=False)
            except Exception as e2:
                print("Fallback attempt failed:", str(e2))

        # Still nothing → return dummy
        if not info:
            return jsonify({
                "title": "Unknown Title",
                "thumbnail": None,
                "source": "Unknown"
            })

        # If playlist → pick first entry
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        return jsonify({
            "title": info.get("title", "Untitled"),
            "thumbnail": info.get("thumbnail"),
            "source": info.get("extractor", "unknown")
        })

    except Exception as e:
        return jsonify({"error": f"Preview failed: {str(e)}"}), 500


@app.route("/download", methods=["POST"])
def download():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",  # ✅ safest combo
            "outtmpl": "%(title)s.%(ext)s",
            "merge_output_format": "mp4",  # ensure mp4 output
            "quiet": True,
            "ignoreerrors": True,
            "no_warnings": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            if not info:
                return jsonify({"error": "Download failed - no info returned"})

            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                return jsonify({"error": "Download failed - file not created"})

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, send_file, jsonify
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


@app.route("/preview", methods=["POST"])
def preview():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
            "no_warnings": False,
            "socket_timeout": 30,
            "default_search": "auto",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        if not info:
            return jsonify({"error": "No info extracted"}), 500

        if "entries" in info:
            info = info["entries"][0]

        return jsonify({
            "title": info.get("title", "Untitled"),
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration", 0),
            "source": info.get("extractor", "Unknown")
        })

    except Exception as e:
        return jsonify({"error": f"Preview failed: {str(e)}"}), 500


@app.route("/download", methods=["POST"])
def download():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ffmpeg_location = get_ffmpeg_path()

        with tempfile.TemporaryDirectory() as tmpdir:
            unique_id = str(uuid.uuid4())
            file_path_template = os.path.join(tmpdir, f"{unique_id}.%(ext)s")

            ydl_opts = {
                "outtmpl": file_path_template,
                "format": "bv*+ba/best",
                "ffmpeg_location": ffmpeg_location,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "ignoreerrors": True,
                "no_warnings": False,
                "default_search": "auto",
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)

                if not info_dict:
                    return jsonify({"error": "Download failed - no info returned"}), 500

                final_file_path = ydl.prepare_filename(info_dict)
                if not os.path.exists(final_file_path):
                    # kuch cases me merged file ka naam change hota hai
                    alt_path = os.path.splitext(final_file_path)[0] + ".mp4"
                    if os.path.exists(alt_path):
                        final_file_path = alt_path
                    else:
                        return jsonify({"error": "Download failed - file not created"}), 500

            safe_title = "".join(
                c for c in info_dict.get("title", "video") if c.isalnum() or c in " _-."
            ).rstrip()

            return send_file(
                final_file_path,
                as_attachment=True,
                download_name=f"{safe_title}.mp4",
                mimetype="video/mp4"
            )

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

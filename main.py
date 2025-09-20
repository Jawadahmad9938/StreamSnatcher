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
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "source": info.get("extractor")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def download():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ffmpeg_location = get_ffmpeg_path()

        with tempfile.TemporaryDirectory() as tmpdir:
            unique_id = str(uuid.uuid4())
            temp_filename = f"{unique_id}.%(ext)s"
            file_path_template = os.path.join(tmpdir, temp_filename)

            ydl_opts = {
                "outtmpl": file_path_template,
                "format": "bestvideo+bestaudio/best",
                "ffmpeg_location": ffmpeg_location,
                "merge_output_format": "mp4",
                "noplaylist": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                final_file_path = ydl.prepare_filename(info_dict)

            if not os.path.exists(final_file_path):
                return jsonify({"error": "Download failed"}), 500

            with open(final_file_path, "rb") as f:
                file_data = f.read()

            return send_file(
                io.BytesIO(file_data),
                as_attachment=True,
                download_name=f"{info_dict.get('title', 'video')}.mp4"
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

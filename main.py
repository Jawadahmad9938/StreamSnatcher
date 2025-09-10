from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import io
import tempfile
import imageio_ffmpeg as iio_ffmpeg

app = Flask(__name__)

SYSTEM_FFMPEG_PATH = r"C:\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
USE_IMAGEIO_FFMPEG = True


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        video_url = request.form.get("url")
        if video_url:
            try:
                ffmpeg_location = SYSTEM_FFMPEG_PATH
                if USE_IMAGEIO_FFMPEG:
                    try:
                        if not os.path.exists(SYSTEM_FFMPEG_PATH):
                            ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
                    except Exception:
                        ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()

                with tempfile.TemporaryDirectory() as tmpdir:
                    unique_id = str(uuid.uuid4())
                    temp_filename = f"{unique_id}.%(ext)s"
                    file_path_template = os.path.join(tmpdir, temp_filename)

                    ydl_opts = {
                        "outtmpl": file_path_template,
                        "format": "bestvideo+bestaudio/best",
                        "ffmpeg_location": ffmpeg_location,
                        "merge_output_format": "mp4",
                        "noplaylist": True
                    }

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(video_url, download=True)
                        final_file_path = ydl.prepare_filename(info_dict)

                    if not os.path.exists(final_file_path):
                        return "⚠️ Error: Download failed.", 500

                    with open(final_file_path, "rb") as f:
                        file_data = f.read()

                return send_file(
                    io.BytesIO(file_data),
                    as_attachment=True,
                    download_name=os.path.basename(final_file_path)
                )

            except Exception as e:
                return f"⚠️ Error: {str(e)}", 500

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)

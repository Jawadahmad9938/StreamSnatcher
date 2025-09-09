from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import imageio_ffmpeg as iio_ffmpeg 

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

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
                        import shutil
                        if not os.path.exists(SYSTEM_FFMPEG_PATH):
                            ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
                    except Exception:
                        ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()

                # temporary UUID filename template
                temp_filename = f"{uuid.uuid4()}.%(ext)s"
                file_path_template = os.path.join(DOWNLOAD_FOLDER, temp_filename)

                ydl_opts = {
                    'outtmpl': file_path_template,
                    'format': 'bestvideo+bestaudio/best',
                    'ffmpeg_location': ffmpeg_location
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(video_url, download=True)
                    final_file_path = ydl.prepare_filename(info_dict) 

                # Directly send file as download
                return send_file(final_file_path, as_attachment=True)

            except Exception as e:
                return f"⚠️ Error: {str(e)}", 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

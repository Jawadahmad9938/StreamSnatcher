from flask import Flask, render_template, request, send_file, redirect, url_for
import yt_dlp
import os
import uuid
import imageio_ffmpeg as iio_ffmpeg  # optional fallback

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

SYSTEM_FFMPEG_PATH = r"C:\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
USE_IMAGEIO_FFMPEG = True

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download_video():
    video_url = request.form.get("url")

    if not video_url:
        return "❌ No URL provided", 400

    try:
        filename = f"{uuid.uuid4()}.mp4"
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)

        ffmpeg_location = SYSTEM_FFMPEG_PATH
        if USE_IMAGEIO_FFMPEG:
            try:
                import shutil
                if not os.path.exists(SYSTEM_FFMPEG_PATH):
                    ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()

        ydl_opts = {
            'outtmpl': file_path,
            'format': 'bestvideo+bestaudio/best',
            'ffmpeg_location': ffmpeg_location
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # redirect to preview page
        return redirect(url_for('preview_video', filename=filename))
    except Exception as e:
        return f"⚠️ Error: {str(e)}", 500

@app.route("/preview/<filename>")
def preview_video(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return "❌ File not found", 404

    return render_template("preview.html", filename=filename)

@app.route("/downloads/<filename>")
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

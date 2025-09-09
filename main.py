from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download_video():
    video_url = request.form.get("url")

    if not video_url:
        return "❌ No URL provided", 400

    try:
        # unique filename banane ke liye
        filename = f"{uuid.uuid4()}.mp4"
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)

        ydl_opts = {
            'outtmpl': file_path,
            'format': 'bestvideo+bestaudio/best'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"⚠️ Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)

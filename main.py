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
        # ✅ Fixed ydl_opts with better error handling
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": False,
            "ignoreerrors": True,  # ✅ Important: Continue even if some formats fail
            "extract_flat": False,
            "force_json": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        if not info:
            return jsonify({"error": "Could not fetch video info"}), 404

        # Agar playlist mila ho to first entry lelo
        if "entries" in info:
            info = info["entries"][0]

        # ✅ Safer format extraction with error handling
        formats = []
        available_formats = info.get("formats", [])
        
        for f in available_formats:
            try:
                # ✅ Filter out None values and problematic formats
                if f.get('format_id'):
                    formats.append({
                        "format_id": f.get("format_id", "unknown"),
                        "ext": f.get("ext", "unknown"),
                        "resolution": f.get("resolution") or 
                                    f"{f.get('width', '')}x{f.get('height', '')}" or "N/A",
                        "filesize": f.get("filesize") or f.get("filesize_approx", 0),
                        "format_note": f.get("format_note", ""),
                    })
            except Exception as format_error:
                # Skip problematic formats but continue processing
                print(f"Skipping format due to error: {format_error}")
                continue

        # ✅ Fallback thumbnail selection
        thumbnail = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url') if info.get('thumbnails') else None

        return jsonify({
            "title": info.get("title", "Unknown Title"),
            "thumbnail": thumbnail,
            "uploader": info.get("uploader", "Unknown Uploader"),
            "duration": info.get("duration", 0),
            "source": info.get("extractor", "Unknown Source"),
            "formats": formats
        })

    except Exception as e:
        print(f"Preview Error: {str(e)}")  # ✅ Debug logging
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
            temp_filename = f"{unique_id}.%(ext)s"
            file_path_template = os.path.join(tmpdir, temp_filename)

            # ✅ More robust download options
            ydl_opts = {
                "outtmpl": file_path_template,
                "format": "bestvideo+bestaudio/best",
                "ffmpeg_location": ffmpeg_location,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "ignoreerrors": True,  # ✅ Important addition
                "no_warnings": False,
                "http_chunk_size": 10485760,  # ✅ Better for large files
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                final_file_path = ydl.prepare_filename(info_dict)

            if not os.path.exists(final_file_path):
                return jsonify({"error": "Download failed - file not created"}), 500

            # ✅ Better file handling
            file_handle = open(final_file_path, "rb")
            filename = f"{info_dict.get('title', 'video')}.mp4"
            
            # ✅ Clean special characters from filename
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            
            return send_file(
                file_handle,
                as_attachment=True,
                download_name=filename,
                mimetype="video/mp4"
            )

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500
    

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

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
        # ✅ More robust configuration
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
            "no_warnings": False,
            "extract_flat": False,
            "force_json": True,
            "format": "best",  # ✅ Specific format selection
            "socket_timeout": 30,
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls"]  # ✅ Skip problematic formats
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ✅ Try multiple approaches
            try:
                info = ydl.extract_info(video_url, download=False)
            except Exception as extract_error:
                print(f"First extract attempt failed: {extract_error}")
                # ✅ Retry with simpler options
                ydl_opts_simple = {
                    "quiet": True,
                    "skip_download": True,
                    "ignoreerrors": True,
                    "extract_flat": True
                }
                with yt_dlp.YoutubeDL(ydl_opts_simple) as ydl_simple:
                    info = ydl_simple.extract_info(video_url, download=False)

        if not info:
            return jsonify({"error": "Could not fetch video info. Video might be restricted or unavailable."}), 404

        # Handle playlist
        if "entries" in info:
            if info["entries"]:
                info = info["entries"][0]
            else:
                return jsonify({"error": "Playlist is empty"}), 404

        # ✅ Safe format extraction
        formats = []
        for f in info.get("formats", []):
            try:
                format_info = {
                    "format_id": f.get("format_id", "unknown"),
                    "ext": f.get("ext", "unknown"),
                    "resolution": "N/A",
                    "filesize": f.get("filesize") or f.get("filesize_approx", 0),
                    "format_note": f.get("format_note", ""),
                }
                
                # ✅ Better resolution detection
                if f.get("resolution"):
                    format_info["resolution"] = f["resolution"]
                elif f.get("width") and f.get("height"):
                    format_info["resolution"] = f"{f['width']}x{f['height']}"
                
                formats.append(format_info)
            except Exception:
                continue

        # ✅ Get best available thumbnail
        thumbnail = info.get("thumbnail")
        if not thumbnail and info.get("thumbnails"):
            for thumb in reversed(info["thumbnails"]):  # Get highest quality thumbnail
                if thumb.get("url"):
                    thumbnail = thumb["url"]
                    break

        return jsonify({
            "title": info.get("title", "Untitled"),
            "thumbnail": thumbnail,
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration", 0),
            "source": info.get("extractor", "Unknown"),
            "formats": formats
        })

    except Exception as e:
        error_msg = f"Preview failed: {str(e)}"
        print(f"Preview Error Details: {error_msg}")
        return jsonify({"error": error_msg}), 500
    
    

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

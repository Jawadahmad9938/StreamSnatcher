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
        # ✅ Metadata-only options (no fixed format)
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
            "no_warnings": False,
            "extract_flat": False,
            "force_json": True,
            "socket_timeout": 30,
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls"]
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
            except Exception as extract_error:
                print(f"First extract attempt failed: {extract_error}")
                # ✅ fallback: very flat/simple
                ydl_opts_simple = {
                    "quiet": True,
                    "skip_download": True,
                    "ignoreerrors": True,
                    "extract_flat": True
                }
                with yt_dlp.YoutubeDL(ydl_opts_simple) as ydl_simple:
                    info = ydl_simple.extract_info(video_url, download=False)

        if not info:
            return jsonify({
                "title": "Unknown Title",
                "thumbnail": None,
                "uploader": "Unknown",
                "duration": 0,
                "source": "Unknown",
                "formats": []
            }), 200

        # Handle playlist → pick first entry
        if "entries" in info:
            if info["entries"]:
                info = info["entries"][0]
            else:
                return jsonify({"error": "Playlist is empty"}), 404

        # ✅ Collect formats (but don’t break if none)
        formats = []
        for f in info.get("formats", []):
            try:
                if not f.get("url"):
                    continue
                formats.append({
                    "format_id": f.get("format_id", "unknown"),
                    "ext": f.get("ext", "unknown"),
                    "resolution": f.get("resolution")
                        or (f"{f.get('width','?')}x{f.get('height','?')}"
                            if f.get("width") and f.get("height") else "N/A"),
                    "filesize": f.get("filesize") or f.get("filesize_approx", 0),
                    "note": f.get("format_note", "")
                })
            except Exception:
                continue

        # ✅ Best thumbnail
        thumbnail = info.get("thumbnail")
        if not thumbnail and info.get("thumbnails"):
            for thumb in reversed(info["thumbnails"]):
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

            ydl_opts = {
                "outtmpl": file_path_template,
                "format": "bestvideo+bestaudio/best",
                "ffmpeg_location": ffmpeg_location,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "ignoreerrors": True,
                "no_warnings": False,
                "http_chunk_size": 10485760,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                final_file_path = ydl.prepare_filename(info_dict)

            if not os.path.exists(final_file_path):
                return jsonify({"error": "Download failed - file not created"}), 500

            file_handle = open(final_file_path, "rb")
            filename = f"{info_dict.get('title', 'video')}.mp4"
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

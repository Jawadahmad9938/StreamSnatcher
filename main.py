from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid
import io
import tempfile
import imageio_ffmpeg as iio_ffmpeg
import logging

app = Flask(__name__)

# Setup logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # 🔥 Enhanced yt-dlp options for better compatibility
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": False,
            "extractaudio": False,
            "writeinfojson": False,
            "ignoreerrors": True,
            # 👇 Key additions for stability
            "geo_bypass": True,
            "nocheckcertificate": True,
            "source_address": "0.0.0.0",
            # 👇 User agent to avoid blocking
            "http_headers": {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 🔥 Add error handling for extraction
            try:
                info = ydl.extract_info(video_url, download=False)
            except yt_dlp.utils.DownloadError as e:
                logger.error(f"DownloadError: {str(e)}")
                return jsonify({"error": f"Video access error: {str(e)}"}), 400
            except Exception as e:
                logger.error(f"Extraction error: {str(e)}")
                return jsonify({"error": f"Could not extract video info: {str(e)}"}), 500

        if not info:
            return jsonify({"error": "Could not fetch video info"}), 404

        # Handle playlist case
        if "entries" in info:
            if not info["entries"]:
                return jsonify({"error": "Playlist is empty"}), 404
            info = info["entries"][0]

        # 🔥 Better format handling with error checking
        formats = []
        available_formats = info.get("formats", [])
        
        if not available_formats:
            logger.warning("No formats available for this video")
            # Try to get basic info anyway
            return jsonify({
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader", "Unknown"),
                "duration": info.get("duration"),
                "source": info.get("extractor", "Unknown"),
                "formats": [],
                "warning": "No downloadable formats available"
            })

        for f in available_formats:
            try:
                # 🔥 Safe format processing
                width = f.get("width")
                height = f.get("height")
                resolution = f.get("resolution")
                
                if not resolution and width and height:
                    resolution = f"{width}x{height}"
                elif not resolution:
                    resolution = "Unknown"

                formats.append({
                    "format_id": f.get("format_id", "unknown"),
                    "ext": f.get("ext", "unknown"),
                    "resolution": resolution,
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "format_note": f.get("format_note", ""),
                    "vcodec": f.get("vcodec", "unknown"),
                    "acodec": f.get("acodec", "unknown"),
                })
            except Exception as format_error:
                logger.warning(f"Error processing format: {format_error}")
                continue

        # 🔥 Return comprehensive info
        response_data = {
            "title": info.get("title", "Unknown Title"),
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration"),
            "source": info.get("extractor", "Unknown"),
            "formats": formats,
            "view_count": info.get("view_count"),
            "upload_date": info.get("upload_date"),
            "description": info.get("description", "")[:200] + "..." if info.get("description") and len(info.get("description", "")) > 200 else info.get("description", "")
        }

        logger.info(f"Successfully extracted info for: {response_data['title']}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/download", methods=["POST"])
def download():
    video_url = request.json.get("url")
    format_id = request.json.get("format_id")  # Optional specific format
    
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ffmpeg_location = get_ffmpeg_path()

        with tempfile.TemporaryDirectory() as tmpdir:
            unique_id = str(uuid.uuid4())
            temp_filename = f"{unique_id}.%(ext)s"
            file_path_template = os.path.join(tmpdir, temp_filename)

            # 🔥 Enhanced download options
            ydl_opts = {
                "outtmpl": file_path_template,
                "ffmpeg_location": ffmpeg_location,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "ignoreerrors": False,
                "no_warnings": False,
                # 👇 Better format selection
                "format": format_id if format_id else "best[height<=720]/best",
                # 👇 Fallback options
                "format_sort": ["res:720", "ext:mp4:m4a"],
                # 👇 Network improvements
                "geo_bypass": True,
                "nocheckcertificate": True,
                "http_headers": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info_dict = ydl.extract_info(video_url, download=True)
                except yt_dlp.utils.DownloadError as e:
                    logger.error(f"Download error: {str(e)}")
                    return jsonify({"error": f"Download failed: {str(e)}"}), 400

            # 🔥 Better file path handling
            if "entries" in info_dict:
                info_dict = info_dict["entries"][0]
                
            final_file_path = ydl.prepare_filename(info_dict)
            
            # 🔥 Check for actual downloaded file
            if not os.path.exists(final_file_path):
                # Try different extensions
                base_path = os.path.splitext(final_file_path)[0]
                for ext in ['.mp4', '.webm', '.mkv', '.avi']:
                    test_path = base_path + ext
                    if os.path.exists(test_path):
                        final_file_path = test_path
                        break
                else:
                    return jsonify({"error": "Downloaded file not found"}), 500

            # 🔥 Safe filename
            safe_title = "".join(c for c in info_dict.get('title', 'video') if c.isalnum() or c in (' ', '-', '_')).rstrip()
            download_name = f"{safe_title}.mp4"

            logger.info(f"Sending file: {final_file_path}")
            
            return send_file(
                final_file_path,
                as_attachment=True,
                download_name=download_name,
                mimetype="video/mp4"
            )

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for production monitoring"""
    return jsonify({"status": "healthy", "service": "youtube-downloader"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)  # Production ke liye debug=False
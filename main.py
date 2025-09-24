from flask import Flask, render_template, request, Response, jsonify
import yt_dlp
import os
import uuid
import tempfile
import imageio_ffmpeg as iio_ffmpeg
import glob
import shutil
import time

app = Flask(__name__)

def get_ffmpeg_path():
    try:
        return iio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


@app.route("/")
def home():
    return render_template("index.html")


def safe_extract_info(url):
    """
    Try to get metadata reliably. Returns info dict or None.
    """
    # First attempt: normal metadata extraction
    base_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "default_search": "auto",
    }
    try:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                # if playlist, pick first entry
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                return info
    except Exception as e:
        # log for debugging
        print("safe_extract_info: primary metadata extract failed:", e)

    # Fallback: flat extraction (less strict)
    try:
        flat_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "extract_flat": True,
            "default_search": "auto",
        }
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                return info
    except Exception as e:
        print("safe_extract_info: fallback extract failed:", e)

    return None


@app.route("/download", methods=["POST"])
def download():
    """
    Robust download endpoint:
      - fetch metadata first
      - if available, download into temp dir with outtmpl
      - find final file (prepare_filename or fallback glob)
      - stream file to client and cleanup temp dir
    """
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    # Step 1: metadata
    info = safe_extract_info(video_url)
    if not info:
        # Helpful error explaining common causes
        return jsonify({
            "error": "Download failed - could not fetch video info. "
                     "Video may be private, region-locked, age-restricted or require cookies/login."
        }), 500

    # Use a temp dir per-download so we can reliably find the file and cleanup
    tmpdir = tempfile.mkdtemp(prefix="streamsnatcher_")
    unique_id = str(uuid.uuid4())
    outtmpl = os.path.join(tmpdir, f"{unique_id}.%(ext)s")

    ffmpeg_location = get_ffmpeg_path()

    ydl_opts = {
        "format": "bv*+ba/best",  # safe fallback: best video+audio if available, otherwise best
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "ffmpeg_location": ffmpeg_location,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # keep temp files if something goes wrong so we can inspect
    }

    try:
        # Step 2: download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We call extract_info with download=True so yt-dlp downloads into tmpdir
            info_dict = ydl.extract_info(video_url, download=True)

            if not info_dict:
                # unexpected, but handle gracefully
                shutil.rmtree(tmpdir, ignore_errors=True)
                return jsonify({"error": "Download failed - no info returned by yt-dlp"}), 500

            # Try to get final filename from yt-dlp
            try:
                final_path = ydl.prepare_filename(info_dict)
            except Exception as e:
                print("prepare_filename failed:", e)
                final_path = None

        # Step 3: If prepare_filename didn't point to an existing file, try sensible fallbacks
        if not final_path or not os.path.exists(final_path):
            # first try .mp4 variant of prepared name
            if final_path:
                alt = os.path.splitext(final_path)[0] + ".mp4"
                if os.path.exists(alt):
                    final_path = alt

        if not final_path or not os.path.exists(final_path):
            # fallback: pick the largest file in tmpdir (likely the downloaded video)
            candidates = glob.glob(os.path.join(tmpdir, "*"))
            if not candidates:
                shutil.rmtree(tmpdir, ignore_errors=True)
                return jsonify({"error": "Download failed - file not created"}), 500
            # choose largest file
            candidates = sorted(candidates, key=lambda p: os.path.getsize(p), reverse=True)
            final_path = candidates[0]

        # final safety check
        if not os.path.exists(final_path):
            shutil.rmtree(tmpdir, ignore_errors=True)
            return jsonify({"error": "Download failed - file not found after download"}), 500

        # sanitize filename for Content-Disposition
        safe_title = info_dict.get("title") if isinstance(info_dict, dict) else None
        if not safe_title:
            safe_title = info.get("title") or "video"
        filename_header = "".join(c for c in safe_title if c.isalnum() or c in " _-.").strip() or "video"
        filename_header = f"{filename_header}.mp4"

        # Step 4: stream generator that cleans up tmpdir when done
        def generate_and_cleanup(path, cleanup_dir):
            try:
                with open(path, "rb") as fh:
                    while True:
                        chunk = fh.read(8192)
                        if not chunk:
                            break
                        yield chunk
            finally:
                # small delay to ensure streaming finished for client
                try:
                    time.sleep(0.1)
                    shutil.rmtree(cleanup_dir, ignore_errors=True)
                except Exception as e:
                    print("cleanup failed:", e)

        # Return streaming response
        resp = Response(generate_and_cleanup(final_path, tmpdir), mimetype="video/mp4")
        resp.headers.set("Content-Disposition", "attachment", filename=filename_header)
        return resp

    except Exception as e:
        # ensure temp dir cleaned on unexpected error
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)

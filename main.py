import os
import re
import uuid
import tempfile
import socket
import ipaddress
import yt_dlp
import imageio_ffmpeg as iio_ffmpeg

from flask import Flask, render_template, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import tldextract


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")

default_rate = os.getenv("RATELIMIT_DEFAULT", "50 per minute")
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[default_rate, "1000 per day"]
)

ALLOWED_DOMAINS = [d.strip().lower() for d in os.getenv("ALLOWED_DOMAINS", "").split(",") if d.strip()]
BLOCKED_DOMAINS = [
    "netflix.com", "hulu.com", "disneyplus.com", "primevideo.com",
    "hotstar.com", "hbomax.com", "paramountplus.com", "peacocktv.com",
    "onlyfans.com", "pornhub.com", "xvideos.com", "xhamster.com",
    "redtube.com", "youjizz.com", "brazzers.com"
]

SYSTEM_FFMPEG_PATH = "/usr/bin/ffmpeg"
USE_IMAGEIO_FFMPEG = True

def get_ffmpeg_path():
    ffmpeg_location = SYSTEM_FFMPEG_PATH
    if USE_IMAGEIO_FFMPEG:
        try:
            if not os.path.exists(SYSTEM_FFMPEG_PATH):
                ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_location = iio_ffmpeg.get_ffmpeg_exe()
    return ffmpeg_location

def is_private_ip(url: str) -> bool:
    """Check if URL resolves to private/reserved IP"""
    try:
        domain_match = re.search(r"https?://([^/]+)", url)
        if not domain_match:
            return True
        domain = domain_match.group(1)
        ip = socket.gethostbyname(domain)
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved
    except Exception:
        return True


def is_blocked_domain(url: str) -> bool:
    url = url.lower()
    for dom in BLOCKED_DOMAINS:
        if dom in url:
            return True
    return False


def is_allowed_domain(url: str) -> bool:
    """Check if domain is in ALLOWED_DOMAINS (supports subdomains + short domains)"""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        ext = tldextract.extract(url)

        registered = ".".join([ext.domain, ext.suffix]) if ext.suffix else ext.domain
        full_domain = ".".join(part for part in [ext.subdomain, ext.domain, ext.suffix] if part)

        return (
            registered.lower() in ALLOWED_DOMAINS
            or full_domain.lower() in ALLOWED_DOMAINS
        )
    except Exception:
        return False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")


@app.route("/preview", methods=["POST"])
@limiter.limit("50 per minute")
def preview():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    if is_private_ip(video_url) or is_blocked_domain(video_url) or not is_allowed_domain(video_url):
        return jsonify({"error": "❌ This source is not allowed due to policy."}), 403

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


@app.route("/download", methods=["GET"])
@limiter.limit("50 per minute")
def download():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    if is_private_ip(video_url) or is_blocked_domain(video_url) or not is_allowed_domain(video_url):
        return jsonify({"error": "❌ This source is not allowed due to policy."}), 403

    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")

        ydl_opts = {
            "quiet": True,
            "merge_output_format": "mp4",
            "outtmpl": output_path,
            "ffmpeg_location": get_ffmpeg_path(),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{info.get('title','video')}.mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

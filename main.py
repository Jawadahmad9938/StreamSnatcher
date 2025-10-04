import os
import re
import uuid
import tempfile
import socket
import ipaddress
import logging
import yt_dlp
import imageio_ffmpeg as iio_ffmpeg

from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import tldextract

app = Flask(__name__)
app.secret_key = "76ade72154f0b0f1417b815bfdd984b14db82aaa568c74ac1708bce43c43d2a6"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("downloader")

default_rate = "10 per minute"
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[default_rate, "1000 per day"]
)

ALLOWED_DOMAINS = [
    "youtube.com", "youtu.be", "tiktok.com", "vm.tiktok.com",
    "instagram.com", "facebook.com", "fb.watch", "pinterest.com",
    "dailymotion.com", "vimeo.com", "twitter.com", "x.com",
    "reddit.com", "linkedin.com", "twitch.tv", "snapchat.com",
    "bilibili.com", "vk.com", "soundcloud.com", "vevo.com",
    "rumble.com", "metacafe.com", "odnoklassniki.ru", "threads.net",
    "likee.com", "triller.co", "byte.co", "clapperapp.com",
    "trell.co", "9gag.com"
]

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

def extract_hostname(url: str) -> str | None:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None

def get_registered_domain(url: str) -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        ext = tldextract.extract(url)
        reg = getattr(ext, "registered_domain", None)
        if reg:
            return reg.lower()
        if ext.domain:
            return (ext.domain + ('.' + ext.suffix if ext.suffix else '')).lower()
    except Exception:
        pass
    return ""

def is_allowed_domain(url: str) -> bool:
    try:
        hostname = extract_hostname(url)
        if not hostname:
            return False
        hostname = hostname.lower()
        registered = get_registered_domain(url)

        if registered and registered in ALLOWED_DOMAINS:
            return True
        if hostname in ALLOWED_DOMAINS:
            return True
        for allowed in ALLOWED_DOMAINS:
            if hostname == allowed or hostname.endswith("." + allowed):
                return True
        return False
    except Exception as e:
        logger.exception("is_allowed_domain error: %s", e)
        return False

def is_blocked_domain(url: str) -> bool:
    try:
        hostname = extract_hostname(url)
        if not hostname:
            return False
        hostname = hostname.lower()
        for dom in BLOCKED_DOMAINS:
            if hostname == dom or hostname.endswith("." + dom) or dom in hostname:
                return True
        return False
    except Exception:
        return True

def is_private_ip(url: str) -> bool:
    hostname = extract_hostname(url)
    if not hostname:
        return True
    try:
        ip_obj = ipaddress.ip_address(hostname)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved
    except Exception:
        pass
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            addr = info[4][0]
            try:
                ip_obj = ipaddress.ip_address(addr)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                    return True
            except Exception:
                continue
        return False
    except socket.gaierror:
        reg = get_registered_domain(url)
        if reg and reg in ALLOWED_DOMAINS:
            return False
        return True
    except Exception:
        return True

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
    payload = request.get_json(silent=True) or {}
    video_url = payload.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    if not is_allowed_domain(video_url):
        return jsonify({"error": "Domain not allowed"}), 403
    if is_blocked_domain(video_url):
        return jsonify({"error": "Blocked source"}), 403
    if is_private_ip(video_url):
        return jsonify({"error": "Private/Reserved IP blocked"}), 403
    try:
        ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        return jsonify({
            "title": info.get("title") or "Untitled",
            "thumbnail": info.get("thumbnail") or "",
            "source": info.get("extractor") or "unknown"
        })
    except Exception as e:
        logger.exception("Preview error: %s", e)
        return jsonify({"error": "Failed to fetch preview"}), 500

@app.route("/download", methods=["GET"])
@limiter.limit("50 per minute")
def download():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    if not is_allowed_domain(video_url):
        return jsonify({"error": "Domain not allowed"}), 403
    if is_blocked_domain(video_url):
        return jsonify({"error": "Blocked source"}), 403
    if is_private_ip(video_url):
        return jsonify({"error": "Private/Reserved IP blocked"}), 403
    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "outtmpl": output_path,
            "ffmpeg_location": get_ffmpeg_path(),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{info.get('title','video')}.mp4"
        )
    except Exception as e:
        logger.exception("Download error: %s", e)
        return jsonify({"error": "Download failed"}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

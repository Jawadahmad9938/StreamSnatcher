import os
import re
import uuid
import tempfile
import socket
import ipaddress
import logging
import ssl
import certifi
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
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
    # ==== YouTube ====
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "studio.youtube.com", "gaming.youtube.com",
    "kids.youtube.com", "tv.youtube.com", "news.youtube.com",
    "youtu.be", "yt.be", "ytimg.com", "youtube-nocookie.com",

    # ==== TikTok ====
    "tiktok.com", "www.tiktok.com", "m.tiktok.com", "api.tiktok.com",
    "live.tiktok.com", "music.tiktok.com", "shop.tiktok.com",
    "account.tiktok.com", "ads.tiktok.com", "support.tiktok.com",
    "library.tiktok.com", "service.tiktok.com", "tv.tiktok.com",
    "pro.tiktok.com", "developer.tiktok.com", "developers.tiktok.com",
    "tiktokcdn.com", "tiktokv.com", "vt.tiktok.com", "vm.tiktok.com",
    "v.tiktok.com", "ib.tiktokv.com", "api-h2.tiktokv.com",
    "p16-tiktokcdn-com.akamaized.net", "muscdn.com", "musical.ly",
    "musemuse.cn", "v16a.tiktokcdn.com", "v16m.tiktokcdn.com", "v19.tiktokcdn.com",
    "*.tiktok.com",

    # ==== Instagram ====
    "instagram.com", "www.instagram.com", "m.instagram.com",
    "graph.instagram.com", "api.instagram.com", "business.instagram.com",
    "ig.me", "cdninstagram.com", "instagr.am",

    # ==== Facebook ====
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "fb.com", "fb.watch", "fb.gg", "fb.me", "business.facebook.com",
    "developers.facebook.com", "l.facebook.com", "apps.facebook.com",
    "touch.facebook.com", "upload.facebook.com", "messenger.com",
    "m.me", "meta.com", "static.xx.fbcdn.net", "video.xx.fbcdn.net",
    "connect.facebook.net",

    # ==== Twitter / X ====
    "twitter.com", "www.twitter.com", "mobile.twitter.com",
    "x.com", "t.co", "api.twitter.com", "publish.twitter.com",
    "video.twimg.com", "pbs.twimg.com",

    # ==== Pinterest ====
    "pinterest.com", "www.pinterest.com", "pin.it",
    "in.pinterest.com", "id.pinterest.com", "br.pinterest.com",
    "es.pinterest.com", "api.pinterest.com", "pinterest.co.uk",

    # ==== Snapchat ====
    "snapchat.com", "www.snapchat.com", "story.snapchat.com",
    "lens.snapchat.com", "ads.snapchat.com", "accounts.snapchat.com",
    "support.snapchat.com", "map.snapchat.com", "scan.snapchat.com",
    "bitmoji.com", "snapcamera.snapchat.com", "snapkit.com",
    "app.snapchat.com", "snappublisher.snapchat.com",

    # ==== Reddit ====
    "reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com",
    "np.reddit.com", "amp.reddit.com", "i.redd.it", "v.redd.it",
    "preview.redd.it", "oauth.reddit.com", "gateway.reddit.com",

    # ==== Vimeo ====
    "vimeo.com", "www.vimeo.com", "player.vimeo.com",
    "api.vimeo.com", "vod-progressive.akamaized.net",

    # ==== Dailymotion ====
    "dailymotion.com", "www.dailymotion.com", "m.dailymotion.com",
    "api.dailymotion.com", "dai.ly", "upload.dailymotion.com",

    # ==== LinkedIn ====
    "linkedin.com", "www.linkedin.com", "m.linkedin.com",
    "api.linkedin.com", "learning.linkedin.com", "business.linkedin.com",
    "slide.linkedin.com", "snap.licdn.com", "media.licdn.com",

    # ==== Twitch ====
    "twitch.tv", "www.twitch.tv", "m.twitch.tv", "clips.twitch.tv",
    "api.twitch.tv", "player.twitch.tv", "dashboard.twitch.tv",
    "vod-secure.twitch.tv", "assets.twitch.tv",

    # ==== SoundCloud ====
    "soundcloud.com", "www.soundcloud.com", "m.soundcloud.com",
    "api.soundcloud.com", "a-v2.sndcdn.com", "sndcdn.com",

    # ==== Threads ====
    "threads.net", "www.threads.net",

    # ==== VK ====
    "vk.com", "www.vk.com", "m.vk.com", "api.vk.com",
    "login.vk.com", "oauth.vk.com", "vkuseraudio.net",

    # ==== Others ====
    "likee.com", "www.likee.com", "triller.co", "www.triller.co",
    "byte.co", "www.byte.co", "clapperapp.com", "www.clapperapp.com",
    "trell.co", "www.trell.co", "9gag.com", "www.9gag.com",
    "bilibili.com", "www.bilibili.com", "m.bilibili.com",
    "rumble.com", "www.rumble.com", "metacafe.com", "www.metacafe.com",
    "odnoklassniki.ru", "ok.ru", "m.ok.ru", "video.ok.ru",

    # ==== URL Shorteners ====
    "bit.ly", "tinyurl.com", "t.ly", "rebrand.ly", "rb.gy",
    "cutt.ly", "ow.ly", "snip.ly", "bl.ink", "short.io",
    "short.cm", "t2m.io", "is.gd", "1drv.ms", "goo.gl"
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
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        if not hostname:
            return False

        if hostname.startswith("www."):
            hostname = hostname[4:]

        ext = tldextract.extract(url)
        registered = ext.registered_domain or hostname

        for allowed in ALLOWED_DOMAINS:
            if hostname == allowed or hostname.endswith("." + allowed) or allowed in hostname or registered.endswith(allowed):
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

# =====================
# DOWNLOAD WITH PROGRESS
# =====================
progress_data = {}

@app.route("/download", methods=["GET"])
@limiter.limit("50 per minute")
def download():
    video_url = request.args.get("url")
    download_id = request.args.get("id") or str(uuid.uuid4())
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    if not is_allowed_domain(video_url):
        return jsonify({"error": "Domain not allowed"}), 403
    if is_blocked_domain(video_url):
        return jsonify({"error": "Blocked source"}), 403
    if is_private_ip(video_url):
        return jsonify({"error": "Private/Reserved IP blocked"}), 403

    progress_data[download_id] = {"percent": "0%", "title": "Starting..."}

    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")

        def progress_hook(d):
            if d.get("status") == "downloading":
                percent = d.get("_percent_str", "0%").strip()
                progress_data[download_id]["percent"] = percent
            elif d.get("status") == "finished":
                progress_data[download_id]["percent"] = "100%"
                progress_data[download_id]["title"] = "Processing..."

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "outtmpl": output_path,
            "ffmpeg_location": get_ffmpeg_path(),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "noplaylist": True,
            "cookiefile": None,
            "http_headers": {"User-Agent": "Mozilla/5.0"},
            "progress_hooks": [progress_hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        progress_data[download_id]["percent"] = "100%"
        progress_data[download_id]["title"] = info.get("title", "video")

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{info.get('title','video')}.mp4"
        )
    except Exception as e:
        logger.exception("Download error: %s", e)
        return jsonify({"error": "Download failed"}), 500

@app.route("/progress/<download_id>")
def progress(download_id):
    data = progress_data.get(download_id)
    if not data:
        return jsonify({"percent": "0%", "title": "Waiting..."}), 200
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

# StreamSnatcher 🎬 - YouTube Video Downloader

A professional Flask-based web application for downloading YouTube videos with real-time progress tracking.

## Features

- 🚀 Real-time download progress updates
- 🎨 Modern, responsive UI with glassmorphism design
- 📱 Mobile-friendly interface
- ⚡ Fast downloads with yt-dlp
- 🔄 Background processing with threading
- 📊 Progress bars and download statistics
- 👀 Video preview before download
- 🎯 Support for multiple simultaneous downloads

## Installation

### Prerequisites

- Python 3.7+
- FFmpeg (for video processing)

### Step 1: Install Python Dependencies

```bash
pip install flask yt-dlp flask-socketio python-socketio imageio-ffmpeg
```

### Step 2: Install FFmpeg

#### Windows:
1. Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/
2. Extract to a folder (e.g., `C:\ffmpeg\`)
3. Update the `SYSTEM_FFMPEG_PATH` in `main.py`:
   ```python
   SYSTEM_FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
   ```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS:
```bash
brew install ffmpeg
```

### Step 3: Project Structure

Create the following project structure:
```
streamsnatcher/
│
├── main.py
├── templates/
│   ├── index.html
│   └── preview.html
└── static/
    ├── style.css
    └── script.js
```

### Step 4: Run the Application

```bash
python main.py
```

Visit http://localhost:5000 in your browser.

## Usage

1. Open the web application in your browser
2. Paste a YouTube URL in the input field
3. Click the "Download" button
4. Watch the real-time progress in the downloads section
5. Preview or download the video when completed

## Configuration

You can modify these settings in `main.py`:

- `DOWNLOAD_FOLDER`: Change download directory
- `SYSTEM_FFMPEG_PATH`: Set custom FFmpeg path
- `USE_IMAGEIO_FFMPEG`: Enable/disable imageio-ffmpeg fallback

## Troubleshooting

### Common Issues:

1. **FFmpeg not found error**:
   - Ensure FFmpeg is installed correctly
   - Update the `SYSTEM_FFMPEG_PATH` in the code

2. **Download progress not showing**:
   - Check if SocketIO is properly installed
   - Ensure JavaScript is enabled in your browser

3. **Videos not downloading**:
   - Verify YouTube URL format
   - Check internet connection

### Dependencies Details:

- `flask`: Web framework
- `yt-dlp`: YouTube video downloading library
- `flask-socketio`: WebSocket support for real-time updates
- `imageio-ffmpeg`: FFmpeg wrapper for Python

## License

This project is for educational purposes only. Please respect YouTube's Terms of Service.

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Ensure all dependencies are installed
3. Verify FFmpeg is working correctly

---

**Note**: This tool is intended for personal use only. Always respect copyright laws and terms of service of the platforms you download from.
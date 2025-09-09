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
1. Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/ (download the "full" build)
2. Extract the ZIP file to a folder (e.g., `C:\ffmpeg\`)
3. Add FFmpeg to your system PATH:
   - Right-click on "This PC" or "My Computer" and select "Properties"
   - Click on "Advanced system settings"
   - Click on "Environment Variables"
   - Under "System variables", find and select the "Path" variable
   - Click "Edit"
   - Click "New" and add the path to the FFmpeg bin folder (e.g., `C:\ffmpeg\bin`)
   - Click "OK" to close all dialogs
4. Verify installation by opening Command Prompt and typing:
   ```bash
   ffmpeg -version
   ```
   You should see FFmpeg version information if installed correctly.

5. Update the `SYSTEM_FFMPEG_PATH` in `main.py`:
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
   - Verify FFmpeg is added to your system PATH
   - Check by running `ffmpeg -version` in Command Prompt
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

## FFmpeg Verification

After installing FFmpeg and adding it to your PATH, verify it's working correctly:

1. Open Command Prompt (Windows) or Terminal (Mac/Linux)
2. Type:
   ```bash
   ffmpeg -version
   ```
3. You should see output similar to:
   ```
   ffmpeg version 6.0-full_build-www.gyan.dev Copyright (c) 2000-2023 the FFmpeg developers
   built with gcc 12.2.0 (Rev10, Built by MSYS2 project)
   ...
   ```

If you see version information, FFmpeg is installed correctly and accessible system-wide.

## License

This project is for educational purposes only. Please respect YouTube's Terms of Service.

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Ensure all dependencies are installed
3. Verify FFmpeg is working correctly by running `ffmpeg -version`
4. Check that FFmpeg's bin folder is correctly added to your system PATH

---

**Note**: This tool is intended for personal use only. Always respect copyright laws and terms of service of the platforms you download from.
import os
import logging
from waitress import serve
from main import app

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(level=logging.INFO)
logging.info("Starting application...")

# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)

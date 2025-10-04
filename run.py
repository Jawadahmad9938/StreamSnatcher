import os
import logging
from dotenv import load_dotenv
from waitress import serve
from main import app

# ---------------------------
# Load environment variables
# ---------------------------
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logging.info(f".env file loaded from {dotenv_path}")
else:
    logging.warning(".env file not found, relying on system environment variables.")

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(level=logging.INFO)
logging.info("Starting application...")

# Debug: print domains to confirm load
logging.info("ALLOWED_DOMAINS = %s", os.getenv("ALLOWED_DOMAINS"))

# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT env automatically
    serve(app, host="0.0.0.0", port=port)

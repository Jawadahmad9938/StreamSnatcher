from dotenv import load_dotenv
load_dotenv() 
from waitress import serve
from main import app
import logging
import os

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT env
    serve(app, host="0.0.0.0", port=port)

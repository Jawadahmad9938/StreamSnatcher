from waitress import serve
from main import app
import logging

logging.basicConfig(level=logging.INFO)

serve(app, host="127.0.0.1", port=5000)

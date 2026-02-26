"""Configuration for the retail data layer and LLM orchestration."""
import os

from dotenv import load_dotenv

# Load environment variables from .env (including GEMINI_API_KEY, etc.)
load_dotenv()

# Path to the SQLite database and CSV (default: data/ under project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.environ.get("RETAIL_DB_PATH", os.path.join(DATA_DIR, "retail.db"))
CSV_PATH = os.environ.get(
    "RETAIL_CSV_PATH",
    os.path.join(DATA_DIR, "Retail_Transaction_Dataset.csv"),
)

# Base URL for the existing Flask REST API used by the LLM layer
API_BASE_URL = os.environ.get("RETAIL_API_BASE_URL", "http://127.0.0.1:5000")

# Gemini / google-genai configuration
# We explicitly expect GEMINI_API_KEY in the environment (or .env)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL_INTENT = os.environ.get("GEMINI_MODEL_INTENT", "gemini-2.5-flash")
GEMINI_MODEL_RESPONSE = os.environ.get(
    "GEMINI_MODEL_RESPONSE", "gemini-3-flash-preview"
)


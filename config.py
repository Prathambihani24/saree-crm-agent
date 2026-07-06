import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "showup123")

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    str(BASE_DIR / "credentials.json"),
)

FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

META_GRAPH_API_VERSION = "v18.0"
META_MESSAGES_URL = (
    f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
    f"/{{phone_number_id}}/messages"
)

VALID_INTENTS = {
    "price_inquiry",
    "availability",
    "order_placement",
    "cod_question",
    "shipping_question",
    "general",
}

def sheets_configured() -> bool:
    return bool(GOOGLE_SHEET_ID) and Path(GOOGLE_CREDENTIALS_PATH).is_file()


def whatsapp_configured() -> bool:
    return bool(META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID)


def groq_configured() -> bool:
    return bool(GROQ_API_KEY)

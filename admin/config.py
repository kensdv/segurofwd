import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot and Telegram API settings
API_TOKEN = os.getenv("API_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")

# Ensure mandatory variables are present
if not API_TOKEN or not API_ID or not API_HASH or not MONGO_URI:
    raise ValueError("Missing required environment variables.")

# Other constants
LOGIN_TIMEOUT = 300  # Timeout for stale login sessions
MAX_OTP_RETRIES = 3
GROUPS_PER_PAGE = 20
CUSTOM_FOLDER = "sessions"

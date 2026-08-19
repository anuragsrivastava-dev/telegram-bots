import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Admin Authorization
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Bot Tokens
PYBOT_TOKEN = os.getenv("PYBOT_TOKEN")
MEOW_TOKEN = os.getenv("MEOW_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PRICE_BOT_TOKEN = os.getenv("PRICE_BOT_TOKEN")
TEMPMAIL_BOT_TOKEN = os.getenv("TEMPMAIL_BOT_TOKEN")
SHORTENER_BOT_TOKEN = os.getenv("SHORTENER_BOT_TOKEN")
TND_BOT_TOKEN = os.getenv("TND_BOT_TOKEN")
MEMORY_BOT_TOKEN = os.getenv("MEMORY_BOT_TOKEN")
HUD_BOT_TOKEN = os.getenv("HUD_BOT_TOKEN")
GAME_BOT_TOKEN = os.getenv("GAME_BOT_TOKEN")

# Quiz Bot token (falls back to GAME_BOT_TOKEN if not specified)
QUIZ_BOT_TOKEN = os.getenv("QUIZ_BOT_TOKEN", GAME_BOT_TOKEN)

# Flappy Game token (falls back to GAME_BOT_TOKEN if not specified)
FLAPPY_GAME_TOKEN = os.getenv("FLAPPY_GAME_TOKEN", GAME_BOT_TOKEN)

missing = [
    key for key, val in {
        "PYBOT_TOKEN": PYBOT_TOKEN,
        "MEOW_TOKEN": MEOW_TOKEN,
        "GROQ_API_KEY": GROQ_API_KEY,
        "PRICE_BOT_TOKEN": PRICE_BOT_TOKEN,
        "TEMPMAIL_BOT_TOKEN": TEMPMAIL_BOT_TOKEN,
        "SHORTENER_BOT_TOKEN": SHORTENER_BOT_TOKEN,
        "TND_BOT_TOKEN": TND_BOT_TOKEN,
        "MEMORY_BOT_TOKEN": MEMORY_BOT_TOKEN,
        "HUD_BOT_TOKEN": HUD_BOT_TOKEN,
        "GAME_BOT_TOKEN": GAME_BOT_TOKEN,
    }.items() if not val
]

if missing:
    raise ValueError(f"Missing required environment variables in .env: {', '.join(missing)}")
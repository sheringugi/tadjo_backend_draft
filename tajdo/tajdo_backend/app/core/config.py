from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Tajdo Online Store API"
    # CORS Origins
    # Load from env or default to localhost
    _ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:5173,http://localhost:3000,https://www.tajdo.ch")
    BACKEND_CORS_ORIGINS: List[str] = [origin.strip() for origin in _ALLOWED_ORIGINS.split(",") if origin.strip()]

    # TWINT Listener Settings
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "143"))
    TWINT_EMAIL_USER: str = os.getenv("TWINT_EMAIL_USER", "")
    TWINT_EMAIL_PASSWORD: str = os.getenv("TWINT_EMAIL_PASSWORD", "")

settings = Settings()
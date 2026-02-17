from typing import List

class Settings:
    PROJECT_NAME: str = "Tajdo Online Store API"
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8080", # Current frontend port
        "http://localhost:5173", # Standard Vite port
        "http://localhost:3000", # Standard React port
    ]

settings = Settings()
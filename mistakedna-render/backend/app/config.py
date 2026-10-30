"""Environment-only configuration. No secrets are shipped with the application."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

@dataclass
class Settings:
    database_url: str = os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "data" / "mistakedna.db"}')
    app_origin: str = os.getenv('APP_ORIGIN', os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:8000')).rstrip('/')
    secure_cookies: bool = os.getenv('COOKIE_SECURE', 'true' if os.getenv('RENDER') else 'false').lower() == 'true'
    production: bool = os.getenv('APP_ENV', 'development') == 'production'
    static_dir: str = os.getenv('STATIC_DIR', str(ROOT / 'frontend' / 'dist'))
    offline_ai_enabled: bool = os.getenv('OFFLINE_AI_ENABLED', 'true').lower() == 'true'
    offline_model_dir: str = os.getenv('OFFLINE_MODEL_DIR', str(Path(__file__).parent / 'offline_model'))
    tutor_limit: int = int(os.getenv('TUTOR_REQUESTS_PER_HOUR', '20'))
    allow_registration: bool = os.getenv('ALLOW_REGISTRATION', 'true').lower() == 'true'

    @property
    def ai_available(self):
        return self.offline_ai_enabled and (Path(self.offline_model_dir)/'weights.npz').is_file() and (Path(self.offline_model_dir)/'manifest.json').is_file()

    def validate(self):
        if self.production:
            if not self.database_url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
                raise RuntimeError('Production requires a persistent PostgreSQL DATABASE_URL.')
            if not self.app_origin.startswith('https://') or not self.secure_cookies:
                raise RuntimeError('Production requires an HTTPS APP_ORIGIN and COOKIE_SECURE=true.')

settings = Settings()

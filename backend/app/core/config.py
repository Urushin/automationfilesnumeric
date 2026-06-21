import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    @property
    def HUGGINGFACE_API_KEY(self) -> str:
        # Check env first
        val = os.getenv("HUGGINGFACE_API_KEY", "")
        if not val:
            # Fallback to DB settings
            try:
                from ..database import SessionLocal
                from ..models import Setting
                db = SessionLocal()
                row = db.query(Setting).first()
                if row and row.huggingface_key:
                    val = row.huggingface_key
                db.close()
            except Exception:
                pass
        return val or ""

    @property
    def STABILITY_API_KEY(self) -> str:
        val = os.getenv("STABILITY_API_KEY", "")
        if not val:
            try:
                from ..database import SessionLocal
                from ..models import Setting
                db = SessionLocal()
                row = db.query(Setting).first()
                if row and getattr(row, "stability_key", None):
                    val = row.stability_key
                db.close()
            except Exception:
                pass
        return val or ""

settings = Settings()

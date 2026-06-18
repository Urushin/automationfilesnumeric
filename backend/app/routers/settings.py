from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Setting
from ..schemas import SettingResponse, SettingUpdate
from ..services.vector import verify_binary

router = APIRouter(prefix="/api/settings", tags=["settings"])

def get_or_create_settings(db: Session) -> Setting:
    """Helper to fetch settings row or create the default one."""
    settings = db.query(Setting).first()
    if not settings:
        settings = Setting(
            openai_key="",
            mistral_key="",
            gemini_key="",
            etsy_client_id="",
            etsy_client_secret="",
            etsy_oauth_token="",
            default_price=3.0,
            default_quantity=999,
            default_status="draft",
            potrace_path="potrace",
            inkscape_path="inkscape",
            mockup_background_path=""
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.get("", response_model=SettingResponse)
def get_settings(db: Session = Depends(get_db)):
    return get_or_create_settings(db)

@router.put("", response_model=SettingResponse)
def update_settings(payload: SettingUpdate, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(settings, key, value)
        
    db.commit()
    db.refresh(settings)
    return settings

@router.post("/test-binaries")
def test_binaries(db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    
    potrace_ok = verify_binary(settings.potrace_path)
    inkscape_ok = verify_binary(settings.inkscape_path)
    
    return {
        "potrace": {
            "status": "OK" if potrace_ok else "FAILED",
            "path": settings.potrace_path,
            "error": None if potrace_ok else "Binary not found. Ensure it is installed and in your system PATH, or specify the absolute path."
        },
        "inkscape": {
            "status": "OK" if inkscape_ok else "FAILED",
            "path": settings.inkscape_path,
            "error": None if inkscape_ok else "Binary not found. Ensure it is installed and in your system PATH, or specify the absolute path."
        }
    }

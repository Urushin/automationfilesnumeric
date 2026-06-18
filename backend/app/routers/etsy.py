import json
import time
import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from ..database import SessionLocal, get_db
from ..models import Setting
from ..services.etsy_api import generate_pkce_pair, refresh_etsy_token
from .settings import get_or_create_settings

router = APIRouter(prefix="/api/etsy", tags=["etsy_oauth"])
oauth_router = APIRouter(prefix="/api/oauth", tags=["etsy_oauth"])

def refresh_token_background(settings_id: int):
    db = SessionLocal()
    try:
        settings = db.query(Setting).filter(Setting.id == settings_id).first()
        if not settings or not settings.etsy_oauth_token:
            return
        token_data = json.loads(settings.etsy_oauth_token)
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 0)
        created_at = token_data.get("created_at", 0)
        if not refresh_token or time.time() < created_at + expires_in - 300:
            return
        new_token = refresh_etsy_token(settings.etsy_client_id, settings.etsy_client_secret, refresh_token)
        settings.etsy_oauth_token = json.dumps(new_token)
        db.commit()
    except Exception as exc:
        print(f"Etsy background token refresh failed: {exc}")
    finally:
        db.close()

@router.get("/login")
def etsy_login(db: Session = Depends(get_db)):
    """Generates authentication URL for Etsy OAuth 2.0 with PKCE."""
    settings = get_or_create_settings(db)
    if not settings.etsy_client_id:
        raise HTTPException(
            status_code=400,
            detail="Veuillez d'abord configurer votre Etsy Client ID dans les réglages."
        )
        
    verifier, challenge = generate_pkce_pair()
    
    # Store the code verifier in settings temporarily
    temp_auth = {
        "code_verifier": verifier,
        "timestamp": time.time()
    }
    settings.etsy_oauth_token = f"temp:{json.dumps(temp_auth)}"
    db.commit()
    
    redirect_uri = "http://localhost:8000/api/oauth/callback"
    scope = "listings_w listings_r"
    state = "etsy_laser_automation_oauth"
    
    auth_url = (
        "https://www.etsy.com/oauth/connect"
        f"?response_type=code"
        f"&client_id={settings.etsy_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    
    return {"url": auth_url}

def render_oauth_error(message: str, status_code: int = 400):
    return HTMLResponse(
        content=f"""
        <html>
            <body style="font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background-color: #0f172a; color: #f8fafc;">
                <div style="background-color: #1e293b; padding: 2rem; border-radius: 0.5rem; max-width: 720px;">
                    <h2 style="color: #ef4444; margin-top: 0;">Échec de Connexion Etsy</h2>
                    <p style="white-space: pre-wrap;">{message}</p>
                    <a href="http://localhost:3000/settings" style="display: inline-block; background-color: #6366f1; color: white; padding: 0.5rem 1rem; border-radius: 0.25rem; text-decoration: none; margin-top: 1rem;">Retourner aux paramètres</a>
                </div>
            </body>
        </html>
        """,
        status_code=status_code,
    )

def handle_etsy_callback(
    background_tasks: BackgroundTasks,
    code: str,
    state: Optional[str],
    db: Session,
):
    """Processes Etsy redirection callback, exchanges code for access and refresh tokens."""
    if state != "etsy_laser_automation_oauth":
        raise HTTPException(status_code=400, detail="État OAuth invalide.")

    settings = get_or_create_settings(db)

    if not settings.etsy_oauth_token or not settings.etsy_oauth_token.startswith("temp:"):
        raise HTTPException(
            status_code=400,
            detail="Session OAuth expirée ou invalide. Veuillez réessayer."
        )

    try:
        temp_data = json.loads(settings.etsy_oauth_token[5:])
        verifier = temp_data.get("code_verifier")
    except Exception:
        raise HTTPException(status_code=400, detail="Données temporaires corrompues.")

    url = "https://api.etsy.com/v3/public/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.etsy_client_id,
        "code": code,
        "redirect_uri": "http://localhost:8000/api/oauth/callback",
        "code_verifier": verifier
    }

    if settings.etsy_client_secret:
        payload["client_secret"] = settings.etsy_client_secret

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        settings.etsy_oauth_token = ""
        db.commit()
        return render_oauth_error(str(exc), 502)

    if response.status_code != 200:
        settings.etsy_oauth_token = ""
        db.commit()
        return render_oauth_error(response.text, 400)

    token_data = response.json()
    token_data["created_at"] = time.time()
    settings.etsy_oauth_token = json.dumps(token_data)
    db.commit()
    db.refresh(settings)

    background_tasks.add_task(refresh_token_background, settings.id)
    return RedirectResponse(url="http://localhost:3000/settings?etsy_connect=success")


@router.get("/callback")
def etsy_callback(
    background_tasks: BackgroundTasks,
    code: str = Query(...), 
    state: str = Query(None), 
    db: Session = Depends(get_db)
):
    return handle_etsy_callback(background_tasks, code, state, db)


@oauth_router.get("/callback")
def oauth_callback(
    background_tasks: BackgroundTasks,
    code: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db),
):
    return handle_etsy_callback(background_tasks, code, state, db)

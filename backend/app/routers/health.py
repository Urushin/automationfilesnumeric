"""
Health Router
Endpoint GET /api/health qui diagnostique l'état de tous les composants système :
- Binaires CLI (Potrace, Inkscape) avec auto-détection multi-OS
- Token OAuth Etsy (validité + expiration)
- Endpoint POST /api/health/auto-detect pour correction automatique des chemins
"""
import json
import os
import platform
import subprocess
import time
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Setting

router = APIRouter(prefix="/api/health", tags=["health"])

# ─────────────────────────────────────────────────────────────────────────────
# CHEMINS STANDARD PAR OS (auto-healing)
# ─────────────────────────────────────────────────────────────────────────────
STANDARD_PATHS: Dict[str, Dict[str, List[str]]] = {
    "Darwin": {  # macOS
        "potrace": [
            "/opt/homebrew/bin/potrace",    # Homebrew M1/M2
            "/usr/local/bin/potrace",       # Homebrew Intel
            "/usr/bin/potrace",
        ],
        "inkscape": [
            "/Applications/Inkscape.app/Contents/MacOS/inkscape",
            "/opt/homebrew/bin/inkscape",
            "/usr/local/bin/inkscape",
        ],
    },
    "Linux": {
        "potrace": [
            "/usr/bin/potrace",
            "/usr/local/bin/potrace",
            "/snap/bin/potrace",
        ],
        "inkscape": [
            "/usr/bin/inkscape",
            "/usr/local/bin/inkscape",
            "/snap/bin/inkscape",
            "/app/bin/inkscape",  # Flatpak
        ],
    },
    "Windows": {
        "potrace": [
            r"C:\Program Files\potrace\potrace.exe",
            r"C:\potrace\potrace.exe",
        ],
        "inkscape": [
            r"C:\Program Files\Inkscape\bin\inkscape.exe",
            r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        ],
    },
}


def _test_binary(path: str) -> bool:
    """Teste si un binaire est exécutable via --version ou -h."""
    for flag in ("--version", "-h", "-V"):
        try:
            result = subprocess.run(
                [path, flag],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if result.returncode in (0, 1):  # Certains binaires retournent 1 pour --version
                return True
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
            continue
    return False


def _auto_detect_binary(name: str, configured_path: str) -> dict:
    """
    Détecte automatiquement un binaire dans les emplacements standards.

    Returns:
        dict avec status, path, resolved_path, error
    """
    os_name = platform.system()

    # 1. Tester le chemin configuré en premier
    if _test_binary(configured_path):
        return {
            "name": name,
            "status": "OK",
            "path": configured_path,
            "resolved_path": configured_path,
            "error": None,
        }

    # 2. Tenter la détection automatique via shutil.which
    import shutil
    which_path = shutil.which(name)
    if which_path and _test_binary(which_path):
        return {
            "name": name,
            "status": "OK",
            "path": configured_path,
            "resolved_path": which_path,
            "error": None,
        }

    # 3. Chercher dans les emplacements standards par OS
    standard = STANDARD_PATHS.get(os_name, {}).get(name, [])
    for candidate in standard:
        if os.path.exists(candidate) and _test_binary(candidate):
            return {
                "name": name,
                "status": "OK",
                "path": configured_path,
                "resolved_path": candidate,
                "error": None,
            }

    # 4. Non trouvé nulle part
    return {
        "name": name,
        "status": "FAILED",
        "path": configured_path,
        "resolved_path": None,
        "error": (
            f"Binaire '{name}' introuvable. Installez-le (brew install {name} sur Mac, "
            f"apt install {name} sur Linux) ou spécifiez le chemin exact dans les paramètres."
        ),
    }


def _get_etsy_token_status(settings: Setting) -> dict:
    """Analyse l'état du token OAuth Etsy."""
    if not settings.etsy_client_id or not settings.etsy_oauth_token or settings.etsy_oauth_token in ("", "mock_mode_active"):
        return {
            "connected": False,
            "expires_in_hours": None,
            "refresh_expires_in_days": None,
            "warning": "Non connecté à Etsy.",
        }

    try:
        token_data = json.loads(settings.etsy_oauth_token)
        created_at = token_data.get("created_at", 0)
        expires_in = token_data.get("expires_in", 14400)  # 4h default

        now = time.time()
        remaining_seconds = (created_at + expires_in) - now
        remaining_hours = remaining_seconds / 3600

        warning = None
        if remaining_hours < 0:
            warning = "🔴 Token expiré ! Reconnectez votre compte Etsy."
        elif remaining_hours < 1:
            warning = f"⚠️ Token expire dans {remaining_hours * 60:.0f} minutes."

        # Refresh token (90 jours)
        refresh_expires_in_days = None
        if "refresh_expires_in" in token_data:
            refresh_remaining = (created_at + token_data["refresh_expires_in"]) - now
            refresh_expires_in_days = max(0, refresh_remaining / 86400)
            if refresh_expires_in_days < 7:
                warning = (warning or "") + f" ⚠️ Refresh token expire dans {refresh_expires_in_days:.0f} jours — reconnectez-vous."

        return {
            "connected": True,
            "expires_in_hours": max(0, remaining_hours),
            "refresh_expires_in_days": refresh_expires_in_days,
            "warning": warning,
        }
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return {
            "connected": False,
            "expires_in_hours": None,
            "refresh_expires_in_days": None,
            "warning": f"Token invalide ou corrompu : {e}",
        }


def get_or_create_settings(db: Session) -> Setting:
    settings = db.query(Setting).first()
    if not settings:
        settings = Setting(
            potrace_path="potrace",
            inkscape_path="inkscape",
            default_price=3.0,
            default_quantity=999,
            default_status="draft",
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("")
def get_health(db: Session = Depends(get_db)):
    """
    Retourne l'état complet du système :
    - Statut de chaque binaire CLI
    - Statut du token OAuth Etsy
    """
    settings = get_or_create_settings(db)

    potrace_status = _auto_detect_binary("potrace", settings.potrace_path or "potrace")
    inkscape_status = _auto_detect_binary("inkscape", settings.inkscape_path or "inkscape")
    etsy_status = _get_etsy_token_status(settings)

    all_ok = (
        potrace_status["status"] == "OK"
        and inkscape_status["status"] == "OK"
    )
    degraded = not all_ok

    return {
        "status": "healthy" if all_ok else "degraded",
        "binaries": [potrace_status, inkscape_status],
        "etsy_token": etsy_status,
    }


@router.post("/auto-detect")
def auto_detect_binaries(db: Session = Depends(get_db)):
    """
    Lance la détection automatique des chemins binaires et met à jour la DB
    si de meilleures valeurs sont trouvées.
    """
    settings = get_or_create_settings(db)

    potrace_result = _auto_detect_binary("potrace", settings.potrace_path or "potrace")
    inkscape_result = _auto_detect_binary("inkscape", settings.inkscape_path or "inkscape")

    updated = []

    if potrace_result["status"] == "OK" and potrace_result["resolved_path"]:
        new_path = potrace_result["resolved_path"]
        if new_path != settings.potrace_path:
            settings.potrace_path = new_path
            updated.append(f"potrace → {new_path}")

    if inkscape_result["status"] == "OK" and inkscape_result["resolved_path"]:
        new_path = inkscape_result["resolved_path"]
        if new_path != settings.inkscape_path:
            settings.inkscape_path = new_path
            updated.append(f"inkscape → {new_path}")

    if updated:
        db.commit()
        db.refresh(settings)

    return {
        "potrace": potrace_result,
        "inkscape": inkscape_result,
        "auto_updated": updated,
        "message": (
            f"Chemins mis à jour : {', '.join(updated)}"
            if updated
            else "Aucun changement — chemins déjà optimaux."
        ),
    }

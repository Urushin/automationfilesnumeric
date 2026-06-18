"""
Scraper Router — Banque d'Idées & Tendances
Expose les endpoints pour lire, rafraîchir et injecter les idées de la banque.
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import IdeaBank
from ..schemas import IdeaBankItem, IdeaBankCreate
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/api/scraper", tags=["Banque d'Idées"])


# ─────────────────────────────────────────────────────────────────────────────
# LIST IDEAS
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/ideas", response_model=List[IdeaBankItem])
def list_ideas(
    category: Optional[str] = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retourne la liste des idées triées par trend_score DESC."""
    q = db.query(IdeaBank)
    if category:
        q = q.filter(IdeaBank.category == category)
    if min_score > 0:
        q = q.filter(IdeaBank.trend_score >= min_score)
    return q.order_by(IdeaBank.trend_score.desc()).offset(offset).limit(limit).all()


# ─────────────────────────────────────────────────────────────────────────────
# REFRESH (manual trigger)
# ─────────────────────────────────────────────────────────────────────────────
def _run_scrape_task(db: Session):
    """Task de fond pour le scraping."""
    from ..services.scraper import run_full_scrape
    try:
        run_full_scrape(db)
    finally:
        db.close()


@router.post("/refresh")
async def refresh_ideas(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Lance le scraping Etsy en tâche de fond."""
    from ..database import SessionLocal
    bg_db = SessionLocal()
    background_tasks.add_task(_run_scrape_task, bg_db)
    return {"message": "Scraping lancé en arrière-plan. Rafraîchissez dans 30 secondes."}


# ─────────────────────────────────────────────────────────────────────────────
# INJECT INTO PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/inject/{idea_id}")
def inject_idea(idea_id: int, db: Session = Depends(get_db)):
    """
    Marque une idée comme injectée et retourne les mots-clés extraits
    pour pré-remplir le champ Thème du pipeline.
    """
    idea = db.query(IdeaBank).filter(IdeaBank.id == idea_id).first()
    if not idea:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Idée introuvable.")

    idea.is_injected = True
    db.commit()

    # Extraire les mots-clés
    keywords = []
    if idea.keywords:
        try:
            keywords = json.loads(idea.keywords)
        except (json.JSONDecodeError, ValueError):
            keywords = [idea.keywords]

    # Construire le thème optimisé
    theme = ", ".join(keywords[:4]) if keywords else idea.title[:80]

    # Construire le prompt Google AI Studio
    stencil_prompt = (
        f"Pure flat solid black stencil silhouette icon on a pure stark solid white background. "
        f"Theme: {theme}. "
        f"No gradients, no shadows, no gray pixels, no texture, no sketch lines. "
        f"All black structures MUST be physically connected. Laser cutting ready. "
        f"Style: modern, clean, minimalist. Single design centered on white."
    )

    return {
        "idea_id": idea_id,
        "theme": theme,
        "keywords": keywords,
        "title": idea.title,
        "category": idea.category,
        "stencil_prompt": stencil_prompt,
        "google_ai_studio_url": "https://aistudio.google.com/app/prompts/new_freeform",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADD MANUAL IDEA
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/ideas", response_model=IdeaBankItem)
def create_idea(payload: IdeaBankCreate, db: Session = Depends(get_db)):
    """Ajoute manuellement une idée dans la banque."""
    item = IdeaBank(
        title=payload.title,
        thumbnail_url=payload.thumbnail_url,
        source_url=payload.source_url,
        trend_score=payload.trend_score,
        category=payload.category,
        detected_at=datetime.utcnow(),
        keywords=payload.keywords,
        source=payload.source or "manual",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ─────────────────────────────────────────────────────────────────────────────
# DELETE IDEA
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/ideas/{idea_id}", status_code=204)
def delete_idea(idea_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    idea = db.query(IdeaBank).filter(IdeaBank.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idée introuvable.")
    db.delete(idea)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE PROXY (avoid loading issues with external images)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/proxy-image")
async def proxy_image(url: str):
    """Proxies an external image through the backend to avoid CORS/loading issues."""
    if not url:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="URL is required")
    
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; EtsyLaserBot/1.0)",
                "Accept": "image/*",
            })
            if resp.status_code != 200:
                from fastapi import HTTPException
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch image")
            
            return StreamingResponse(
                iter([resp.content]),
                media_type=resp.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        except httpx.TimeoutException:
            from fastapi import HTTPException
            raise HTTPException(status_code=504, detail="Image fetch timeout")
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# GET SEASONAL INFO
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/seasonal")
def get_seasonal_context():
    """Retourne le contexte saisonnier courant."""
    from ..services.scraper import _get_seasonal_context
    return _get_seasonal_context()

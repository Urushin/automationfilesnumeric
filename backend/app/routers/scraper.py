import json
import threading
import queue
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import IdeaBank
from app.services.scraper import run_full_scrape

router = APIRouter(prefix="/api/scraper", tags=["Trends Scraper"])

class TrendItemSchema(BaseModel):
    id: int
    title: str
    source_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    trend_score: int
    category: Optional[str] = None
    section: str = "trending"

    class Config:
        from_attributes = True

@router.get("/trends", response_model=List[TrendItemSchema])
def get_scraped_trends(
    limit: int = Query(150, ge=1, le=300),
    db: Session = Depends(get_db)
):
    """Retrieves all strictly validated trending product listings stored in IdeaBank."""
    try:
        results = db.query(IdeaBank).order_by(IdeaBank.trend_score.desc()).limit(limit).all()
        return results
    except Exception as e:
        # Graceful fallback to prevent server 500 error blowing up the UI dashboard
        return []

@router.get("/stream")
async def stream_scraping_job():
    """Streams the status of the scraping job to the client in real-time."""
    q = queue.Queue()

    def scraper_worker():
        db = SessionLocal()
        try:
            for progress_data in run_full_scrape(db):
                q.put(progress_data)
        except Exception as e:
            q.put({'step': 99, 'msg': f'Erreur inattendue: {str(e)}', 'done': True})
        finally:
            db.close()
            q.put(None)  # Signal de fin
            
    # On lance le scraping bloquant dans un thread séparé
    threading.Thread(target=scraper_worker, daemon=True).start()

    async def event_stream():
        # 1. Ping immédiat pour confirmer la connexion au navigateur
        yield f"data: {json.dumps({'step': 0, 'msg': 'Connexion établie, démarrage en cours...'})}\n\n"
        while True:
            try:
                while True:
                    data = q.get_nowait()
                    if data is None:
                        await asyncio.sleep(1.5)  # Donne le temps au frontend de fermer proprement
                        return
                    yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                pass
                
            # 2. Keep-alive pour empêcher Next.js/le navigateur de couper la connexion
            yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
    )
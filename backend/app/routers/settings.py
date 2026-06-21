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
            banana_key="",
            replicate_key="",
            openrouter_key="",
            huggingface_key="",
            anthropic_key="",
            stability_key="",
            image_ai_provider="banana",
            text_ai_provider="gemini-2.0-flash-lite",
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


from pydantic import BaseModel
from typing import Optional

class PromptsUpdateBody(BaseModel):
    prompt_seo: Optional[str] = None
    prompt_image_generation: Optional[str] = None
    prompt_inpainting: Optional[str] = None
    prompt_trend_scraping: Optional[str] = None

@router.get("/prompts")
def get_system_prompts(db: Session = Depends(get_db)):
    """
    Exposes all system backend prompts (SEO, Image Generation, Inpainting, Scraping).
    """
    settings = get_or_create_settings(db)
    from ..services.seo_engine import SEO_SYSTEM_PROMPT
    
    inpainting_prompt_def = (
        "You are an expert prompt engineer for Text-to-Image models (gpt-image-2 and Imagen 3).\n"
        "Your role is to write a revised and corrected image prompt in English based on visual feedback.\n"
        "You are modifying a black and white stencil design for laser cutting.\n"
        "Analyze the original base image and the current generated image.\n"
        "Generate a highly detailed, optimized prompt in English for the image generator "
        "describing the final corrected image. The design MUST remain a stark black and white stencil silhouette "
        "with all black parts connected. Include style instructions to make it clean.\n"
        "Return ONLY the plain text prompt, with no markdown, no quotes, and no introductory/concluding text."
    )
    
    image_gen_prompt_def = (
        "A professional, crisp e-commerce product photography of an empty interior wall mockup, straight-on centered shot, eye-level perspective. "
        "The main focus is a large, flat, completely empty wall made of a premium texture.\n"
        "STRICT VISUAL RULES:\n"
        "- The center of the wall MUST be completely blank, flat, and clear.\n"
        "- NO existing frames, NO canvases, NO paintings, NO wall clocks, NO shelves, and NO mirrors on the wall.\n"
        "- NO hanging pendant lights, NO overhead lights, NO plants overlapping the empty wall.\n"
        "- Soft, natural, ambient side-lighting from a realistic window creating clean, subtle depth. Photorealistic rendering, 8k resolution, uncluttered luxury aesthetic."
    )
    
    scraping_prompt_def = (
        "You are an expert market analyst in digital files and laser-cutting designs (SVG, DXF).\n"
        "Analyze the current date/season context.\n"
        "Generate 10 highly trending, original, and highly profitable concept ideas for digital laser-cut designs.\n"
        "For each concept, provide: Title (French), Description (French), Category, Trend Score, Keywords (5 relevant search keywords, French).\n"
        "Respond strictly with a JSON array of objects. Do not wrap it in markdown or add explanations."
    )
    
    p_seo = settings.prompt_seo if (settings.prompt_seo and settings.prompt_seo.strip()) else SEO_SYSTEM_PROMPT.strip()
    p_image = settings.prompt_image_generation if (settings.prompt_image_generation and settings.prompt_image_generation.strip()) else image_gen_prompt_def.strip()
    p_inpainting = settings.prompt_inpainting if (settings.prompt_inpainting and settings.prompt_inpainting.strip()) else inpainting_prompt_def.strip()
    p_scraping = settings.prompt_trend_scraping if (settings.prompt_trend_scraping and settings.prompt_trend_scraping.strip()) else scraping_prompt_def.strip()

    return [
        {
            "id": "seo",
            "title": "Etsy SEO Generation System Prompt",
            "description": "Used by the copywriting engine to generate optimized, bilingual titles, descriptions, and tag lists tailored for Etsy search algorithm requirements.",
            "prompt": p_seo
        },
        {
            "id": "image_generation",
            "title": "Mockup Background Backdrop Generation Prompt",
            "description": "Instructs DALL-E/GPT to produce empty premium room backdrops matching the theme, ready to receive composite stencils.",
            "prompt": p_image
        },
        {
            "id": "inpainting",
            "title": "Inpainting Correction & Guidance Prompt",
            "description": "Generates localized modification instructions when regenerating specific stencil zones using DALL-E edit endpoints.",
            "prompt": p_inpainting
        },
        {
            "id": "trend_scraping",
            "title": "Trend Scraper AI Concept Generation Prompt",
            "description": "Directs LLMs to analyze seasonal events and generate fresh, highly-converting design concepts in JSON format.",
            "prompt": p_scraping
        }
    ]


@router.post("/prompts")
def update_system_prompts(body: PromptsUpdateBody, db: Session = Depends(get_db)):
    """
    Updates the custom system prompts in the database settings.
    """
    settings = get_or_create_settings(db)
    if body.prompt_seo is not None:
        settings.prompt_seo = body.prompt_seo
    if body.prompt_image_generation is not None:
        settings.prompt_image_generation = body.prompt_image_generation
    if body.prompt_inpainting is not None:
        settings.prompt_inpainting = body.prompt_inpainting
    if body.prompt_trend_scraping is not None:
        settings.prompt_trend_scraping = body.prompt_trend_scraping
    db.commit()
    db.refresh(settings)
    return {"status": "success", "message": "Prompts updated successfully."}


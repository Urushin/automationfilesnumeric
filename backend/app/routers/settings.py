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
            stencil_image_provider="banana",
            mockup_image_provider="banana",
            stencil_image_quality="auto",
            mockup_image_quality="auto",
            text_ai_provider="gemini-2.0-flash-lite",
            etsy_client_id="",
            etsy_client_secret="",
            etsy_oauth_token="",
            default_price=3.0,
            default_quantity=999,
            default_status="draft",
            potrace_path="potrace",
            inkscape_path="inkscape",
            mockup_background_path="",
            watermark_text="digitalfilesbymop",
            default_apply_watermark=False,
            mockup_pack_count=4
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
    prompt_stencil_single: Optional[str] = None
    prompt_stencil_multiple: Optional[str] = None
    prompt_stencil_framed_filigree: Optional[str] = None
    prompt_vision_description: Optional[str] = None
    prompt_imagen3_negative_suffix: Optional[str] = None
    prompt_legacy_framed_filigree: Optional[str] = None
    prompt_legacy_classic: Optional[str] = None
    prompt_legacy_image_to_image: Optional[str] = None
    prompt_legacy_grad_cap: Optional[str] = None
    prompt_mockup_banana: Optional[str] = None
    prompt_mockup_dalle3: Optional[str] = None
    prompt_mockup_degraded: Optional[str] = None

@router.get("/prompts")
def get_system_prompts(db: Session = Depends(get_db)):
    """
    Exposes all system backend prompts (SEO, Image Generation, Inpainting, Scraping, Stencils, Legacy, Mockups).
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

    stencil_single_def = "A professional 2D flat vector silhouette stencil of {theme}. Pure solid black #000000 shapes on pristine solid white background #FFFFFF, clean lines."
    stencil_multiple_def = "An organized flash-sheet collection grid containing exactly {bundle_size} distinct variations of: {theme}. Grid layout, disconnected by wide white spaces. Pure black #000000 shapes on pristine white #FFFFFF background."
    stencil_framed_filigree_def = "Generate a strictly square image. Intricate stencil silhouette art based on: {final_prompt}."
    vision_description_def = "Describe the core subject, exact posture, layout, and shapes of this image in English for a silhouette stencil maker. Output ONLY the raw description, no prose."
    imagen3_negative_suffix_def = "\nABSOLUTELY NO: color, photo, 3d, rendering, drop shadow, inner shadow, gradient, shading, gray tones, realistic texture, sketch, blurry, floating parts, text, watermark, signature. Pure flat 2D graphic only."
    
    legacy_framed_filigree_def = (
        "Generate a strictly square image (1024x1024 resolution). An intricate, highly detailed, flat vector-style layered stencil silhouette art containing exactly {bundle_size} design(s) of '{theme}'. \n\n"
        "Strict Technical Constraints:\n"
        "- STRUCTURAL RING: The design MUST be entirely enclosed within a solid black circular outer frame ring acting as the primary structural support.\n"
        "- Solid black lines (#000000) on a pure white background (#FFFFFF) only. No gray, shadows, or gradients.\n"
        "- COMPLEX FILIGREE: Incorporate rich, elegant internal filigree and interlacing motifs.\n"
        "- ABSOLUTE STRUCTURAL INTEGRITY: Every internal element MUST be physically fused to neighboring lines or directly connected to the circular outer frame ring using clean, thick bridging joints. Zero floating islands. Optimized for flawless CNC routing."
    )
    legacy_classic_def = (
        "Generate a strictly square image (1024x1024 resolution). A crisp, perfect, flat vector-style silhouette bundle collection containing exactly {bundle_size} separate designs of '{theme}'. \n\n"
        "Strict Technical Constraints:\n"
        "- Solid black shapes and lines on a solid stark white background only. Pure black (#000000) on pure white (#FFFFFF).\n"
        "- CRITICAL STRUCTURAL CONSTRAINT: Every single black shape and element within each design MUST be physically connected to its main body to prevent floating islands. Must hold together as one connected piece for laser cutting.\n"
        "- Thick, clear, bold lines. NO gradients, shadows, grey pixels, sketchy lines, or text."
    )
    legacy_image_to_image_def = (
        "\n\nIMAGE-TO-IMAGE INSTRUCTIONS:\n"
        "- Treat the attached reference image strictly as a structural skeleton or shape template.\n"
        "- Output a flat 2D graphic only. Absolutely NO 3D effects, NO bevels, NO shadows, NO color gradients, and NO gray pixels. Every pixel must be either pure black #000000 or pure white #FFFFFF."
    )
    legacy_grad_cap_def = " Replicate the silhouette of a classic graduation cap / mortarboard from the reference, flattening it into a pure solid black silhouette shape on a stark white background."
    
    mockup_banana_def = (
        "E-commerce professional lifestyle presentation photography of a cozy room. "
        "A premium, beautiful wall (e.g. textured plaster, rustic wood paneling, or neat brick wall) "
        "where the physical matte black metal laser-cut silhouette design from the reference image is mounted flat on the wall. "
        "The room's architectural style, lighting, surrounding interior decor, and props must perfectly adapt to the theme of '{theme}'. \n\n"
        "CRITICAL VISUAL CONSTRAINT: \n"
        "The design outline from the reference image must be perfectly preserved and rendered as a physical matte black metal product on the wall, "
        "fully visible with soft, realistic drop shadows behind it. The environment must look highly cozy, realistic, and premium. Soft natural cinematic lighting. "
        "No other artwork, no text, no frames."
    )
    mockup_dalle3_def = (
        "Generate a strictly square image (1024x1024 resolution). E-commerce professional lifestyle presentation photography of a cozy room. "
        "A premium, beautiful empty wall (e.g. textured plaster, rustic wood paneling, or neat brick wall) suitable for displaying wall art. "
        "The room's architectural style, lighting, and surrounding interior decor must perfectly adapt to the theme of '{theme}'. "
        "CRITICAL BACKDROP RULE: The wall MUST be completely empty, flat, clean, and uncluttered. "
        "There must be NO artwork, NO text, NO frames, NO clocks, and NO shelves on the wall. The wall is ready for mounting a design. "
        "The environment must look highly cozy, realistic, and premium. Soft natural cinematic lighting. A clean empty space is essential."
    )
    mockup_degraded_def = "A crisp black and white silhouette stencil of '{theme}' as a physical wall art mounted on a modern room wall, professional catalog photo, premium lighting, high quality"
    
    p_seo = settings.prompt_seo if (settings.prompt_seo and settings.prompt_seo.strip()) else SEO_SYSTEM_PROMPT.strip()
    p_image = settings.prompt_image_generation if (settings.prompt_image_generation and settings.prompt_image_generation.strip()) else image_gen_prompt_def.strip()
    p_inpainting = settings.prompt_inpainting if (settings.prompt_inpainting and settings.prompt_inpainting.strip()) else inpainting_prompt_def.strip()
    p_scraping = settings.prompt_trend_scraping if (settings.prompt_trend_scraping and settings.prompt_trend_scraping.strip()) else scraping_prompt_def.strip()

    p_stencil_single = settings.prompt_stencil_single if (settings.prompt_stencil_single and settings.prompt_stencil_single.strip()) else stencil_single_def.strip()
    p_stencil_multiple = settings.prompt_stencil_multiple if (settings.prompt_stencil_multiple and settings.prompt_stencil_multiple.strip()) else stencil_multiple_def.strip()
    p_stencil_framed_filigree = settings.prompt_stencil_framed_filigree if (settings.prompt_stencil_framed_filigree and settings.prompt_stencil_framed_filigree.strip()) else stencil_framed_filigree_def.strip()
    p_vision_description = settings.prompt_vision_description if (settings.prompt_vision_description and settings.prompt_vision_description.strip()) else vision_description_def.strip()
    p_imagen3_negative_suffix = settings.prompt_imagen3_negative_suffix if (settings.prompt_imagen3_negative_suffix and settings.prompt_imagen3_negative_suffix.strip()) else imagen3_negative_suffix_def.strip()

    p_legacy_framed_filigree = settings.prompt_legacy_framed_filigree if (settings.prompt_legacy_framed_filigree and settings.prompt_legacy_framed_filigree.strip()) else legacy_framed_filigree_def.strip()
    p_legacy_classic = settings.prompt_legacy_classic if (settings.prompt_legacy_classic and settings.prompt_legacy_classic.strip()) else legacy_classic_def.strip()
    p_legacy_image_to_image = settings.prompt_legacy_image_to_image if (settings.prompt_legacy_image_to_image and settings.prompt_legacy_image_to_image.strip()) else legacy_image_to_image_def.strip()
    p_legacy_grad_cap = settings.prompt_legacy_grad_cap if (settings.prompt_legacy_grad_cap and settings.prompt_legacy_grad_cap.strip()) else legacy_grad_cap_def.strip()

    p_mockup_banana = settings.prompt_mockup_banana if (settings.prompt_mockup_banana and settings.prompt_mockup_banana.strip()) else mockup_banana_def.strip()
    p_mockup_dalle3 = settings.prompt_mockup_dalle3 if (settings.prompt_mockup_dalle3 and settings.prompt_mockup_dalle3.strip()) else mockup_dalle3_def.strip()
    p_mockup_degraded = settings.prompt_mockup_degraded if (settings.prompt_mockup_degraded and settings.prompt_mockup_degraded.strip()) else mockup_degraded_def.strip()

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
        },
        {
            "id": "stencil_single",
            "title": "Stencil - Single Design Prompt",
            "description": "Base prompt to generate a single B&W vector silhouette stencil from a text theme.",
            "prompt": p_stencil_single
        },
        {
            "id": "stencil_multiple",
            "title": "Stencil - Multiple Designs Prompt",
            "description": "Base prompt to generate a grid collection bundle of B&W stencils.",
            "prompt": p_stencil_multiple
        },
        {
            "id": "stencil_framed_filigree",
            "title": "Stencil - Framed Filigree Style Prefix",
            "description": "Used for framed filigree style stencil generations to enforce outer ring technical details.",
            "prompt": p_stencil_framed_filigree
        },
        {
            "id": "vision_description",
            "title": "Image-to-Image / Vision Description Prompt",
            "description": "Instructs GPT-4o-mini to extract a technical B&W description of a reference image.",
            "prompt": p_vision_description
        },
        {
            "id": "imagen3_negative_suffix",
            "title": "Imagen 3 Stencil Negative Suffix",
            "description": "Strict negative rules appended to Imagen 3 generations to prevent color, shadows, and 3D effects.",
            "prompt": p_imagen3_negative_suffix
        },
        {
            "id": "legacy_framed_filigree",
            "title": "Legacy Generator - Framed Filigree Prompt",
            "description": "Legacy generator prompt for framed filigree CNC-optimized stencil generation.",
            "prompt": p_legacy_framed_filigree
        },
        {
            "id": "legacy_classic",
            "title": "Legacy Generator - Classic Prompt",
            "description": "Legacy generator prompt for classic B&W silhouette bundle stencil generation.",
            "prompt": p_legacy_classic
        },
        {
            "id": "legacy_image_to_image",
            "title": "Legacy Generator - Image-to-Image Instruction",
            "description": "Legacy generator instructions added when performing image-to-image silhouette reference matching.",
            "prompt": p_legacy_image_to_image
        },
        {
            "id": "legacy_grad_cap",
            "title": "Legacy Generator - Graduation Cap Fallback",
            "description": "Legacy fallback instruction template to recreate a graduation cap silhouette.",
            "prompt": p_legacy_grad_cap
        },
        {
            "id": "mockup_banana",
            "title": "Mockup - Banana SDXL Room Prompt",
            "description": "Instructs Nano Banana (SDXL) to generate a lifestyle mockup room with a B&W stencil mounted as physical metal on the wall.",
            "prompt": p_mockup_banana
        },
        {
            "id": "mockup_dalle3",
            "title": "Mockup - DALL-E 3 / Generic Room Prompt",
            "description": "Generates a clean empty lifestyle backdrop room for composite mockup styling.",
            "prompt": p_mockup_dalle3
        },
        {
            "id": "mockup_degraded",
            "title": "Mockup - Degraded Fallback Prompt",
            "description": "Text-to-image fallback prompt to generate a mockup when the original stencil is missing.",
            "prompt": p_mockup_degraded
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
    if body.prompt_stencil_single is not None:
        settings.prompt_stencil_single = body.prompt_stencil_single
    if body.prompt_stencil_multiple is not None:
        settings.prompt_stencil_multiple = body.prompt_stencil_multiple
    if body.prompt_stencil_framed_filigree is not None:
        settings.prompt_stencil_framed_filigree = body.prompt_stencil_framed_filigree
    if body.prompt_vision_description is not None:
        settings.prompt_vision_description = body.prompt_vision_description
    if body.prompt_imagen3_negative_suffix is not None:
        settings.prompt_imagen3_negative_suffix = body.prompt_imagen3_negative_suffix
    if body.prompt_legacy_framed_filigree is not None:
        settings.prompt_legacy_framed_filigree = body.prompt_legacy_framed_filigree
    if body.prompt_legacy_classic is not None:
        settings.prompt_legacy_classic = body.prompt_legacy_classic
    if body.prompt_legacy_image_to_image is not None:
        settings.prompt_legacy_image_to_image = body.prompt_legacy_image_to_image
    if body.prompt_legacy_grad_cap is not None:
        settings.prompt_legacy_grad_cap = body.prompt_legacy_grad_cap
    if body.prompt_mockup_banana is not None:
        settings.prompt_mockup_banana = body.prompt_mockup_banana
    if body.prompt_mockup_dalle3 is not None:
        settings.prompt_mockup_dalle3 = body.prompt_mockup_dalle3
    if body.prompt_mockup_degraded is not None:
        settings.prompt_mockup_degraded = body.prompt_mockup_degraded
    db.commit()
    db.refresh(settings)
    return {"status": "success", "message": "Prompts updated successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# STORAGE STATS & PURGE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
import os
import shutil

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage"))


@router.get("/storage-stats")
def get_storage_stats(db: Session = Depends(get_db)):
    """Calculates disk storage statistics for storage/ directory."""
    if not os.path.exists(STORAGE_DIR):
        return {
            "total_size_mb": 0.0,
            "total_files": 0,
            "creation_folders_count": 0,
            "temp_files_count": 0,
            "temp_size_mb": 0.0,
        }

    total_size = 0
    total_files = 0
    temp_files_count = 0
    temp_size = 0
    creation_folders = set()

    for root, dirs, files in os.walk(STORAGE_DIR):
        for d in dirs:
            if d.startswith("creation_"):
                creation_folders.add(d)
        for f in files:
            if f.startswith("."):
                continue
            f_path = os.path.join(root, f)
            try:
                f_size = os.path.getsize(f_path)
                total_size += f_size
                total_files += 1

                # Check if it's a temporary cache/render file
                f_lower = f.lower()
                if (
                    f_lower.startswith("temp_")
                    or f_lower.endswith(".tmp")
                    or "_chunks" in root
                    or f_lower.startswith("test_")
                    or "temp_bg" in f_lower
                ):
                    temp_files_count += 1
                    temp_size += f_size
            except Exception:
                pass

    return {
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_files": total_files,
        "creation_folders_count": len(creation_folders),
        "temp_files_count": temp_files_count,
        "temp_size_mb": round(temp_size / (1024 * 1024), 2),
    }


@router.post("/purge-storage")
def purge_storage(db: Session = Depends(get_db)):
    """
    Cleans up temporary cache files, chunks, and temp backdrops from storage.
    Preserves all final user deliverables (SVG, DXF, AI, EPS, PDF, PNG, Mockups, ZIP).
    """
    if not os.path.exists(STORAGE_DIR):
        return {"status": "success", "deleted_files_count": 0, "freed_space_mb": 0.0}

    deleted_count = 0
    freed_bytes = 0

    for root, dirs, files in os.walk(STORAGE_DIR, topdown=False):
        # Remove temporary directories (_chunks, etc.)
        for d in dirs:
            if d in ["_chunks", "tmp", "temp"]:
                dir_path = os.path.join(root, d)
                try:
                    for sub_root, _, sub_files in os.walk(dir_path):
                        for sf in sub_files:
                            freed_bytes += os.path.getsize(os.path.join(sub_root, sf))
                            deleted_count += 1
                    shutil.rmtree(dir_path, ignore_errors=True)
                except Exception:
                    pass

        # Remove temporary files
        for f in files:
            f_lower = f.lower()
            if (
                f_lower.startswith("temp_")
                or f_lower.endswith(".tmp")
                or f_lower.startswith("test_")
                or "temp_bg" in f_lower
            ):
                f_path = os.path.join(root, f)
                try:
                    freed_bytes += os.path.getsize(f_path)
                    os.remove(f_path)
                    deleted_count += 1
                except Exception:
                    pass

    return {
        "status": "success",
        "deleted_files_count": deleted_count,
        "freed_space_mb": round(freed_bytes / (1024 * 1024), 2),
    }


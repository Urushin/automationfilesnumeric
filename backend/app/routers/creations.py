import os
import shutil
import requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db, SessionLocal
from ..models import Creation, Setting
from ..schemas import CreationResponse, CreationUpdate, PublishRequest
from ..services.image_engine import generate_stencil_image, split_multielement_image, local_binarize_image
from ..services.export_formats import svg_to_ai, svg_to_eps, svg_to_high_quality_png
from ..services.seo_engine import generate_etsy_seo
from ..services.mockup_engine import (
    generate_ai_mockup,
    composite_stencil_on_bg,
    create_real_mockup,
    generate_etsy_standard_mockup_pack,
    apply_watermark_to_image,
)
from ..services.svg_analyzer import (
    analyze_svg_connectivity,
    detect_floating_islands,
    generate_islands_overlay,
    auto_bridge_stencil,
)
from ..services.vector import png_to_svg, svg_to_dxf
from ..services.image import convert_to_transparent_png, package_assets, png_to_pdf
from ..services.etsy_api import publish_listing_to_etsy
from ..services.compliance import run_compliance_check
from .settings import get_or_create_settings
from pydantic import BaseModel
import re
import unicodedata

class TranslateSEORequest(BaseModel):
    text: str
    creation_id: str
    instructions: Optional[str] = None
    target_fields: List[str] = ["title", "description", "tags"] # e.g. ["title", "tags"]

class SelectVariantRequest(BaseModel):
    variant_path: str

class TranslateSEOResponse(BaseModel):
    status: str = "success"
    data: Optional[dict] = None
    title_en: str = ""
    description_en: str = ""
    tags_en: List[str] = []
    title_fr: str = ""
    description_fr: str = ""
    tags_fr: List[str] = []

router = APIRouter(prefix="/api/creations", tags=["creations"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage"))
os.makedirs(STORAGE_DIR, exist_ok=True)

@router.get("", response_model=List[CreationResponse])
def list_creations(db: Session = Depends(get_db)):
    return db.query(Creation).order_by(Creation.timestamp.desc()).all()

@router.get("/{creation_id}", response_model=CreationResponse)
def get_creation(creation_id: int, db: Session = Depends(get_db)):
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
    return creation

@router.put("/{creation_id}", response_model=CreationResponse)
def update_creation(creation_id: int, payload: CreationUpdate, db: Session = Depends(get_db)):
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(creation, key, value)
        
    db.commit()
    db.refresh(creation)
    return creation

@router.delete("/{creation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_creation(creation_id: int, db: Session = Depends(get_db)):
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    # Delete folder and its files
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    if os.path.exists(creation_dir):
        shutil.rmtree(creation_dir)
        
    db.delete(creation)
    db.commit()
    return None


class DeleteFileBody(BaseModel):
    file_path: str  # static URL like /static/creation_N/filename.jpg


@router.delete("/{creation_id}/file", response_model=CreationResponse)
def delete_creation_file(creation_id: int, body: DeleteFileBody, db: Session = Depends(get_db)):
    """Physically removes a generated file from disk and scrubs all DB references."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    file_path = body.file_path.strip()

    # Resolve static URL → filesystem path
    if file_path.startswith("/static/"):
        abs_path = os.path.join(STORAGE_DIR, file_path.replace("/static/", "", 1))
    else:
        abs_path = os.path.join(STORAGE_DIR, f"creation_{creation_id}", os.path.basename(file_path))

    # Physical deletion (non-blocking if already gone)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Impossible de supprimer le fichier : {e}")

    # ── Scrub from every DB path field ──────────────────────────────────────
    def _drop(raw: str | None) -> str:
        if not raw:
            return raw
        parts = [p.strip() for p in raw.split(",") if p.strip() and p.strip() != file_path]
        return ",".join(parts) if parts else None

    def _drop_first(current: str | None) -> str | None:
        if current and current.strip() == file_path:
            return None
        return current

    # Singular path fields
    creation.mockup_path = _drop_first(creation.mockup_path)
    creation.real_mockup_path = _drop_first(creation.real_mockup_path)
    creation.upscale_png_path = _drop_first(creation.upscale_png_path)
    creation.svg_path = _drop_first(creation.svg_path)
    creation.dxf_path = _drop_first(creation.dxf_path)
    creation.ai_path = _drop_first(creation.ai_path)
    creation.eps_path = _drop_first(creation.eps_path)
    creation.pdf_path = _drop_first(creation.pdf_path)
    creation.zip_path = _drop_first(creation.zip_path)
    creation.source_png_path = _drop_first(creation.source_png_path)

    # Comma-separated list fields (stored as _raw columns)
    creation.mockup_paths_raw = _drop(creation.mockup_paths_raw)
    creation.real_mockup_paths_raw = _drop(creation.real_mockup_paths_raw)
    creation.commercial_mockup_paths_raw = _drop(creation.commercial_mockup_paths_raw)
    creation.png_paths_raw = _drop(getattr(creation, "png_paths_raw", None))
    creation.svg_paths_raw = _drop(getattr(creation, "svg_paths_raw", None))
    creation.dxf_paths_raw = _drop(getattr(creation, "dxf_paths_raw", None))
    creation.ai_paths_raw = _drop(getattr(creation, "ai_paths_raw", None))
    creation.eps_paths_raw = _drop(getattr(creation, "eps_paths_raw", None))
    creation.pdf_paths_raw = _drop(getattr(creation, "pdf_paths_raw", None))

    # Also remove from selected_images_raw
    creation.selected_images_raw = _drop(creation.selected_images_raw)
    # And source_png_variants_raw
    creation.source_png_variants_raw = _drop(getattr(creation, "source_png_variants_raw", None))

    db.commit()
    db.refresh(creation)
    return creation


def _bg_global_pipeline(
    creation_id: int,
    theme: str,
    init_image_path: Optional[str],
    safe_theme: str,
    source_png: str,
    upscale_png: str,
    svg_path: str,
    dxf_path: str,
    pdf_path: str,
    mockup_path: str,
    zip_path: str,
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None
):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
        
        creation.status = "processing"
        creation.current_step = "Génération du stencil..."
        db.commit()

        settings = get_or_create_settings(db)
        image_provider = preferred_image_provider or settings.stencil_image_provider or settings.image_ai_provider
        text_provider = preferred_text_provider or settings.text_ai_provider
        
        # Step 1: Generate stencil image
        generate_stencil_image(
            image_provider,
            settings.banana_key,
            settings.openai_key,
            theme,
            source_png,
            init_image_path=init_image_path,
            gemini_key=settings.gemini_key,
            replicate_key=settings.replicate_key,
            openrouter_key=settings.openrouter_key,
            huggingface_key=settings.huggingface_key,
            quality=settings.stencil_image_quality,
            mockup_provider=settings.mockup_image_provider,
            mockup_quality=settings.mockup_image_quality
        )
        creation.source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
        creation.current_step = "Détourage & Résolution..."
        db.commit()

        # Step 2: Upscaling ×3
        convert_to_transparent_png(source_png, upscale_png, scale_factor=3)
        creation.upscale_png_path = f"/static/creation_{creation.id}/{safe_theme}.png"
        creation.current_step = "Vectorisation..."
        db.commit()

        # Step 3: Vectorisation
        png_to_svg(settings.potrace_path, upscale_png, svg_path)
        creation.svg_path = f"/static/creation_{creation.id}/{safe_theme}.svg"
        creation.current_step = "Conversion CAO..."
        db.commit()

        # Step 4: CAD Conversion
        svg_to_dxf(settings.inkscape_path, svg_path, dxf_path, png_source_path=source_png)
        creation.dxf_path = f"/static/creation_{creation.id}/{safe_theme}.dxf"
        creation.current_step = "Génération PDF..."
        db.commit()

        # Step 5: PDF Print Format
        png_src = upscale_png if os.path.exists(upscale_png) else source_png
        png_to_pdf(png_src, pdf_path)
        creation.pdf_path = f"/static/creation_{creation.id}/{safe_theme}.pdf"
        creation.current_step = "Génération du mockup..."
        db.commit()

        # Step 6: Mockup generation
        generate_ai_mockup(
            image_provider,
            settings.banana_key,
            settings.openai_key,
            upscale_png if os.path.exists(upscale_png) else source_png,
            theme,
            mockup_path,
            settings.gemini_key,
            replicate_key=settings.replicate_key,
            openrouter_key=settings.openrouter_key,
            huggingface_key=settings.huggingface_key
        )
        creation.mockup_path = f"/static/creation_{creation.id}/{safe_theme}_mockup.png"
        creation.current_step = "Création du ZIP..."
        db.commit()

        # Step 7: ZIP Packaging
        assets_to_zip = [svg_path, dxf_path, pdf_path, upscale_png]
        package_assets(assets_to_zip, zip_path)
        creation.zip_path = f"/static/creation_{creation.id}/{safe_theme}.zip"
        creation.current_step = "Rédaction SEO..."
        db.commit()

        # Step 8: Call SEO Copywriting
        seo = generate_etsy_seo(
            theme=theme,
            provider=text_provider,
            gemini_key=settings.gemini_key,
            mistral_key=settings.mistral_key,
            openai_key=settings.openai_key,
            replicate_key=settings.replicate_key,
            openrouter_key=settings.openrouter_key,
            huggingface_key=settings.huggingface_key,
            anthropic_key=settings.anthropic_key,
            db=db,
            image_path=upscale_png if os.path.exists(upscale_png) else source_png,
            bundle_size=creation.bundle_size or 4
        )
        creation.title_fr = seo.get("title_fr")
        creation.title_en = seo.get("title_en")
        creation.description = seo.get("description")
        creation.tags_fr = ",".join(seo.get("tags_fr", []))
        creation.tags_en = ",".join(seo.get("tags_en", []))
        
        creation.status = "completed"
        creation.current_step = "Terminé"
        db.commit()

    except Exception as e:
        print(f"Global pipeline background task failed: {e}")
        creation.status = "failed"
        creation.failed_reason = str(e)
        creation.current_step = "Échec"
        db.commit()
    finally:
        db.close()


def _bg_modular_pipeline(
    creation_id: int,
    theme: Optional[str],
    safe_theme: str,
    source_png: str,
    svg_path: str,
    dxf_path: str,
    pdf_path: str,
    upscale_png: str,
    mockup_path: str,
    real_mockup_path: str,
    zip_path: str,
    generate_ai_stencil: bool,
    vectorize: bool,
    convert_cad: bool,
    format_pdf: bool,
    upscale: bool,
    package: bool,
    generate_seo: bool,
    generate_real_mockup: bool,
    use_ai_mockup: bool,
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None
):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
        
        creation.status = "processing"
        creation.current_step = "Lancement..."
        db.commit()

        settings = get_or_create_settings(db)
        image_provider = preferred_image_provider or settings.stencil_image_provider or settings.image_ai_provider
        text_provider = preferred_text_provider or settings.text_ai_provider
        bundle_size = creation.bundle_size or 4
        source_type = creation.source_type or "text_prompt"

        inkscape_bin = settings.inkscape_path
        creation_dir = os.path.dirname(source_png)

        # ── PREPARATION / GENERATION ──
        if source_type == "vector_svg":
            # The uploaded file is saved as source_png, but it is an SVG file
            uploaded_file = source_png
            is_valid_svg = False
            if os.path.exists(uploaded_file):
                try:
                    with open(uploaded_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(1000).strip()
                        if "<svg" in content or "svg" in content.lower():
                            is_valid_svg = True
                except Exception:
                    pass

            if is_valid_svg:
                shutil.copy(uploaded_file, svg_path)
            
            svg_to_high_quality_png(inkscape_bin, svg_path, upscale_png, 300)
            if os.path.exists(upscale_png):
                shutil.copy(upscale_png, source_png)

            creation.svg_path = f"/static/creation_{creation.id}/{os.path.basename(svg_path)}"
            creation.source_png_path = f"/static/creation_{creation.id}/{os.path.basename(source_png)}"
            creation.upscale_png_path = f"/static/creation_{creation.id}/{os.path.basename(upscale_png)}"
            db.commit()

        elif source_type in ("raw_image", "ready_bw_image"):
            local_binarize_image(source_png, source_png)
            creation.source_png_path = f"/static/creation_{creation.id}/{os.path.basename(source_png)}"
            db.commit()

        elif source_type == "transparent_png":
            pass

        elif source_type == "text_prompt":
            if generate_ai_stencil:
                init_image_path = source_png + ".init.png"
                if os.path.exists(source_png):
                    shutil.copy(source_png, init_image_path)
                else:
                    init_image_path = None
                
                generate_stencil_image(
                    image_provider,
                    settings.banana_key,
                    settings.openai_key,
                    theme or "Design",
                    source_png,
                    init_image_path=init_image_path,
                    bundle_size=bundle_size,
                    gemini_key=settings.gemini_key,
                    replicate_key=settings.replicate_key,
                    openrouter_key=settings.openrouter_key,
                    huggingface_key=settings.huggingface_key,
                    vectorize=True,
                    quality=settings.stencil_image_quality,
                    mockup_provider=settings.mockup_image_provider,
                    mockup_quality=settings.mockup_image_quality
                )
                # local_binarize_image(source_png, source_png)
                creation.source_png_path = f"/static/creation_{creation.id}/{os.path.basename(source_png)}"
                db.commit()

        # ── ELEMENT SPLITTING (for bundle_size > 1) ──
        element_paths = []
        if bundle_size > 1 and source_type != "vector_svg":
            element_paths = split_multielement_image(source_png, creation_dir, bundle_size)
        
        if not element_paths:
            element_paths = [source_png]

        # Prepare elements list
        elements = []
        for idx, el_png in enumerate(element_paths):
            if len(element_paths) == 1:
                el_name = safe_theme
            else:
                el_name = f"{safe_theme}_{idx+1}"
            
            elements.append({
                "source_png": el_png,
                "base_name": el_name,
                "svg_path": os.path.join(creation_dir, f"{el_name}.svg"),
                "dxf_path": os.path.join(creation_dir, f"{el_name}.dxf"),
                "ai_path": os.path.join(creation_dir, f"{el_name}.ai"),
                "eps_path": os.path.join(creation_dir, f"{el_name}.eps"),
                "pdf_path": os.path.join(creation_dir, f"{el_name}.pdf"),
                "upscale_png": os.path.join(creation_dir, f"{el_name}.png"),
            })

        # Vectorize
        if source_type == "vector_svg":
            creation.svg_path = f"/static/creation_{creation.id}/{os.path.basename(svg_path)}"
            creation.svg_paths = [f"/static/creation_{creation.id}/{os.path.basename(svg_path)}"]
            db.commit()
        elif vectorize:
            creation.current_step = "Vectorisation..."
            db.commit()
            svg_urls = []
            for el in elements:
                png_to_svg(settings.potrace_path, el["source_png"], el["svg_path"])
                if os.path.exists(el["svg_path"]):
                    svg_urls.append(f"/static/creation_{creation.id}/{os.path.basename(el['svg_path'])}")
            creation.svg_path = svg_urls[0] if svg_urls else None
            creation.svg_paths = svg_urls
            db.commit()

        # CAD
        if convert_cad:
            creation.current_step = "Conversion CAO..."
            db.commit()
            dxf_urls, ai_urls, eps_urls = [], [], []
            for el in elements:
                if not os.path.exists(el["svg_path"]):
                    png_to_svg(settings.potrace_path, el["source_png"], el["svg_path"])
                svg_to_dxf(settings.inkscape_path, el["svg_path"], el["dxf_path"], png_source_path=el["source_png"])
                svg_to_ai(settings.inkscape_path, el["svg_path"], el["ai_path"])
                svg_to_eps(settings.inkscape_path, el["svg_path"], el["eps_path"])
                
                if os.path.exists(el["dxf_path"]):
                    dxf_urls.append(f"/static/creation_{creation.id}/{os.path.basename(el['dxf_path'])}")
                if os.path.exists(el["ai_path"]):
                    ai_urls.append(f"/static/creation_{creation.id}/{os.path.basename(el['ai_path'])}")
                if os.path.exists(el["eps_path"]):
                    eps_urls.append(f"/static/creation_{creation.id}/{os.path.basename(el['eps_path'])}")
            
            creation.dxf_path = dxf_urls[0] if dxf_urls else None
            creation.ai_path = ai_urls[0] if ai_urls else None
            creation.eps_path = eps_urls[0] if eps_urls else None
            db.commit()

        # Upscale
        if upscale or generate_real_mockup:
            creation.current_step = "Upscaling..."
            db.commit()
            png_urls = []
            for el in elements:
                hq_ok = False
                if os.path.exists(el["svg_path"]):
                    hq_ok = svg_to_high_quality_png(settings.inkscape_path, el["svg_path"], el["upscale_png"], 300)
                if not hq_ok:
                    convert_to_transparent_png(el["source_png"], el["upscale_png"], scale_factor=3)
                if os.path.exists(el["upscale_png"]):
                    png_urls.append(f"/static/creation_{creation.id}/{os.path.basename(el['upscale_png'])}")
            
            creation.upscale_png_path = png_urls[0] if png_urls else None
            creation.png_paths = png_urls
            db.commit()

        # PDF
        if format_pdf:
            creation.current_step = "Génération PDF..."
            db.commit()
            pdf_urls = []
            for el in elements:
                png_src = el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"]
                png_to_pdf(png_src, el["pdf_path"])
                if os.path.exists(el["pdf_path"]):
                    pdf_urls.append(f"/static/creation_{creation.id}/{os.path.basename(el['pdf_path'])}")
            creation.pdf_path = pdf_urls[0] if pdf_urls else None
            creation.pdf_paths = pdf_urls
            db.commit()

        # Standardized 4-Image Etsy Marketing Pack
        if generate_real_mockup:
            creation.current_step = "Génération du pack 4 visuels Etsy..."
            db.commit()

            parsed_styles = []
            if creation.mockup_styles:
                try:
                    parsed_styles = json.loads(creation.mockup_styles)
                except Exception:
                    parsed_styles = [x.strip() for x in creation.mockup_styles.split(",") if x.strip()]
            selected_style = parsed_styles[0] if parsed_styles else "classic_living_room"

            png_for_mockup = (
                upscale_png if os.path.exists(upscale_png)
                else (binarized_png if os.path.exists(binarized_png) else source_png)
            )

            watermark_text = getattr(settings, "watermark_text", "digitalfilesbymop") or "digitalfilesbymop"
            apply_wm = getattr(creation, "apply_watermark", False) or getattr(settings, "default_apply_watermark", False)

            pack_result = generate_etsy_standard_mockup_pack(
                stencil_path=png_for_mockup,
                output_dir=creation_dir,
                theme=creation.theme or "Design",
                bundle_size=creation.bundle_size or 1,
                bg_style=selected_style,
                apply_watermark=apply_wm,
                watermark_text=watermark_text
            )

            all_raw_paths = [f"/static/creation_{creation.id}/{os.path.basename(p)}" for p in pack_result["all_paths"]]
            first_raw_path = all_raw_paths[0] if all_raw_paths else None

            if first_raw_path:
                creation.mockup_path = first_raw_path
                existing_mockups = creation.mockup_paths or []
                for path in all_raw_paths:
                    if path not in existing_mockups:
                        existing_mockups.append(path)
                creation.mockup_paths = existing_mockups

            creation.real_mockup_path = None
            creation.real_mockup_paths = []
            db.commit()


        # ZIP
        if package:
            creation.current_step = "Création du ZIP..."
            db.commit()
            assets_to_zip = []
            for el in elements:
                for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                    p = el[path_key]
                    if p and os.path.exists(p):
                        assets_to_zip.append(p)
            
            mockups_to_zip = creation.mockup_paths or []
            for raw_p in mockups_to_zip:
                full_raw_p = os.path.join(creation_dir, os.path.basename(raw_p))
                if os.path.exists(full_raw_p):
                    assets_to_zip.append(full_raw_p)
            
            assets_to_zip = list(dict.fromkeys(assets_to_zip))
            package_assets(assets_to_zip, zip_path)
            creation.zip_path = f"/static/creation_{creation.id}/{safe_theme}.zip"
            db.commit()

        # Copywriting
        if generate_seo and theme:
            creation.current_step = "Rédaction SEO..."
            db.commit()
            seo = generate_etsy_seo(
                theme=theme,
                provider=text_provider,
                gemini_key=settings.gemini_key,
                mistral_key=settings.mistral_key,
                openai_key=settings.openai_key,
                replicate_key=settings.replicate_key,
                openrouter_key=settings.openrouter_key,
                huggingface_key=settings.huggingface_key,
                anthropic_key=settings.anthropic_key,
                db=db,
                image_path=source_png,
                bundle_size=bundle_size
            )
            creation.title_fr = seo.get("title_fr")
            creation.title_en = seo.get("title_en")
            creation.description = seo.get("description")
            creation.tags_fr = ",".join(seo.get("tags_fr", []))
            creation.tags_en = ",".join(seo.get("tags_en", []))

        creation.status = "completed"
        creation.current_step = "Terminé"
        db.commit()

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Modular pipeline background task failed: {e}")
        creation.status = "failed"
        creation.failed_reason = str(e)
        creation.current_step = "Échec"
        db.commit()
    finally:
        db.close()


@router.post("/global", response_model=CreationResponse)
def run_global_pipeline(
    background_tasks: BackgroundTasks,
    theme: str = Form(...), 
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    preferred_image_provider: Optional[str] = Form(None),
    preferred_text_provider: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    MODE A: PIPELINE GLOBAL (AUTOMATIC)
    1. Create database row.
    2. Start asynchronous pipeline processing in the background.
    3. Return response immediately.
    """
    settings = get_or_create_settings(db)
    
    # 1. Create DB entry to get ID
    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
        current_step="Création en attente..."
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)
    
    # Setup directories
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)
    
    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme).strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation.id}"

    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    svg_path = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path = os.path.join(creation_dir, f"{safe_theme}.dxf")
    pdf_path = os.path.join(creation_dir, f"{safe_theme}.pdf")
    upscale_png = os.path.join(creation_dir, f"{safe_theme}.png")
    mockup_path = os.path.join(creation_dir, f"{safe_theme}_mockup.png")
    zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
    
    init_image_path = None
    if file:
        init_image_path = os.path.join(creation_dir, "init_image.png")
        with open(init_image_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    elif image_url:
        init_image_path = os.path.join(creation_dir, "init_image.png")
        try:
            resp = requests.get(image_url, timeout=15)
            resp.raise_for_status()
            with open(init_image_path, "wb") as f:
                f.write(resp.content)
        except Exception as e:
            print(f"Warning: Could not download init image from URL: {e}")
            init_image_path = None

    background_tasks.add_task(
        _bg_global_pipeline,
        creation.id,
        theme,
        init_image_path,
        safe_theme,
        source_png,
        upscale_png,
        svg_path,
        dxf_path,
        pdf_path,
        mockup_path,
        zip_path,
        preferred_image_provider,
        preferred_text_provider
    )
    
    return creation


@router.post("/modular", response_model=CreationResponse)
def run_modular_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    theme: Optional[str] = Form(None),
    generate_ai_stencil: bool = Form(False),
    vectorize: bool = Form(False),
    convert_cad: bool = Form(False),
    format_pdf: bool = Form(False),
    upscale: bool = Form(False),
    package: bool = Form(False),
    generate_seo: bool = Form(False),
    generate_real_mockup: bool = Form(False),
    use_ai_mockup: bool = Form(False),
    preferred_image_provider: Optional[str] = Form(None),
    preferred_text_provider: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    MODE B: MODE MODULAIRE (À LA CARTE)
    1. Save uploaded file as source image.
    2. Start asynchronous pipeline processing for selected modules in the background.
    3. Return response immediately.
    """
    settings = get_or_create_settings(db)
    
    # Validation
    if generate_seo and not theme:
        raise HTTPException(
            status_code=400,
            detail="Theme field is required if SEO Copywriting is checked."
        )
        
    # Create DB entry
    creation = Creation(
        theme=theme or "Fichier Importé",
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
        current_step="Création en attente..."
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)
    
    # Setup directory
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)
    
    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme or "Fichier Importé").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation.id}"

    # Save uploaded file
    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    with open(source_png, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    creation.source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
    db.commit()
    
    svg_path = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path = os.path.join(creation_dir, f"{safe_theme}.dxf")
    pdf_path = os.path.join(creation_dir, f"{safe_theme}.pdf")
    upscale_png = os.path.join(creation_dir, f"{safe_theme}.png")
    mockup_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
    real_mockup_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
    zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
    
    background_tasks.add_task(
        _bg_modular_pipeline,
        creation.id,
        theme,
        safe_theme,
        source_png,
        svg_path,
        dxf_path,
        pdf_path,
        upscale_png,
        mockup_path,
        real_mockup_path,
        zip_path,
        generate_ai_stencil,
        vectorize,
        convert_cad,
        format_pdf,
        upscale,
        package,
        generate_seo,
        generate_real_mockup,
        use_ai_mockup,
        preferred_image_provider,
        preferred_text_provider
    )
    
    return creation

@router.post("/{creation_id}/publish")
def publish_creation_etsy(creation_id: int, payload: Optional[PublishRequest] = None, db: Session = Depends(get_db)):
    """Triggers publication to Etsy shop listing after compliance and guardrail checks."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    if payload is not None and payload.selected_assets is not None:
        creation.selected_images_raw = ",".join(payload.selected_assets)
        db.commit()
        db.refresh(creation)

    settings = get_or_create_settings(db)

    # ── Guardrails format ─────────────────────────────────────────────────
    missing = []
    if not creation.title_fr: missing.append("Titre FR")
    if not creation.title_en: missing.append("Titre EN")
    if not creation.description: missing.append("Description FR")
    if not creation.mockup_path: missing.append("Image Mockup")
    if not creation.zip_path: missing.append("Fichier Client ZIP")
    if creation.title_en and len(creation.title_en) > 140:
        missing.append("Titre EN dépasse 140 caractères")

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Publication bloquée. Éléments obligatoires manquants : {', '.join(missing)}"
        )

    # ── Compliance check ─────────────────────────────────────────────────
    compliance = run_compliance_check(
        title_fr=creation.title_fr or "",
        title_en=creation.title_en or "",
        description=creation.description or "",
        description_en=creation.description_en or "",
        tags_fr=creation.tags_fr or "",
        tags_en=creation.tags_en or "",
    )
    critical_warnings = [w for w in compliance.warnings if w.level == "CRITICAL"]
    if critical_warnings:
        details = "; ".join(w.message for w in critical_warnings)
        raise HTTPException(
            status_code=400,
            detail=f"Publication bloquée — Conformité Etsy : {details}"
        )

    try:
        result = publish_listing_to_etsy(settings, creation, db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Échec de publication Etsy : {str(e)}"
        )

import platform
from fastapi.responses import FileResponse

@router.get("/{creation_id}/download/{file_type}")
def download_creation_file(creation_id: int, file_type: str, filename: Optional[str] = None, db: Session = Depends(get_db)):
    """Forces browser local download by returning files with attachment headers."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Création introuvable.")
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    
    if filename:
        safe_name = os.path.basename(filename)
        file_path = os.path.join(creation_dir, safe_name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Fichier {safe_name} introuvable.")
        return FileResponse(
            path=file_path,
            filename=safe_name,
            headers={"Content-Disposition": f"attachment; filename={safe_name}"}
        )
        
    db_fields = {
        "svg": creation.svg_path,
        "dxf": creation.dxf_path,
        "ai": creation.ai_path,
        "eps": creation.eps_path,
        "pdf": creation.pdf_path,
        "png": creation.upscale_png_path,
        "zip": creation.zip_path,
        "raw": creation.source_png_path,
        "mockup": creation.mockup_path,
        "real_mockup": creation.real_mockup_path,
    }
    
    if file_type not in db_fields:
        raise HTTPException(status_code=400, detail="Type de fichier invalide.")
        
    db_path = db_fields[file_type]
    if not db_path:
        raise HTTPException(status_code=404, detail=f"Fichier {file_type} non généré.")
        
    file_name = os.path.basename(db_path)
    file_path = os.path.join(creation_dir, file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Fichier {file_name} introuvable.")
        
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream"
    )

@router.post("/{creation_id}/open-folder")
def open_creation_folder(creation_id: int, db: Session = Depends(get_db)):
    """Opens the local storage directory in the host OS file explorer (Finder/Explorer)."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Création introuvable.")
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    if not os.path.exists(creation_dir):
        raise HTTPException(status_code=404, detail="Dossier de création inexistant.")
        
    try:
        current_os = platform.system()
        if current_os == "Darwin":  # macOS
            import subprocess
            subprocess.run(["open", creation_dir])
        elif current_os == "Windows":
            os.startfile(creation_dir)
        else:  # Linux / Unix
            import subprocess
            subprocess.run(["xdg-open", creation_dir])
        return {"success": True, "message": "Dossier ouvert."}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible d'ouvrir le dossier local: {str(e)}"
        )

@router.post("/{creation_id}/open-file")
def open_creation_file(creation_id: int, file_url: str, db: Session = Depends(get_db)):
    """Opens a specific file in the host OS default viewer."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Création introuvable.")
        
    import urllib.parse
    parsed_url = urllib.parse.unquote(file_url)
    
    if parsed_url.startswith("/static/"):
        relative_path = parsed_url.replace("/static/", "")
        local_path = os.path.abspath(os.path.join(STORAGE_DIR, relative_path))
    else:
        raise HTTPException(status_code=400, detail="URL de fichier invalide.")
        
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le disque.")
        
    try:
        current_os = platform.system()
        if current_os == "Darwin":  # macOS
            import subprocess
            subprocess.run(["open", local_path])
        elif current_os == "Windows":
            os.startfile(local_path)
        else:  # Linux / Unix
            import subprocess
            subprocess.run(["xdg-open", local_path])
        return {"success": True, "message": "Fichier ouvert."}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible d'ouvrir le fichier: {str(e)}"
        )

@router.post("/{creation_id}/regenerate-seo", response_model=CreationResponse)
def regenerate_creation_seo(creation_id: int, db: Session = Depends(get_db)):
    """Regenerates bilingual SEO titles, description and tags for a creation."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    settings = get_or_create_settings(db)
    
    from ..services.seo_engine import generate_etsy_seo
    
    source_img_path = None
    if creation.upscale_png_path:
        relative_path = creation.upscale_png_path.replace("/static/", "")
        source_img_path = os.path.join(STORAGE_DIR, relative_path)
    
    if not source_img_path or not os.path.exists(source_img_path):
        if creation.source_png_path:
            relative_path = creation.source_png_path.replace("/static/", "")
            source_img_path = os.path.join(STORAGE_DIR, relative_path)
            
    if source_img_path and not os.path.exists(source_img_path):
        source_img_path = None
            
    try:
        seo = generate_etsy_seo(
            theme=creation.theme or "Design",
            provider=settings.text_ai_provider,
            gemini_key=settings.gemini_key,
            mistral_key=settings.mistral_key,
            openai_key=settings.openai_key,
            replicate_key=settings.replicate_key,
            openrouter_key=settings.openrouter_key,
            huggingface_key=settings.huggingface_key,
            anthropic_key=settings.anthropic_key,
            db=db,
            image_path=source_img_path,
            bundle_size=creation.bundle_size or 4
        )
        
        creation.title_fr = seo.get("title_fr")
        creation.title_en = seo.get("title_en")
        creation.description = seo.get("description_fr") or seo.get("description")
        creation.description_en = seo.get("description_en")
        creation.tags_fr = ",".join(seo.get("tags_fr", []))
        creation.tags_en = ",".join(seo.get("tags_en", []))
        
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate SEO: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# GRANULAR REGENERATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel

class InstructionsBody(BaseModel):
    instructions: Optional[str] = None
    use_ai_mockup: Optional[bool] = None
    bundle_size: Optional[int] = None
    vectorize: Optional[bool] = None
    apply_tp_overlay: Optional[bool] = None
    theme: Optional[str] = None
    n_images: Optional[int] = None
    mockup_styles: Optional[List[str]] = None

@router.post("/{creation_id}/regenerate-image", response_model=CreationResponse)
def regenerate_creation_image(
    creation_id: int, 
    body: Optional[InstructionsBody] = None, 
    db: Session = Depends(get_db)
):
    """Regenerates the source stencil image, optionally guided by user instructions and multimodal analysis."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    settings = get_or_create_settings(db)
    
    import re
    import shutil
    from ..services.image_engine import generate_stencil_image, regenerate_stencil_image_guided
    
    if body and body.theme is not None:
        creation.theme = body.theme
        db.commit()

    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    os.makedirs(creation_dir, exist_ok=True)
    
    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    init_png = source_png + ".init.png"
    
    # Save a copy as init.png if it does not exist yet to keep a history of the first generation
    if os.path.exists(source_png) and not os.path.exists(init_png):
        shutil.copy(source_png, init_png)
        
    instructions = body.instructions if body else None
    if body and body.bundle_size is not None:
        creation.bundle_size = body.bundle_size
        db.commit()
    
    try:
        import time
        ts = int(time.time())
        new_source_png = os.path.join(creation_dir, f"{safe_theme}_source_{ts}.png")

        vectorize_flag = body.vectorize if (body and body.vectorize is not None) else True
        if instructions and instructions.strip():
            # Guided correction using Gemini Multimodal + Image Gen
            current_image = source_png
            if creation.source_png_path:
                local_curr = os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
                if os.path.exists(local_curr):
                    current_image = local_curr

            regenerate_stencil_image_guided(
                provider=settings.stencil_image_provider or settings.image_ai_provider,
                banana_key=settings.banana_key,
                openai_key=settings.openai_key,
                theme=creation.theme or "Design",
                current_image_path=current_image,
                init_image_path=init_png if os.path.exists(init_png) else current_image,
                instructions=instructions,
                output_path=new_source_png,
                bundle_size=creation.bundle_size or 4,
                gemini_key=settings.gemini_key,
                replicate_key=settings.replicate_key,
                openrouter_key=settings.openrouter_key,
                huggingface_key=settings.huggingface_key,
                vectorize=vectorize_flag,
                quality=settings.stencil_image_quality,
                mockup_provider=settings.mockup_image_provider,
                mockup_quality=settings.mockup_image_quality
            )
            new_static = f"/static/creation_{creation_id}/{os.path.basename(new_source_png)}"
            creation.source_png_path = new_static
            existing_variants = creation.source_png_variants or []
            if new_static not in existing_variants:
                existing_variants.append(new_static)
            creation.source_png_variants = existing_variants
        else:
            # Simple regeneration
            res = generate_stencil_image(
                provider=settings.stencil_image_provider or settings.image_ai_provider,
                banana_key=settings.banana_key,
                openai_key=settings.openai_key,
                theme=creation.theme or "Design",
                output_path=new_source_png,
                init_image_path=init_png if os.path.exists(init_png) else None,
                bundle_size=creation.bundle_size or 4,
                gemini_key=settings.gemini_key,
                replicate_key=settings.replicate_key,
                openrouter_key=settings.openrouter_key,
                huggingface_key=settings.huggingface_key,
                vectorize=vectorize_flag,
                n_images=body.n_images if (body and body.n_images) else 1,
                quality=settings.stencil_image_quality,
                mockup_provider=settings.mockup_image_provider,
                mockup_quality=settings.mockup_image_quality
            )
            raw_saved_paths = res.get("saved_paths", []) if isinstance(res, dict) else [new_source_png]
            static_variants = [f"/static/creation_{creation_id}/{os.path.basename(p)}" for p in raw_saved_paths]
            
            if static_variants:
                creation.source_png_path = static_variants[0]
            existing_variants = creation.source_png_variants or []
            for v in static_variants:
                if v not in existing_variants:
                    existing_variants.append(v)
            creation.source_png_variants = existing_variants
            
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate image: {str(e)}")

@router.post("/{creation_id}/regenerate-vector", response_model=CreationResponse)
def regenerate_creation_vector(creation_id: int, db: Session = Depends(get_db)):
    """Runs binarization and vectorization (PNG to SVG)."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    settings = get_or_create_settings(db)
    
    import re
    from PIL import Image, ImageFilter
    from ..services.vector import png_to_svg, _otsu_threshold
    from ..services.svg_analyzer import analyze_svg_connectivity
    
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    import time
    ts = int(time.time())

    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    if creation.source_png_path:
        local_src = os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
        if os.path.exists(local_src):
            source_png = local_src

    binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized_{ts}.png")
    svg_path = os.path.join(creation_dir, f"{safe_theme}_{ts}.svg")
    
    if not os.path.exists(source_png):
        raise HTTPException(status_code=400, detail="Source image does not exist. Please generate image first.")
        
    try:
        # Binarize
        with Image.open(source_png) as img:
            gray = img.convert("L")
            gray = gray.filter(ImageFilter.GaussianBlur(radius=1.0))
            threshold = _otsu_threshold(gray)
            mono = gray.point(lambda x: 0 if x < threshold else 255, mode="1")
            mono.convert("RGB").save(binarized_png, "PNG")
            
        # Vectorize
        png_to_svg(settings.potrace_path, binarized_png, svg_path, settings.inkscape_path)
        
        # Analyze islands
        connectivity = analyze_svg_connectivity(svg_path)
        island_count = connectivity.get("island_count", 0)
        
        new_svg = f"/static/creation_{creation_id}/{os.path.basename(svg_path)}"
        creation.svg_path = new_svg
        creation.connectivity_warnings = max(0, island_count - 1)
        
        existing_svgs = creation.svg_paths or []
        if new_svg not in existing_svgs:
            existing_svgs.append(new_svg)
        creation.svg_paths = existing_svgs
        
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to vectorize: {str(e)}")

@router.post("/{creation_id}/regenerate-cad", response_model=CreationResponse)
def regenerate_creation_cad(creation_id: int, db: Session = Depends(get_db)):
    """Runs CAD conversions (SVG to DXF, AI, EPS)."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    settings = get_or_create_settings(db)
    
    import re
    from ..services.vector import svg_to_dxf
    from ..services.export_formats import svg_to_ai, svg_to_eps
    
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    import time
    ts = int(time.time())

    svg_path = os.path.join(creation_dir, f"{safe_theme}.svg")
    if creation.svg_path:
        local_svg = os.path.join(STORAGE_DIR, creation.svg_path.replace("/static/", ""))
        if os.path.exists(local_svg):
            svg_path = local_svg

    # Try to find a binarized PNG to align with Inkscape CLI requirements
    binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
    
    dxf_path = os.path.join(creation_dir, f"{safe_theme}_{ts}.dxf")
    ai_path = os.path.join(creation_dir, f"{safe_theme}_{ts}.ai")
    eps_path = os.path.join(creation_dir, f"{safe_theme}_{ts}.eps")
    
    if not os.path.exists(svg_path):
        raise HTTPException(status_code=400, detail="SVG file does not exist. Please run vectorization first.")
        
    try:
        svg_to_dxf(settings.inkscape_path, svg_path, dxf_path, binarized_png if os.path.exists(binarized_png) else svg_path)
        svg_to_ai(settings.inkscape_path, svg_path, ai_path)
        svg_to_eps(settings.inkscape_path, svg_path, eps_path)
        
        new_dxf = f"/static/creation_{creation_id}/{os.path.basename(dxf_path)}" if os.path.exists(dxf_path) else None
        new_ai = f"/static/creation_{creation_id}/{os.path.basename(ai_path)}" if os.path.exists(ai_path) else None
        new_eps = f"/static/creation_{creation_id}/{os.path.basename(eps_path)}" if os.path.exists(eps_path) else None
        
        if new_dxf:
            creation.dxf_path = new_dxf
            existing_dxfs = creation.dxf_paths or []
            if new_dxf not in existing_dxfs:
                existing_dxfs.append(new_dxf)
            creation.dxf_paths = existing_dxfs
            
        if new_ai:
            creation.ai_path = new_ai
            existing_ais = creation.ai_paths or []
            if new_ai not in existing_ais:
                existing_ais.append(new_ai)
            creation.ai_paths = existing_ais
            
        if new_eps:
            creation.eps_path = new_eps
            existing_epss = creation.eps_paths or []
            if new_eps not in existing_epss:
                existing_epss.append(new_eps)
            creation.eps_paths = existing_epss
        
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CAD formats: {str(e)}")

@router.post("/{creation_id}/regenerate-upscale", response_model=CreationResponse)
def regenerate_creation_upscale(creation_id: int, db: Session = Depends(get_db)):
    """Runs x3 PNG high resolution upscale."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    settings = get_or_create_settings(db)
    
    import re
    from ..services.image import convert_to_transparent_png
    from ..services.export_formats import svg_to_high_quality_png
    
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    import time
    ts = int(time.time())

    svg_path = os.path.join(creation_dir, f"{safe_theme}.svg")
    if creation.svg_path:
        local_svg = os.path.join(STORAGE_DIR, creation.svg_path.replace("/static/", ""))
        if os.path.exists(local_svg):
            svg_path = local_svg

    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    if creation.source_png_path:
        local_src = os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
        if os.path.exists(local_src):
            source_png = local_src

    binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
    upscale_png = os.path.join(creation_dir, f"{safe_theme}_{ts}.png")
    
    try:
        hq_ok = False
        if os.path.exists(svg_path):
            hq_ok = svg_to_high_quality_png(settings.inkscape_path, svg_path, upscale_png, 300)
        
        if not hq_ok:
            ref_png = binarized_png if os.path.exists(binarized_png) else source_png
            if not os.path.exists(ref_png):
                raise HTTPException(status_code=400, detail="No source image found to upscale.")
            convert_to_transparent_png(ref_png, upscale_png, 3)
            
        new_upscale = f"/static/creation_{creation_id}/{os.path.basename(upscale_png)}"
        creation.upscale_png_path = new_upscale
        
        existing_pngs = creation.png_paths or []
        if new_upscale not in existing_pngs:
            existing_pngs.append(new_upscale)
        creation.png_paths = existing_pngs

        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upscale image: {str(e)}")

@router.post("/{creation_id}/regenerate-pdf", response_model=CreationResponse)
def regenerate_creation_pdf(creation_id: int, db: Session = Depends(get_db)):
    """Runs PDF high quality conversion."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    import re
    from ..services.image import png_to_pdf
    
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    import time
    ts = int(time.time())

    upscale_png = os.path.join(creation_dir, f"{safe_theme}.png")
    if creation.upscale_png_path:
        local_upscale = os.path.join(STORAGE_DIR, creation.upscale_png_path.replace("/static/", ""))
        if os.path.exists(local_upscale):
            upscale_png = local_upscale

    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    if creation.source_png_path:
        local_src = os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
        if os.path.exists(local_src):
            source_png = local_src

    pdf_path = os.path.join(creation_dir, f"{safe_theme}_{ts}.pdf")
    
    ref_png = upscale_png if os.path.exists(upscale_png) else source_png
    if not os.path.exists(ref_png):
        raise HTTPException(status_code=400, detail="No source image found to generate PDF.")
        
    svg_path = os.path.join(creation_dir, f"{safe_theme}.svg")
    if creation.svg_path:
        local_svg = os.path.join(STORAGE_DIR, creation.svg_path.replace("/static/", ""))
        if os.path.exists(local_svg):
            svg_path = local_svg

    try:
        from ..services.vector import svg_to_pdf
        svg_to_pdf(settings.inkscape_path, svg_path, pdf_path, ref_png)
        new_pdf = f"/static/creation_{creation_id}/{os.path.basename(pdf_path)}"
        creation.pdf_path = new_pdf
        
        existing_pdfs = creation.pdf_paths or []
        if new_pdf not in existing_pdfs:
            existing_pdfs.append(new_pdf)
        creation.pdf_paths = existing_pdfs

        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.post("/{creation_id}/regenerate-mockup", response_model=CreationResponse)
def regenerate_creation_mockup(
    creation_id: int, 
    body: Optional[InstructionsBody] = None, 
    db: Session = Depends(get_db)
):
    """Regenerates mockup, optionally with AI instructions if use_ai_mockup is enabled."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    settings = get_or_create_settings(db)
    
    import re
    from ..services.mockup_engine import composite_stencil_on_bg
    
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    import time
    ts = int(time.time())
    apply_tp = body.apply_tp_overlay if (body and body.apply_tp_overlay is not None) else False

    upscale_png = os.path.join(creation_dir, f"{safe_theme}.png")
    if creation.upscale_png_path:
        local_upscale = os.path.join(STORAGE_DIR, creation.upscale_png_path.replace("/static/", ""))
        if os.path.exists(local_upscale):
            upscale_png = local_upscale

    source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
    if creation.source_png_path:
        local_src = os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
        if os.path.exists(local_src):
            source_png = local_src
            
    ref_png = upscale_png if os.path.exists(upscale_png) else source_png
    if not os.path.exists(ref_png):
        raise HTTPException(status_code=400, detail="No source image found to generate mockup.")
        
    instructions = body.instructions if body else None
    
    # Mockup style prompt definitions
    MOCKUP_STYLE_PROMPTS = {
        "classic_living_room": "A professional product photography of a modern luxury living room, elegant sofa, warm ambient light, with a large blank concrete wall in the center.",
        "modern_bedroom": "A professional product photography of a minimalist Scandinavian bedroom, cozy linen bedding, warm wooden side table, with a large blank plaster wall in the center.",
        "industrial_loft": "A professional product photography of a spacious industrial loft, brick wall, steel accents, large windows, with a large blank dark brick wall in the center.",
        "scandinavian_office": "A professional product photography of a Scandinavian design home office, minimalist light wood desk, plants, with a large blank white wall in the center.",
        "boho_chic": "A professional product photography of a cozy bohemian living room, rattan furniture, warm textiles, pampas grass, with a large blank beige wall in the center.",
        "industrial": "A professional product photography of an industrial style room, raw brick walls, black steel windows, concrete floor, minimalist decor, with a large blank industrial wall in the center.",
        "luxury_wood": "A professional product photography of a luxurious room with dark wood paneling, warm ambient spotlights, high-end design furniture, with a large blank dark wooden wall in the center.",
        "modern_plaster": "A professional product photography of a modern architectural room, textured grey plaster walls, soft natural diffused side-light, minimalist setup, with a large blank plaster wall in the center."
    }

    import json
    parsed_styles = None
    if body and body.mockup_styles:
        parsed_styles = body.mockup_styles

    styles_file = os.path.join(creation_dir, "mockup_styles.json")
    if not parsed_styles:
        parsed_styles = ["classic_living_room"]
        if os.path.exists(styles_file):
            try:
                with open(styles_file, "r", encoding="utf-8") as f_styles:
                    styles_data = json.load(f_styles)
                    parsed_styles = styles_data.get("styles", ["classic_living_room"])
            except Exception:
                pass

    # Save to db and file
    creation.mockup_styles = json.dumps(parsed_styles)
    try:
        with open(styles_file, "w", encoding="utf-8") as f_styles:
            json.dump({"styles": parsed_styles}, f_styles)
    except Exception as e:
        print(f"Failed to write mockup_styles.json: {e}")

    try:
        use_ai = False
        if body:
            if body.use_ai_mockup is not None:
                use_ai = body.use_ai_mockup
            elif body.instructions and body.instructions.strip():
                use_ai = True

        first_raw_path = None
        first_comm_path = None
        all_raw_paths = []
        all_comm_paths = []

        # Loop over parsed_styles to regenerate each
        for idx, style_name in enumerate(parsed_styles):
            style_prompt = MOCKUP_STYLE_PROMPTS.get(style_name, style_name)
            if idx == 0 and instructions and instructions.strip():
                style_prompt = f"{style_prompt} with these settings: {instructions}"
                
            bg_temp_file = None
            is_temp_bg = False
            if use_ai:
                try:
                    from ..services.image_engine import generate_mockup_backdrop
                    print(f"[creations] Generating AI room backdrop for style {style_name}: {style_prompt}")
                    backdrop_bytes = generate_mockup_backdrop(
                        style_prompt,
                        settings.openai_key
                    )
                    import tempfile
                    temp_bg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    temp_bg.write(backdrop_bytes)
                    temp_bg.close()
                    bg_temp_file = temp_bg.name
                    is_temp_bg = True
                except Exception as bg_err:
                    print(f"[creations] AI backdrop generation failed for style {style_name}: {bg_err}. Falling back to static/default.")

            if not bg_temp_file:
                # Try static background candidates
                bg_candidates = [
                    os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/{style_name}.jpg")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/{style_name}.jpeg")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/{style_name}.png")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../assets/backgrounds/classic_living_room.jpg")),
                ]
                bg_temp_file = next((p for p in bg_candidates if os.path.exists(p)), None)

            try:
                mockup_raw_path = os.path.join(creation_dir, f"Fichier_Import_mockup_raw_{idx+1}_{ts}.jpg")
                
                # Export: Raw Mockup (WITHOUT watermark)
                composite_stencil_on_bg(
                    ref_png,
                    bg_temp_file,
                    mockup_raw_path,
                    "matte_black_metal",
                    False
                )
                
                if idx == 0:
                    first_raw_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}"
                if os.path.exists(mockup_raw_path):
                    all_raw_paths.append(f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}")

                    # Generate commercial mockup if apply_tp is True
                    if apply_tp:
                        mockup_comm_filename = f"{safe_theme}_commercial_{idx+1}_{ts}.jpg"
                        mockup_comm_path = os.path.join(creation_dir, mockup_comm_filename)
                        try:
                            from ..services.mockup_engine import apply_commercial_template_overlay
                            apply_commercial_template_overlay(mockup_raw_path, mockup_comm_path)
                            if os.path.exists(mockup_comm_path):
                                comm_web_path = f"/static/creation_{creation_id}/{mockup_comm_filename}"
                                all_comm_paths.append(comm_web_path)
                                if idx == 0:
                                    first_comm_path = comm_web_path
                        except Exception as tp_err:
                            print(f"[creations] Failed to apply tp overlay to mockup: {tp_err}")
            finally:
                if is_temp_bg and bg_temp_file and os.path.exists(bg_temp_file):
                    try:
                        os.remove(bg_temp_file)
                    except Exception:
                        pass
        
        if first_raw_path:
            creation.mockup_path = first_raw_path
            existing_mockups = creation.mockup_paths or []
            for path in all_raw_paths:
                if path not in existing_mockups:
                    existing_mockups.append(path)
            creation.mockup_paths = existing_mockups
            
        if all_comm_paths:
            creation.real_mockup_path = first_comm_path
            existing_comm = creation.real_mockup_paths or []
            for path in all_comm_paths:
                if path not in existing_comm:
                    existing_comm.append(path)
            creation.real_mockup_paths = existing_comm
            
            # Also save to commercial_mockup_paths
            existing_comm_mockups = creation.commercial_mockup_paths or []
            for path in all_comm_paths:
                if path not in existing_comm_mockups:
                    existing_comm_mockups.append(path)
            creation.commercial_mockup_paths = existing_comm_mockups

            # Auto-select the generated commercial templates for Etsy publishing
            existing_selected = [p.strip() for p in (creation.selected_images_raw or "").split(",") if p.strip()]
            for p in all_comm_paths:
                if p not in existing_selected:
                    existing_selected.append(p)
            creation.selected_images_raw = ",".join(existing_selected)
            
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate mockup: {str(e)}")

@router.post("/{creation_id}/regenerate-zip", response_model=CreationResponse)
def regenerate_creation_zip(creation_id: int, db: Session = Depends(get_db)):
    """Rebuilds the client package ZIP containing all existing files."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    import re
    from ..services.image import package_assets
    
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    import time
    ts = int(time.time())

    svg_path = os.path.join(creation_dir, f"{safe_theme}.svg")
    if creation.svg_path:
        local_svg = os.path.join(STORAGE_DIR, creation.svg_path.replace("/static/", ""))
        if os.path.exists(local_svg):
            svg_path = local_svg

    dxf_path = os.path.join(creation_dir, f"{safe_theme}.dxf")
    if creation.dxf_path:
        local_dxf = os.path.join(STORAGE_DIR, creation.dxf_path.replace("/static/", ""))
        if os.path.exists(local_dxf):
            dxf_path = local_dxf

    ai_path = os.path.join(creation_dir, f"{safe_theme}.ai")
    if creation.ai_path:
        local_ai = os.path.join(STORAGE_DIR, creation.ai_path.replace("/static/", ""))
        if os.path.exists(local_ai):
            ai_path = local_ai

    eps_path = os.path.join(creation_dir, f"{safe_theme}.eps")
    if creation.eps_path:
        local_eps = os.path.join(STORAGE_DIR, creation.eps_path.replace("/static/", ""))
        if os.path.exists(local_eps):
            eps_path = local_eps

    pdf_path = os.path.join(creation_dir, f"{safe_theme}.pdf")
    if creation.pdf_path:
        local_pdf = os.path.join(STORAGE_DIR, creation.pdf_path.replace("/static/", ""))
        if os.path.exists(local_pdf):
            pdf_path = local_pdf

    upscale_png = os.path.join(creation_dir, f"{safe_theme}.png")
    if creation.upscale_png_path:
        local_upscale = os.path.join(STORAGE_DIR, creation.upscale_png_path.replace("/static/", ""))
        if os.path.exists(local_upscale):
            upscale_png = local_upscale

    zip_path = os.path.join(creation_dir, f"{safe_theme}_{ts}.zip")
    
    assets = []
    # Master paths
    for p in [svg_path, dxf_path, ai_path, eps_path, pdf_path, upscale_png]:
        if p and os.path.exists(p) and p not in assets:
            assets.append(p)
            
    # List paths (split elements & mockups)
    for path_list_name in ["svg_paths", "dxf_paths", "ai_paths", "eps_paths", "pdf_paths", "png_paths", "mockup_paths", "real_mockup_paths"]:
        urls = getattr(creation, path_list_name, []) or []
        for url in urls:
            if url:
                local_p = url.replace("/static/", STORAGE_DIR + "/")
                if os.path.exists(local_p) and local_p not in assets:
                    assets.append(local_p)

    if not assets:
        raise HTTPException(status_code=400, detail="No files exist to package.")
        
    try:
        package_assets(assets, zip_path)
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}"
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to package ZIP: {str(e)}")


@router.post("/{creation_id}/clean-metadata", response_model=CreationResponse)
def clean_creation_metadata(creation_id: int, db: Session = Depends(get_db)):
    """Automatically cleans and conforms titles, tags, and description for Etsy."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    from ..services.etsy_api import auto_clean_metadata_for_etsy
    try:
        auto_clean_metadata_for_etsy(creation)
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clean metadata: {str(e)}")


@router.post("/translate-seo", response_model=TranslateSEOResponse)
def translate_and_optimize_seo(
    req: TranslateSEORequest,
    db: Session = Depends(get_db)
):
    """
    Translates and optimizes bilingual Etsy metadata (FR + EN) using Mistral AI.
    Expects the model to return: { fr: { title, description, tags }, en: { title, description, tags } }
    Returns both language blocks so the frontend can update both simultaneously.
    """
    settings = get_or_create_settings(db)
    keys = {
        "openai_key":   settings.openai_key,
        "gemini_key":   settings.gemini_key,
        "mistral_key":  settings.mistral_key,
        "replicate_key": settings.replicate_key,
        "openrouter_key": settings.openrouter_key,
        "huggingface_key": settings.huggingface_key,
        "anthropic_key": settings.anthropic_key,
    }
    provider = settings.text_ai_provider or "gemini-2.0-flash-lite"
    
    from ..services.text_engine import translate_and_optimize_prompt
    
    try:
        res_content = translate_and_optimize_prompt(
            user_text=req.text,
            target_fields=req.target_fields,
            instructions=req.instructions,
            provider=provider,
            keys=keys
        )
        
        import json
        res_data = json.loads(res_content)
        
        # Extract bilingual blocks
        fr_block = res_data.get("fr", {})
        en_block = res_data.get("en", {})
        
        # Helper for tag cleaning
        import unicodedata
        def _clean_tag(t):
            val = unicodedata.normalize("NFKD", str(t))
            val = val.encode("ascii", "ignore").decode("ascii")
            val = re.sub(r"[^a-zA-Z0-9 ]+", " ", val).lower()
            val = re.sub(r"\s+", " ", val).strip()
            return val[:20]
        
        def _process_tags(raw_tags, fallback_pool):
            clean_tags = []
            seen = set()
            for t in (raw_tags or []):
                ct = _clean_tag(t)
                if ct and ct not in seen:
                    clean_tags.append(ct)
                    seen.add(ct)
            for ft in fallback_pool:
                if len(clean_tags) >= 13:
                    break
                cft = _clean_tag(ft)
                if cft and cft not in seen:
                    clean_tags.append(cft)
                    seen.add(cft)
            return clean_tags[:13]
        
        fallback_en = ["svg file", "laser cut file", "dxf file", "laser stencil", "eps file", "ai file", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser", "wood laser", "laser engrave"]
        fallback_fr = ["fichier svg", "decoupe laser", "fichier dxf", "stencil laser", "fichier eps", "fichier ai", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser", "bois laser", "gravure laser"]
        
        title_en = (en_block.get("title") or res_data.get("title") or "")[:140]
        desc_en = en_block.get("description") or res_data.get("description") or ""
        tags_en = _process_tags(en_block.get("tags") or res_data.get("tags", []), fallback_en)
        
        title_fr = (fr_block.get("title") or "")[:140]
        desc_fr = fr_block.get("description") or ""
        tags_fr = _process_tags(fr_block.get("tags", []), fallback_fr)
        
        # Build the bilingual data object for frontend consumption
        bilingual_data = {
            "fr": {
                "title": title_fr,
                "description": desc_fr,
                "tags": tags_fr
            },
            "en": {
                "title": title_en,
                "description": desc_en,
                "tags": tags_en
            }
        }
        
        return TranslateSEOResponse(
            status="success",
            data=bilingual_data,
            title_fr=title_fr,
            description_fr=desc_fr,
            tags_fr=tags_fr,
            title_en=title_en,
            description_en=desc_en,
            tags_en=tags_en
        )
    except Exception as e:
        print(f"[translate-seo] Mistral bilingual translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/{creation_id}/select-variant", response_model=CreationResponse)
def select_creation_variant(
    creation_id: int,
    req: SelectVariantRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    creation.source_png_path = req.variant_path
    creation.status = "processing"
    creation.current_step = "Régénération suite au choix de la variante..."
    db.commit()
    db.refresh(creation)

    from ..routers.pipeline import reprocess_creation_assets
    background_tasks.add_task(reprocess_creation_assets, creation.id)

    return creation


class ApplyTemplateBody(BaseModel):
    target_image_path: str


@router.post("/{creation_id}/apply-template", response_model=CreationResponse)
def apply_template_to_image(creation_id: int, body: ApplyTemplateBody, db: Session = Depends(get_db)):
    """Applies the tp.png overlay on a selected generated image."""
    import re
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")
        
    # Map static URL or relative path to filesystem path
    target_path = body.target_image_path
    if target_path.startswith("/static/"):
        target_file_path = os.path.join(STORAGE_DIR, target_path.replace("/static/", ""))
    else:
        target_file_path = os.path.join(STORAGE_DIR, f"creation_{creation_id}", os.path.basename(target_path))
        
    if not os.path.exists(target_file_path):
        raise HTTPException(status_code=400, detail=f"Target image file does not exist: {target_file_path}")
        
    # Generate timestamped filename for output
    import time
    ts = int(time.time())
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    output_filename = f"{safe_theme}_commercial_{ts}.jpg"
    output_file_path = os.path.join(creation_dir, output_filename)
    
    try:
        from ..services.mockup_engine import apply_commercial_template_overlay
        apply_commercial_template_overlay(target_file_path, output_file_path)
        
        # Add to commercial_mockup_paths
        new_commercial_path = f"/static/creation_{creation_id}/{output_filename}"
        
        existing_comm_mockups = creation.commercial_mockup_paths or []
        if new_commercial_path not in existing_comm_mockups:
            existing_comm_mockups.append(new_commercial_path)
        creation.commercial_mockup_paths = existing_comm_mockups
        
        # Add to selected_images_raw automatically so it is checked for Etsy
        existing_selected = [p.strip() for p in (creation.selected_images_raw or "").split(",") if p.strip()]
        if new_commercial_path not in existing_selected:
            existing_selected.append(new_commercial_path)
        creation.selected_images_raw = ",".join(existing_selected)
        
        db.commit()
        db.refresh(creation)
        return creation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply template overlay: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# ISLAND ANALYSIS & AUTO-BRIDGING ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{creation_id}/islands-analysis")
def get_islands_analysis(creation_id: int, db: Session = Depends(get_db)):
    """
    Analyzes floating disconnected islands in the creation's stencil
    and generates a visual inspection map with glowing red markers.
    """
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    source_img = (
        os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
        if creation.source_png_path and creation.source_png_path.startswith("/static/")
        else (creation.source_png_path or os.path.join(creation_dir, "Fichier_Import.png"))
    )

    if not os.path.exists(source_img):
        # Try finding any candidate png in creation_dir
        candidates = [os.path.join(creation_dir, f) for f in os.listdir(creation_dir) if f.endswith(".png") and not f.startswith("temp")] if os.path.exists(creation_dir) else []
        source_img = candidates[0] if candidates else None

    if not source_img or not os.path.exists(source_img):
        return {"island_count": 0, "islands": [], "overlay_url": None, "safe_to_cut": True}

    analysis = detect_floating_islands(source_img)
    overlay_filename = "islands_diagnostic_overlay.png"
    overlay_path = os.path.join(creation_dir, overlay_filename)

    generate_islands_overlay(source_img, overlay_path, analysis["islands"])

    return {
        "island_count": analysis["island_count"],
        "islands": analysis["islands"],
        "main_body_area": analysis["main_body_area"],
        "overlay_url": f"/static/creation_{creation_id}/{overlay_filename}?t={int(time.time())}",
        "safe_to_cut": analysis["island_count"] == 0,
    }


class AutoBridgeRequest(BaseModel):
    bridge_width: int = 5


@router.post("/{creation_id}/auto-bridge")
def trigger_auto_bridge(creation_id: int, body: Optional[AutoBridgeRequest] = None, db: Session = Depends(get_db)):
    """
    Applies 1-Click Auto-Bridging:
    Connects every floating island with geometric struts, re-vectorizes to SVG, DXF, AI, EPS, PDF,
    and updates the creation with 0 connectivity warnings!
    """
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    settings = get_or_create_settings(db)
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")

    source_img = (
        os.path.join(STORAGE_DIR, creation.source_png_path.replace("/static/", ""))
        if creation.source_png_path and creation.source_png_path.startswith("/static/")
        else (creation.source_png_path or os.path.join(creation_dir, "Fichier_Import.png"))
    )

    if not source_img or not os.path.exists(source_img):
        raise HTTPException(status_code=400, detail="Source stencil image not found.")

    bridge_w = body.bridge_width if body else 5
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_') or f"design_{creation_id}"

    # 1. Apply geometric auto-bridging
    bridged_png_path = os.path.join(creation_dir, f"{safe_theme}_bridged.png")
    bridge_res = auto_bridge_stencil(source_img, bridged_png_path, bridge_width=bridge_w)

    # Overwrite source image or use bridged image
    import shutil
    shutil.copyfile(bridged_png_path, source_img)

    # 2. Re-vectorize to SVG with node simplification
    svg_file = os.path.join(creation_dir, f"{safe_theme}.svg")
    png_to_svg(settings.potrace_path, settings.inkscape_path, source_img, svg_file)

    # 3. Re-export CAD formats (DXF, AI, EPS, PDF)
    dxf_file = os.path.join(creation_dir, f"{safe_theme}.dxf")
    ai_file = os.path.join(creation_dir, f"{safe_theme}.ai")
    eps_file = os.path.join(creation_dir, f"{safe_theme}.eps")
    pdf_file = os.path.join(creation_dir, f"{safe_theme}.pdf")

    svg_to_dxf(settings.inkscape_path, svg_file, dxf_file)
    svg_to_ai(settings.inkscape_path, svg_file, ai_file)
    svg_to_eps(settings.inkscape_path, svg_file, eps_file)
    png_to_pdf(source_img, pdf_file)

    # 4. Re-analyze connectivity
    connectivity = analyze_svg_connectivity(svg_file)
    islands_check = detect_floating_islands(source_img)

    creation.connectivity_warnings = islands_check["island_count"]
    creation.current_step = f"Auto-Bridge appliqué ({bridge_res['bridges_added']} ponts créés) ✓"
    db.commit()
    db.refresh(creation)

    return {
        "status": "success",
        "bridges_added": bridge_res["bridges_added"],
        "island_count": islands_check["island_count"],
        "safe_to_cut": islands_check["island_count"] == 0,
        "message": f"Auto-Bridging terminé : {bridge_res['bridges_added']} pont(s) solide(s) créé(s) !",
        "creation": creation,
    }





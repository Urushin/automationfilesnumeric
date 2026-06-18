import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db, SessionLocal
from ..models import Creation, Setting
from ..schemas import CreationResponse, CreationUpdate
from ..services.generator import generate_stencil_image, generate_seo_metadata
from ..services.gemini_seo import generate_etsy_seo
from ..services.vector import png_to_svg, svg_to_dxf
from ..services.image import convert_to_transparent_png, create_mockup, package_assets, png_to_pdf
from ..services.etsy_api import publish_listing_to_etsy
from ..services.compliance import run_compliance_check
from .settings import get_or_create_settings

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

@router.post("/{creation_id}/regenerate-seo", response_model=CreationResponse)
def regenerate_creation_seo(creation_id: int, db: Session = Depends(get_db)):
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    settings = get_or_create_settings(db)
    theme = creation.theme or "Design laser"
    seo = generate_etsy_seo(theme, settings.gemini_key, db)

    creation.title_fr = seo.get("title_fr")
    creation.title_en = seo.get("title_en")
    creation.description = seo.get("description") or seo.get("description_fr")
    creation.description_en = seo.get("description_en")
    creation.tags_fr = ",".join(seo.get("tags_fr", []))
    creation.tags_en = ",".join(seo.get("tags_en", []))
    creation.current_step = "SEO régénéré ✓"

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

@router.post("/global", response_model=CreationResponse)
def run_global_pipeline(theme: str = Form(...), db: Session = Depends(get_db)):
    """
    MODE A: PIPELINE GLOBAL (AUTOMATIC)
    1. Create database row.
    2. Generate PNG via OpenAI DALL-E 3.
    3. Run entire processing (SVG, DXF, PDF, Upscale, Mockup, ZIP).
    4. Generate LLM SEO texts.
    """
    settings = get_or_create_settings(db)
    
    # 1. Create DB entry to get ID
    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)
    
    # Setup directories
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)
    
    source_png = os.path.join(creation_dir, "source_raw.png")
    svg_path = os.path.join(creation_dir, "file.svg")
    dxf_path = os.path.join(creation_dir, "file.dxf")
    pdf_path = os.path.join(creation_dir, "file.pdf")
    upscale_png = os.path.join(creation_dir, "file_upscaled.png")
    mockup_path = os.path.join(creation_dir, "mockup.png")
    zip_path = os.path.join(creation_dir, "client_package.zip")
    
    try:
        # Step 1: Generate stencil image via DALL-E 3
        try:
            generate_stencil_image(settings.openai_key, theme, source_png)
            creation.source_png_path = f"/static/creation_{creation.id}/source_raw.png"
            db.commit()
        except Exception as e:
            # Cleanup DB on complete image generation failure
            db.delete(creation)
            db.commit()
            raise HTTPException(
                status_code=500, 
                detail=f"DALL-E 3 image generation failed: {e}. Check your OpenAI API Key."
            )
            
        # Step 2: Upscaling ×3 (always first — all subsequent steps use the upscaled version)
        try:
            convert_to_transparent_png(source_png, upscale_png, scale_factor=3)
            creation.upscale_png_path = f"/static/creation_{creation.id}/file_upscaled.png"
        except Exception as e:
            print(f"Pillow Client upscaling failed: {e}")

        # Step 3: Vectorisation (from upscaled PNG)
        try:
            png_to_svg(settings.potrace_path, upscale_png, svg_path)
            creation.svg_path = f"/static/creation_{creation.id}/file.svg"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Potrace Vectorization failed: {e}")
            
        # Step 4: CAD Conversion
        try:
            svg_to_dxf(settings.inkscape_path, svg_path, dxf_path, png_source_path=source_png)
            creation.dxf_path = f"/static/creation_{creation.id}/file.dxf"
        except Exception as e:
            print(f"Inkscape CAD conversion failed: {e}")
            
        # Step 5: PDF Print Format
        try:
            png_src = upscale_png if os.path.exists(upscale_png) else source_png
            png_to_pdf(png_src, pdf_path)
            creation.pdf_path = f"/static/creation_{creation.id}/file.pdf"
        except Exception as e:
            print(f"PDF generation failed: {e}")
            
        # Step 6: Mockup generation
        try:
            bg_path = settings.mockup_background_path
            create_mockup(upscale_png, bg_path, mockup_path)
            creation.mockup_path = f"/static/creation_{creation.id}/mockup.png"
        except Exception as e:
            print(f"Mockup generation failed: {e}")
            
        # Step 7: Package all into ZIP
        try:
            assets_to_zip = [svg_path, dxf_path, pdf_path, upscale_png]
            package_assets(assets_to_zip, zip_path)
            creation.zip_path = f"/static/creation_{creation.id}/client_package.zip"
        except Exception as e:
            print(f"ZIP packaging failed: {e}")
            
        # Step 8: Call SEO Copywriting
        try:
            seo = generate_seo_metadata(settings, theme)
            creation.title_fr = seo.get("title_fr")
            creation.title_en = seo.get("title_en")
            creation.description = seo.get("description") or seo.get("description_fr")
            creation.description_en = seo.get("description_en")
            creation.tags_fr = ",".join(seo.get("tags_fr", []))
            creation.tags_en = ",".join(seo.get("tags_en", []))
        except Exception as e:
            print(f"SEO Copywriting LLM call failed, fallback used: {e}")
            
        db.commit()
        db.refresh(creation)
        return creation
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected pipeline error: {str(e)}")

@router.post("/modular", response_model=CreationResponse)
def run_modular_pipeline(
    file: UploadFile = File(...),
    theme: Optional[str] = Form(None),
    vectorize: bool = Form(False),
    convert_cad: bool = Form(False),
    format_pdf: bool = Form(False),
    upscale: bool = Form(False),
    package: bool = Form(False),
    generate_seo: bool = Form(False),
    generate_mockup: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    MODE B: MODE MODULAIRE (À LA CARTE)
    1. Save uploaded file as source image.
    2. Execute only selected operations.
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
        is_published_etsy=False
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)
    
    # Setup directory
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)
    
    # Save uploaded file
    source_png = os.path.join(creation_dir, "source_raw.png")
    with open(source_png, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    creation.source_png_path = f"/static/creation_{creation.id}/source_raw.png"
    db.commit()
    
    svg_path = os.path.join(creation_dir, "file.svg")
    dxf_path = os.path.join(creation_dir, "file.dxf")
    pdf_path = os.path.join(creation_dir, "file.pdf")
    upscale_png = os.path.join(creation_dir, "file_upscaled.png")
    mockup_path = os.path.join(creation_dir, "mockup.png")
    zip_path = os.path.join(creation_dir, "client_package.zip")
    
    try:
        # Run vectorize
        if vectorize:
            png_to_svg(settings.potrace_path, source_png, svg_path)
            creation.svg_path = f"/static/creation_{creation.id}/file.svg"
            
        # Run CAD
        if convert_cad:
            # We need SVG for CAD. If SVG not vectorized yet, run it implicitly
            if not os.path.exists(svg_path):
                png_to_svg(settings.potrace_path, source_png, svg_path)
                creation.svg_path = f"/static/creation_{creation.id}/file.svg"
            svg_to_dxf(settings.inkscape_path, svg_path, dxf_path, png_source_path=source_png)
            creation.dxf_path = f"/static/creation_{creation.id}/file.dxf"
            
        # Run upscale
        if upscale or generate_mockup:  # Mockup relies on upscaled png
            convert_to_transparent_png(source_png, upscale_png, scale_factor=3)
            creation.upscale_png_path = f"/static/creation_{creation.id}/file_upscaled.png"
            
        # Run PDF
        if format_pdf:
            png_src = upscale_png if os.path.exists(upscale_png) else source_png
            png_to_pdf(png_src, pdf_path)
            creation.pdf_path = f"/static/creation_{creation.id}/file.pdf"
            
        # Run Mockup
        if generate_mockup:
            bg_path = settings.mockup_background_path
            create_mockup(upscale_png, bg_path, mockup_path)
            creation.mockup_path = f"/static/creation_{creation.id}/mockup.png"
            
        # Run Package (ZIP)
        if package:
            assets_to_zip = []
            if os.path.exists(svg_path): assets_to_zip.append(svg_path)
            if os.path.exists(dxf_path): assets_to_zip.append(dxf_path)
            if os.path.exists(pdf_path): assets_to_zip.append(pdf_path)
            if os.path.exists(upscale_png): assets_to_zip.append(upscale_png)
            
            package_assets(assets_to_zip, zip_path)
            creation.zip_path = f"/static/creation_{creation.id}/client_package.zip"
            
        # Run Copywriting
        if generate_seo and theme:
            seo = generate_seo_metadata(settings, theme)
            creation.title_fr = seo.get("title_fr")
            creation.title_en = seo.get("title_en")
            creation.description = seo.get("description") or seo.get("description_fr")
            creation.description_en = seo.get("description_en")
            creation.tags_fr = ",".join(seo.get("tags_fr", []))
            creation.tags_en = ",".join(seo.get("tags_en", []))
            
        db.commit()
        db.refresh(creation)
        return creation
        
    except Exception as e:
        # We don't delete on modular failure, since the user might want to check partial outputs
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Modular pipeline failed: {str(e)}"
        )

@router.post("/{creation_id}/publish")
def publish_creation_etsy(creation_id: int, db: Session = Depends(get_db)):
    """Triggers publication to Etsy shop listing after compliance and guardrail checks."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Creation not found.")

    settings = get_or_create_settings(db)

    # ── Guardrails format ─────────────────────────────────────────────────
    missing = []
    if not creation.title_fr: missing.append("Titre FR")
    if not creation.title_en: missing.append("Titre EN")
    if not creation.description: missing.append("Description FR")
    if not creation.description_en: missing.append("Description EN")
    if not creation.tags_fr: missing.append("Tags FR")
    if not creation.tags_en: missing.append("Tags EN")
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
def download_creation_file(creation_id: int, file_type: str, db: Session = Depends(get_db)):
    """Forces browser local download by returning files with attachment headers."""
    creation = db.query(Creation).filter(Creation.id == creation_id).first()
    if not creation:
        raise HTTPException(status_code=404, detail="Création introuvable.")
        
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    
    mapping = {
        "svg":    "file.svg",
        "dxf":    "file.dxf",
        "ai":     "file.ai",         # [NEW]
        "eps":    "file.eps",        # [NEW]
        "pdf":    "file.pdf",
        "png":    "file_upscaled.png",
        "zip":    "client_package.zip",
        "raw":    "source_raw.png",
        "mockup": "mockup.jpg",
    }
    
    if file_type not in mapping:
        raise HTTPException(status_code=400, detail="Type de fichier invalide.")
        
    file_name = mapping[file_type]
    file_path = os.path.join(creation_dir, file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Fichier {file_name} introuvable.")
        
    # Generate clean name for the download
    safe_theme = "".join([c if c.isalnum() else "_" for c in creation.theme])
    download_name = f"{safe_theme}_{file_name}"
    
    return FileResponse(
        path=file_path,
        filename=download_name,
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

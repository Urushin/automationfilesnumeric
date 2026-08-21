"""
SSE Streaming Pipeline Router — v3.0
Runs the full Etsy Laser Automation pipeline step by step and streams
real-time progress events to the frontend via Server-Sent Events.
"""
import asyncio
import json
import os
import shutil
import tempfile
import urllib.parse
from datetime import datetime
from typing import AsyncGenerator, Optional, List
import requests

from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db, SessionLocal
from ..models import Creation, CreationAsset, Setting
from ..schemas import CreationResponse
from ..routers.settings import get_or_create_settings
from ..services.image_engine import (
    generate_stencil_image,
    regenerate_stencil_image_guided,
    execute_inpainting,
    split_multielement_image,
    local_binarize_image,
    local_binarize_opaque,
    stream_dalle_image_progressive,
    generate_mockup_backdrop,
)
from ..services.seo_engine import generate_etsy_seo
from ..services.generator import generate_seo_metadata
from ..services.vector import png_to_svg, svg_to_dxf, svg_to_pdf
from ..services.image import convert_to_transparent_png, package_assets, png_to_pdf
from ..services.mockup_processor import create_ecommerce_mockup
from ..services.export_formats import svg_to_ai, svg_to_eps, svg_to_high_quality_png
from ..services.svg_analyzer import analyze_svg_connectivity
from ..services.mockup_engine import (
    composite_stencil_on_bg,
    create_real_mockup,
    generate_etsy_standard_mockup_pack,
    create_real_layer_compositing,
    generate_formats_infographic,
    generate_specs_dimensions_infographic,
    generate_zoom_texture_mockup,
    apply_watermark_to_image,
)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline SSE"])

STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../storage")
)
os.makedirs(STORAGE_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# CENTRALIZED MOCKUP STYLE PROMPTS (single source of truth)
# ─────────────────────────────────────────────────────────────────────────────
MOCKUP_STYLE_PROMPTS = {
    "classic_living_room": "A professional product photography of a modern luxury living room, elegant sofa, warm ambient light, with a large blank concrete wall in the center.",
    "modern_bedroom": "A professional product photography of a minimalist Scandinavian bedroom, cozy linen bedding, warm wooden side table, with a large blank plaster wall in the center.",
    "industrial_loft": "A professional product photography of a spacious industrial loft, brick wall, steel accents, large windows, with a large blank dark brick wall in the center.",
    "scandinavian_office": "A professional product photography of a Scandinavian design home office, minimalist light wood desk, plants, with a large blank white wall in the center.",
    "boho_chic": "A professional product photography of a cozy bohemian living room, rattan furniture, warm textiles, pampas grass, with a large blank beige wall in the center.",
    "industrial": "A professional product photography of a modern industrial room, concrete walls, dark metal accents, warm spotlighting, with a large flat empty concrete wall in the center.",
    "luxury_wood": "A professional product photography of a luxury room interior, premium warm rustic oak wooden panels on the wall, elegant high-end styling, with a large flat empty wooden wall in the center.",
    "modern_plaster": "A professional product photography of a minimalist modern room, high-end matte plaster textured wall, soft natural side lighting, with a large flat empty plaster wall in the center."
}


# ─────────────────────────────────────────────────────────────────────────────
# SSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _status(step: int, text: str, status: str = "active") -> str:
    return _sse("status", {"step": step, "text": text, "status": status})


def _sync_creation_assets(db: Session, creation_id: int, asset_type: str, paths: list):
    try:
        db.query(CreationAsset).filter(
            CreationAsset.creation_id == creation_id,
            CreationAsset.asset_type == asset_type
        ).delete()
        for idx, p in enumerate(paths):
            if not p:
                continue
            asset = CreationAsset(
                creation_id=creation_id,
                asset_type=asset_type,
                file_path=p,
                filename=os.path.basename(p),
                sort_order=idx
            )
            db.add(asset)
    except Exception as e:
        print(f"[assets_sync] Warning: failed to sync {asset_type} assets: {e}")


def _update_creation(creation_id: int, **fields):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if creation:
            for k, v in fields.items():
                if k == "png_paths" and isinstance(v, list):
                    creation.png_paths = v
                    _sync_creation_assets(db, creation_id, "png", v)
                elif k == "svg_paths" and isinstance(v, list):
                    creation.svg_paths = v
                    _sync_creation_assets(db, creation_id, "svg", v)
                elif k == "pdf_paths" and isinstance(v, list):
                    creation.pdf_paths = v
                    _sync_creation_assets(db, creation_id, "pdf", v)
                elif k == "mockup_paths" and isinstance(v, list):
                    creation.mockup_paths = v
                    _sync_creation_assets(db, creation_id, "mockup", v)
                elif k == "real_mockup_paths" and isinstance(v, list):
                    creation.real_mockup_paths = v
                    _sync_creation_assets(db, creation_id, "real_mockup", v)
                elif k == "dxf_paths" and isinstance(v, list):
                    creation.dxf_paths = v
                    _sync_creation_assets(db, creation_id, "dxf", v)
                elif k == "ai_paths" and isinstance(v, list):
                    creation.ai_paths = v
                    _sync_creation_assets(db, creation_id, "ai", v)
                elif k == "eps_paths" and isinstance(v, list):
                    creation.eps_paths = v
                    _sync_creation_assets(db, creation_id, "eps", v)
                elif k == "source_png_variants" and isinstance(v, list):
                    creation.source_png_variants = v
                    _sync_creation_assets(db, creation_id, "variant", v)
                elif k == "zip_path" and isinstance(v, str) and v:
                    creation.zip_path = v
                    _sync_creation_assets(db, creation_id, "zip", [v])
                elif k == "source_png_path" and isinstance(v, str) and v:
                    creation.source_png_path = v
                    _sync_creation_assets(db, creation_id, "source_png", [v])
                else:
                    setattr(creation, k, v)
            db.commit()
    finally:
        db.close()



# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL PIPELINE STREAM
# ─────────────────────────────────────────────────────────────────────────────
async def _global_pipeline_generator(
    theme: str,
    session_token: str = "",
    creation_id: Optional[int] = None,
    design_style: str = "classic",
    bundle_size: int = 4,
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    db = SessionLocal()
    existing_source_png_path = None
    try:
        settings = get_or_create_settings(db)
        if creation_id:
            creation = db.query(Creation).filter(Creation.id == creation_id).first()
            theme = creation.theme or theme
            existing_source_png_path = creation.source_png_path
            cid = creation_id
            bundle_size = creation.bundle_size or bundle_size
        else:
            creation = Creation(
                theme=theme,
                timestamp=datetime.utcnow(),
                is_published_etsy=False,
                status="processing",
                current_step="Initialisation...",
                session_token=session_token or None,
                quantity=settings.default_quantity,
                bundle_size=bundle_size,
            )
            db.add(creation)
            db.commit()
            db.refresh(creation)
            cid = creation.id
            existing_source_png_path = creation.source_png_path
        settings_snap = {
            "openai_key":   getattr(settings, "openai_key", None),
            "banana_key":   getattr(settings, "banana_key", None),
            "gemini_key":   getattr(settings, "gemini_key", None),
            "mistral_key":  getattr(settings, "mistral_key", None),
            "replicate_key": getattr(settings, "replicate_key", None),
            "openrouter_key": getattr(settings, "openrouter_key", None),
            "huggingface_key": getattr(settings, "huggingface_key", None),
            "anthropic_key": getattr(settings, "anthropic_key", None),
            "stability_key": getattr(settings, "stability_key", None),
            "image_ai_provider": preferred_image_provider or getattr(settings, "image_ai_provider", "banana") or "banana",
            "stencil_image_provider": preferred_image_provider or getattr(settings, "stencil_image_provider", None) or getattr(settings, "image_ai_provider", "banana") or "banana",
            "mockup_image_provider": getattr(settings, "mockup_image_provider", None) or getattr(settings, "image_ai_provider", "banana") or "banana",
            "stencil_image_quality": getattr(settings, "stencil_image_quality", "auto") or "auto",
            "mockup_image_quality": getattr(settings, "mockup_image_quality", "auto") or "auto",
            "text_ai_provider":  preferred_text_provider or getattr(settings, "text_ai_provider", "gemini-2.0-flash-lite") or "gemini-2.0-flash-lite",
            "potrace_path": getattr(settings, "potrace_path", "potrace"),
            "inkscape_path":getattr(settings, "inkscape_path", "inkscape"),
        }
    finally:
        db.close()

    yield _sse("created", {"creation_id": cid, "session_token": session_token})

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{cid}")
    os.makedirs(creation_dir, exist_ok=True)

    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme).strip('_')
    if not safe_theme:
        safe_theme = f"design_{cid}"

    source_png    = os.path.join(creation_dir, f"{safe_theme}_source.png")
    binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
    svg_path      = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path      = os.path.join(creation_dir, f"{safe_theme}.dxf")
    ai_path       = os.path.join(creation_dir, f"{safe_theme}.ai")
    eps_path      = os.path.join(creation_dir, f"{safe_theme}.eps")
    pdf_path      = os.path.join(creation_dir, f"{safe_theme}.pdf")
    upscale_png   = os.path.join(creation_dir, f"{safe_theme}.png")
    mockup_path   = os.path.join(creation_dir, f"{safe_theme}_mockup.jpg")
    zip_path      = os.path.join(creation_dir, f"{safe_theme}.zip")

    init_image_path = None
    if creation_id and existing_source_png_path:
        existing_source = os.path.join(STORAGE_DIR, f"creation_{cid}", os.path.basename(existing_source_png_path))
        if os.path.exists(existing_source):
            init_image_path = existing_source + ".init.png"
            shutil.copy(existing_source, init_image_path)

    comp_status = {
        "stencil": {"status": "success", "paths": [], "error": None},
        "seo": {"status": "success", "data": None, "error": None},
        "mockup": {"status": "success", "paths": [], "error": None}
    }

    try:
        # ── STEP 1: Image AI Generation ────────────────────────────────────
        stencil_provider = settings_snap.get('stencil_image_provider') or settings_snap.get('image_ai_provider', 'banana')
        yield _status(1, f"Génération du motif IA ({stencil_provider})...")
        _update_creation(cid, current_step="Génération d'Image...")
        try:
            result = await asyncio.to_thread(
                generate_stencil_image,
                provider=stencil_provider,
                banana_key=settings_snap.get("banana_key"),
                openai_key=settings_snap.get("openai_key"),
                theme=theme,
                output_path=source_png,
                init_image_path=init_image_path,
                bundle_size=bundle_size,
                design_style=design_style,
                gemini_key=settings_snap.get("gemini_key"),
                replicate_key=settings_snap.get("replicate_key"),
                openrouter_key=settings_snap.get("openrouter_key"),
                huggingface_key=settings_snap.get("huggingface_key"),
                stability_key=settings_snap.get("stability_key"),
                n_images=1,
                quality=settings_snap.get("stencil_image_quality", "auto"),
                mockup_provider=settings_snap.get("mockup_image_provider"),
                mockup_quality=settings_snap.get("mockup_image_quality", "auto")
            )
            comp_status["stencil"]["paths"] = [f"/static/creation_{cid}/{os.path.basename(source_png)}"]
            stencil_prompt = result.get("prompt", "") if isinstance(result, dict) else ""
            _update_creation(
                cid,
                source_png_path=f"/static/creation_{cid}/{os.path.basename(source_png)}",
                current_step="Image générée ✓",
                pipeline_status=json.dumps(comp_status)
            )
            yield _sse("image_ready", {
                "source_png_path": f"/static/creation_{cid}/{os.path.basename(source_png)}",
                "provider": settings_snap.get("image_ai_provider"),
                "prompt": stencil_prompt
            })
        except Exception as se:
            print(f"[pipeline] Stencil generation failed: {se}")
            comp_status["stencil"]["status"] = "failed"
            comp_status["stencil"]["error"] = str(se)
            
            error_type = "GENERATION_FAILED"
            error_msg = str(se)
            if "BILLING_LIMIT_REACHED" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "credits are depleted" in error_msg or "Billing hard limit" in error_msg:
                error_type = "PROVIDER_CREDITS_EXHAUSTED"
                error_msg = "Vos clés API OpenAI/Gemini n'ont plus de crédits ou HuggingFace est inaccessible. Veuillez vérifier votre connexion et vos abonnements."
                
            _update_creation(cid, status="failed", failed_reason=error_msg, current_step="Échec")
            yield _sse("error", {
                "status": "error",
                "error_type": error_type,
                "msg": error_msg,
                "message": error_msg
            })
            return



        # ── STEP 2: Binarisation ─────────
        yield _status(2, "Binarisation (suppression anti-aliasing, seuillage Otsu)...")
        _update_creation(cid, current_step="Binarisation...")
        if os.path.exists(source_png):
            await asyncio.to_thread(local_binarize_image, source_png, binarized_png)
            _update_creation(cid, current_step="Binarisé ✓")
        else:
            print("[pipeline] source_png not found, skipping binarization.")

        # ── ELEMENT SPLITTING ──
        element_paths = []
        if bundle_size > 1 and os.path.exists(binarized_png):
            yield _status(3, "Détection et séparation des éléments du pack...")
            element_paths = await asyncio.to_thread(
                split_multielement_image, binarized_png, creation_dir, bundle_size
            )
        
        if not element_paths:
            if os.path.exists(binarized_png):
                element_paths = [binarized_png]
            elif os.path.exists(source_png):
                element_paths = [source_png]
            else:
                element_paths = []

        elements = []
        for idx, el_png in enumerate(element_paths):
            el_name = safe_theme if len(element_paths) == 1 else f"{safe_theme}_{idx+1}"
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

        # ── STEP 3: Upscale ───────────────────────────
        yield _status(3, f"Upscaling HQ ×3 ({len(elements)} éléments)...")
        _update_creation(cid, current_step="Upscaling...")
        png_urls = []
        for el in elements:
            if os.path.exists(el["source_png"]):
                await asyncio.to_thread(convert_to_transparent_png, el["source_png"], el["upscale_png"], 3)
                if os.path.exists(el["upscale_png"]):
                    png_urls.append(f"/static/creation_{cid}/{os.path.basename(el['upscale_png'])}")

        if png_urls:
            _update_creation(
                cid,
                upscale_png_path=png_urls[0],
                png_paths=png_urls,
                current_step="Upscaled ✓",
            )
            yield _sse("assets_ready", {
                "upscale_png_path": png_urls[0],
                "png_paths": png_urls,
            })

        # ── STEP 4: Vectorisation SVG ───────────────────
        yield _status(4, f"Vectorisation Potrace ({len(elements)} éléments)...")
        _update_creation(cid, current_step="Vectorisation SVG...")
        svg_urls = []
        for el in elements:
            if os.path.exists(el["source_png"]):
                await asyncio.to_thread(png_to_svg, settings_snap["potrace_path"], el["source_png"], el["svg_path"], settings_snap["inkscape_path"])
                if os.path.exists(el["svg_path"]):
                    svg_urls.append(f"/static/creation_{cid}/{os.path.basename(el['svg_path'])}")

        master_svg_url = svg_urls[0] if svg_urls else None
        connectivity = {"island_count": 1, "severity": "info", "message": "N/A", "safe_to_cut": True}
        if elements and os.path.exists(elements[0]["svg_path"]):
            connectivity = await asyncio.to_thread(analyze_svg_connectivity, elements[0]["svg_path"])

        _update_creation(
            cid,
            svg_path=master_svg_url,
            svg_paths=svg_urls,
            connectivity_warnings=max(0, connectivity.get("island_count", 1) - 1),
            current_step="SVG généré ✓",
        )
        yield _sse("vector_ready", {
            "svg_path": master_svg_url,
            "svg_paths": svg_urls,
            "connectivity": connectivity,
        })

        if connectivity.get("severity") in ("warning", "critical"):
            yield _sse("connectivity_warning", {
                "island_count": connectivity.get("island_count", 0),
                "severity": connectivity["severity"],
                "message": connectivity["message"],
                "safe_to_cut": connectivity["safe_to_cut"],
            })

        # ── STEP 5: Exports CAO ────────────────────────────────
        yield _status(5, f"Génération DXF, AI, EPS ({len(elements)} éléments)...")
        _update_creation(cid, current_step="Exports CAO...")
        inkscape_bin = settings_snap["inkscape_path"]
        dxf_urls, ai_urls, eps_urls = [], [], []
        for el in elements:
            if os.path.exists(el["svg_path"]):
                await asyncio.to_thread(svg_to_dxf, inkscape_bin, el["svg_path"], el["dxf_path"], el["source_png"])
                await asyncio.to_thread(svg_to_ai, inkscape_bin, el["svg_path"], el["ai_path"])
                await asyncio.to_thread(svg_to_eps, inkscape_bin, el["svg_path"], el["eps_path"])
                if os.path.exists(el["dxf_path"]):
                    dxf_urls.append(f"/static/creation_{cid}/{os.path.basename(el['dxf_path'])}")
                if os.path.exists(el["ai_path"]):
                    ai_urls.append(f"/static/creation_{cid}/{os.path.basename(el['ai_path'])}")
                if os.path.exists(el["eps_path"]):
                    eps_urls.append(f"/static/creation_{cid}/{os.path.basename(el['eps_path'])}")

        _update_creation(
            cid,
            dxf_path=dxf_urls[0] if dxf_urls else None,
            dxf_paths=dxf_urls,
            ai_path=ai_urls[0] if ai_urls else None,
            ai_paths=ai_urls,
            eps_path=eps_urls[0] if eps_urls else None,
            eps_paths=eps_urls,
        )
        yield _sse("assets_ready", {
            "dxf_path": dxf_urls[0] if dxf_urls else None,
            "dxf_paths": dxf_urls,
            "ai_path":  ai_urls[0] if ai_urls else None,
            "ai_paths": ai_urls,
            "eps_path": eps_urls[0] if eps_urls else None,
            "eps_paths": eps_urls,
        })

        # ── STEP 6: PDF ──────────────────────────────
        yield _status(6, f"Génération PDF ({len(elements)} éléments)...")
        _update_creation(cid, current_step="Génération PDF...")
        pdf_urls = []
        for el in elements:
            png_src = el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"]
            if os.path.exists(el["svg_path"]):
                await asyncio.to_thread(svg_to_pdf, settings_snap["inkscape_path"], el["svg_path"], el["pdf_path"], png_src)
                if os.path.exists(el["pdf_path"]):
                    pdf_urls.append(f"/static/creation_{cid}/{os.path.basename(el['pdf_path'])}")

        _update_creation(cid, pdf_path=pdf_urls[0] if pdf_urls else None, pdf_paths=pdf_urls)
        yield _sse("assets_ready", {"pdf_path": pdf_urls[0] if pdf_urls else None, "pdf_paths": pdf_urls})

        # ── STEP 7: Pack 4 Visuels Etsy (Placage Réel & Zéro Hallucination) ───
        yield _status(7, "Création du pack de 4 visuels Etsy (Mockup, Zoom, Formats, Guide)...")
        _update_creation(cid, current_step="Création du pack Etsy (4 visuels)...")
        try:
            png_for_mockup = upscale_png if os.path.exists(upscale_png) else binarized_png

            db = SessionLocal()
            try:
                creation = db.query(Creation).filter(Creation.id == cid).first()
                mockup_styles_raw = creation.mockup_styles if creation else None
                settings_obj = db.query(Setting).first()
                watermark_text = getattr(settings_obj, "watermark_text", "digitalfilesbymop") or "digitalfilesbymop"
                apply_wm = getattr(creation, "apply_watermark", False) or getattr(settings_obj, "default_apply_watermark", False)
            finally:
                db.close()

            parsed_styles = []
            if mockup_styles_raw:
                try:
                    parsed_styles = json.loads(mockup_styles_raw)
                except Exception:
                    parsed_styles = [x.strip() for x in mockup_styles_raw.split(",") if x.strip()]
            selected_style = parsed_styles[0] if parsed_styles else "classic_living_room"

            pack_result = await asyncio.to_thread(
                generate_etsy_standard_mockup_pack,
                stencil_path=png_for_mockup,
                output_dir=creation_dir,
                theme=theme,
                bundle_size=bundle_size,
                bg_style=selected_style,
                apply_watermark=apply_wm,
                watermark_text=watermark_text
            )

            mockup_raw_paths = [f"/static/creation_{cid}/{os.path.basename(p)}" for p in pack_result["all_paths"]]
            first_raw_path = mockup_raw_paths[0] if mockup_raw_paths else None

            _update_creation(
                cid,
                mockup_path=first_raw_path,
                mockup_paths=mockup_raw_paths,
                real_mockup_path=None,
                real_mockup_paths=[],
                current_step="Pack Etsy (4 visuels) généré ✓",
                pipeline_status=json.dumps(comp_status)
            )
            if first_raw_path:
                yield _sse("mockup_ready", {
                    "mockup_path": first_raw_path,
                    "mockup_paths": mockup_raw_paths,
                    "real_mockup_path": None,
                    "real_mockup_paths": [],
                    "commercial_mockup_paths": []
                })
        except Exception as me:
            print(f"[pipeline] Mockup generation failed: {me}")
            comp_status["mockup"]["status"] = "failed"
            comp_status["mockup"]["error"] = str(me)
            _update_creation(cid, current_step="Mockup failed, proceeding...", pipeline_status=json.dumps(comp_status))


        # ── STEP 8: ZIP ──────────────────────────────────
        yield _status(8, "Création de l'archive ZIP...")
        _update_creation(cid, current_step="Création ZIP...")
        assets_to_zip = []
        for el in elements:
            for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                p = el[path_key]
                if p and os.path.exists(p):
                    assets_to_zip.append(p)
        for raw_p in mockup_raw_paths:
            full_raw_p = os.path.join(creation_dir, os.path.basename(raw_p))
            if os.path.exists(full_raw_p):
                assets_to_zip.append(full_raw_p)

        if assets_to_zip:
            await asyncio.to_thread(package_assets, assets_to_zip, zip_path)
            _update_creation(cid, zip_path=f"/static/creation_{cid}/{os.path.basename(zip_path)}", current_step="ZIP créé ✓")
            yield _sse("assets_ready", {"zip_path": f"/static/creation_{cid}/{os.path.basename(zip_path)}"})

        # ── STEP 9: SEO ──────────────────────────────────
        yield _status(9, f"Rédaction SEO bilingue ({settings_snap.get('text_ai_provider', 'gemini')})...")
        _update_creation(cid, current_step="Rédaction SEO...")
        seo_image_path = upscale_png if os.path.exists(upscale_png) else (binarized_png if os.path.exists(binarized_png) else source_png)
        try:
            seo = await asyncio.to_thread(
                generate_etsy_seo,
                theme=theme,
                provider=settings_snap["text_ai_provider"],
                gemini_key=settings_snap["gemini_key"],
                mistral_key=settings_snap["mistral_key"],
                openai_key=settings_snap["openai_key"],
                replicate_key=settings_snap.get("replicate_key"),
                openrouter_key=settings_snap.get("openrouter_key"),
                huggingface_key=settings_snap.get("huggingface_key"),
                anthropic_key=settings_snap.get("anthropic_key"),
                db=None,
                image_path=seo_image_path,
                bundle_size=bundle_size
            )

            comp_status["seo"]["status"] = seo.get("status", "success")
            comp_status["seo"]["error"] = seo.get("error")
            comp_status["seo"]["data"] = {
                "title_fr": seo.get("title_fr"),
                "title_en": seo.get("title_en"),
                "tags_fr": seo.get("tags_fr"),
                "tags_en": seo.get("tags_en")
            }

            def _tag_list(t):
                if not t: return []
                return [x.strip() for x in t.split(",") if x.strip()] if isinstance(t, str) else t

            def _tag_csv(t):
                if not t: return ""
                return ",".join(t) if isinstance(t, list) else t

            def _description_fr(s):
                return s.get("description_fr") or s.get("description") or ""

            tags_fr = _tag_list(seo.get("tags_fr"))
            tags_en = _tag_list(seo.get("tags_en"))

            _update_creation(
                cid,
                title_fr=seo.get("title_fr"),
                title_en=seo.get("title_en"),
                description=_description_fr(seo),
                description_en=seo.get("description_en"),
                tags_fr=_tag_csv(tags_fr),
                tags_en=_tag_csv(tags_en),
                current_step="SEO rédigé ✓",
                pipeline_status=json.dumps(comp_status)
            )
            yield _sse("seo_ready", {
                "title_fr":       seo.get("title_fr"),
                "title_en":       seo.get("title_en"),
                "description":    _description_fr(seo),
                "description_fr": _description_fr(seo),
                "description_en": seo.get("description_en"),
                "tags_fr":        tags_fr,
                "tags_en":        tags_en,
            })
        except Exception as seoe:
            print(f"[pipeline] SEO failed: {seoe}")
            comp_status["seo"]["status"] = "failed"
            comp_status["seo"]["error"] = str(seoe)
            _update_creation(cid, current_step="SEO failed, proceeding...", pipeline_status=json.dumps(comp_status))

        # ── STEP 10: Compliance ──────────────────────────────────────
        yield _status(10, "Vérification de conformité Etsy...")
        _update_creation(cid, current_step="Vérification de conformité...")
        compliance_warnings_val = None
        try:
            compliance = await asyncio.to_thread(
                run_compliance_check,
                title=seo.get("title_fr", "") if seo else "",
                description=_description_fr(seo) if seo else "",
                tags=tags_fr if seo else []
            )
            compliance_warnings_val = compliance.to_json()
            yield _sse("compliance_result", compliance.to_dict())
        except Exception as ce:
            print(f"[pipeline] Compliance check failed: {ce}")

        _update_creation(
            cid,
            compliance_warnings=compliance_warnings_val,
            status="completed",
            current_step="Terminé ✓",
            pipeline_status=json.dumps(comp_status)
        )

        # ── DONE ──────────────────────────────────────────────────────────
        yield _status(11, "Pipeline terminé avec succès ! 🎉", status="complete")
        yield _sse("done", {"creation_id": cid, "pipeline_status": comp_status})

    except Exception as e:
        import traceback
        traceback.print_exc()
        _update_creation(cid, status="failed", failed_reason=str(e), current_step="Erreur")
        yield _sse("error", {"msg": str(e), "creation_id": cid})


@router.get("/stream/global")
async def stream_global_pipeline(
    theme: str,
    session_token: str = "",
    creation_id: Optional[int] = None,
    design_style: str = "classic",
    bundle_size: int = 4,
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return StreamingResponse(
        _global_pipeline_generator(
            theme=theme,
            session_token=session_token,
            creation_id=creation_id,
            design_style=design_style,
            bundle_size=bundle_size,
            preferred_image_provider=preferred_image_provider,
            preferred_text_provider=preferred_text_provider,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS FOR MODULAR PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
class SaveWorkspaceRequest(BaseModel):
    creation_id: int
    theme: Optional[str] = None
    canvas_data: Optional[str] = None
    canvasData: Optional[str] = None
    asset_path: Optional[str] = None
    asset_type: Optional[str] = "master_stencil"


class MockupItemConfig(BaseModel):
    index: int
    style: str


class PipelineExecutionRequest(BaseModel):
    creation_id: str
    generate_real_mockup: bool = False
    mockup_configs: list[MockupItemConfig] = []



# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND REPROCESSING FOR WORKSPACE & SELECTION
# ─────────────────────────────────────────────────────────────────────────────
def reprocess_creation_assets(creation_id: int):
    """
    Regenerates all downstream assets (vector, CAD, PDF, mockup, ZIP, SEO)
    for a creation when its source_png_path has changed (e.g. workspace save, guided retouch, or variant selection).
    """
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return

        settings = get_or_create_settings(db)
        settings_snap = {
            "openai_key":   getattr(settings, "openai_key", None),
            "gemini_key":   getattr(settings, "gemini_key", None),
            "mistral_key":  getattr(settings, "mistral_key", None),
            "replicate_key": getattr(settings, "replicate_key", None),
            "openrouter_key": getattr(settings, "openrouter_key", None),
            "huggingface_key": getattr(settings, "huggingface_key", None),
            "potrace_path": getattr(settings, "potrace_path", "potrace"),
            "inkscape_path":getattr(settings, "inkscape_path", "inkscape"),
            "image_ai_provider": getattr(settings, "image_ai_provider", "banana") or "banana",
            "stencil_image_provider": getattr(settings, "stencil_image_provider", None) or getattr(settings, "image_ai_provider", "banana") or "banana",
            "mockup_image_provider": getattr(settings, "mockup_image_provider", None) or getattr(settings, "image_ai_provider", "banana") or "banana",
            "stencil_image_quality": getattr(settings, "stencil_image_quality", "auto") or "auto",
            "mockup_image_quality": getattr(settings, "mockup_image_quality", "auto") or "auto",
            "text_ai_provider":  getattr(settings, "text_ai_provider", "gemini-2.0-flash-lite") or "gemini-2.0-flash-lite",
            "prompt_image_generation": getattr(settings, "prompt_image_generation", None),
        }

        import re
        safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
        if not safe_theme:
            safe_theme = f"design_{creation_id}"

        creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
        source_png = os.path.join(creation_dir, os.path.basename(creation.source_png_path))
        binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")

        # 1. Binarize
        local_binarize_image(source_png, binarized_png)

        # 2. Slice (based on creation.bundle_size)
        bundle_size = creation.bundle_size or 1
        element_paths = []
        if bundle_size > 1 and creation.source_type != "vector_svg":
            element_paths = split_multielement_image(binarized_png, creation_dir, bundle_size)
        if not element_paths:
            element_paths = [binarized_png]

        elements = []
        for idx, el_png in enumerate(element_paths):
            el_name = safe_theme if len(element_paths) == 1 else f"{safe_theme}_{idx+1}"
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

        # 3. Vectorize, CAD, Upscale, PDF
        svg_urls = []
        dxf_urls = []
        ai_urls = []
        eps_urls = []
        png_urls = []
        pdf_urls = []
        inkscape_bin = settings_snap["inkscape_path"]

        for el in elements:
            if os.path.exists(el["source_png"]):
                # transparent high quality upscale
                convert_to_transparent_png(el["source_png"], el["upscale_png"], 3)
                if os.path.exists(el["upscale_png"]):
                    png_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['upscale_png'])}")
                
                # potrace vectorisation
                png_to_svg(settings_snap["potrace_path"], el["source_png"], el["svg_path"], inkscape_bin)
                if os.path.exists(el["svg_path"]):
                    svg_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['svg_path'])}")
                    # CAD conversion
                    svg_to_dxf(inkscape_bin, el["svg_path"], el["dxf_path"], el["source_png"])
                    svg_to_ai(inkscape_bin, el["svg_path"], el["ai_path"])
                    svg_to_eps(inkscape_bin, el["svg_path"], el["eps_path"])
                    if os.path.exists(el["dxf_path"]):
                        dxf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['dxf_path'])}")
                    if os.path.exists(el["ai_path"]):
                        ai_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['ai_path'])}")
                    if os.path.exists(el["eps_path"]):
                        eps_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['eps_path'])}")
                    
                    # PDF conversion
                    if os.path.exists(el["svg_path"]):
                        svg_to_pdf(inkscape_bin, el["svg_path"], el["pdf_path"], el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"])
                    if os.path.exists(el["pdf_path"]):
                        pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")

        # 4. Mockups
        master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
        if os.path.exists(binarized_png):
            convert_to_transparent_png(binarized_png, master_upscale, 3)
        png_for_mockup = master_upscale if os.path.exists(master_upscale) else binarized_png
        
        # Load styles from DB column (preferred) or fallback to mockup_styles.json
        parsed_styles = ["classic_living_room"]
        if creation.mockup_styles:
            try:
                parsed_styles = json.loads(creation.mockup_styles)
            except Exception:
                parsed_styles = ["classic_living_room"]
        else:
            styles_file = os.path.join(creation_dir, "mockup_styles.json")
            if os.path.exists(styles_file):
                try:
                    with open(styles_file, "r", encoding="utf-8") as f_styles:
                        styles_data = json.load(f_styles)
                        parsed_styles = styles_data.get("styles", ["classic_living_room"])
                except Exception:
                    pass

        first_raw_path = None
        first_comm_path = None
        mockup_raw_paths = []
        mockup_commercial_paths = []

        for s_idx, style_name in enumerate(parsed_styles):
            style_prompt = MOCKUP_STYLE_PROMPTS.get(style_name, style_name)
            mockup_raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw_{s_idx+1}.jpg")
            mockup_commercial_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial_{s_idx+1}.jpg")
            try:
                backdrop_bytes = generate_mockup_backdrop(
                    style_prompt,
                    settings_snap["openai_key"],
                    custom_prompt=settings_snap.get("prompt_image_generation"),
                    model=settings_snap.get("mockup_image_provider"),
                    quality=settings_snap.get("mockup_image_quality")
                )
                temp_bg = os.path.join(creation_dir, f"temp_bg_{style_name}_{s_idx}.jpg")
                with open(temp_bg, 'wb') as f_bg:
                    f_bg.write(backdrop_bytes)
                    
                # Raw Mockup
                composite_stencil_on_bg(
                    stencil_path=png_for_mockup,
                    bg_path=temp_bg,
                    output_path=mockup_raw_path,
                    material="matte_black_metal",
                    apply_tp_overlay=False
                )
                # Commercial Mockup
                composite_stencil_on_bg(
                    stencil_path=png_for_mockup,
                    bg_path=temp_bg,
                    output_path=mockup_commercial_path,
                    material="matte_black_metal",
                    apply_tp_overlay=True
                )
                
                if s_idx == 0:
                    first_raw_path = mockup_raw_path
                    first_comm_path = mockup_commercial_path

                if os.path.exists(mockup_raw_path):
                    mockup_raw_paths.append(mockup_raw_path)
                if os.path.exists(mockup_commercial_path):
                    mockup_commercial_paths.append(mockup_commercial_path)

                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
            except Exception as mockup_err:
                print(f"[pipeline] Reprocess Mockup style {style_name} failed: {mockup_err}")

        # 5. ZIP Packaging
        zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
        assets_to_zip = []
        for el in elements:
            for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                p = el[path_key]
                if p and os.path.exists(p):
                    assets_to_zip.append(p)
        for raw_p in mockup_raw_paths:
            assets_to_zip.append(raw_p)

        if assets_to_zip:
            package_assets(assets_to_zip, zip_path)
            
        # Update DB values
        creation.svg_path = svg_urls[0] if svg_urls else None
        creation.svg_paths = svg_urls
        creation.dxf_path = dxf_urls[0] if dxf_urls else None
        creation.dxf_paths = dxf_urls
        creation.ai_path = ai_urls[0] if ai_urls else None
        creation.ai_paths = ai_urls
        creation.eps_path = eps_urls[0] if eps_urls else None
        creation.eps_paths = eps_urls
        creation.upscale_png_path = png_urls[0] if png_urls else None
        creation.png_paths = png_urls
        creation.pdf_path = pdf_urls[0] if pdf_urls else None
        creation.pdf_paths = pdf_urls
        creation.mockup_path = f"/static/creation_{creation_id}/{os.path.basename(first_raw_path)}" if first_raw_path and os.path.exists(first_raw_path) else None
        creation.mockup_paths = [f"/static/creation_{creation_id}/{os.path.basename(p)}" for p in mockup_raw_paths]
        creation.real_mockup_path = f"/static/creation_{creation_id}/{os.path.basename(first_comm_path)}" if first_comm_path and os.path.exists(first_comm_path) else None
        creation.real_mockup_paths = [f"/static/creation_{creation_id}/{os.path.basename(p)}" for p in mockup_commercial_paths]
        # Also save to commercial_mockup_paths so section 6b instantly sees them
        if mockup_commercial_paths:
            comm_urls = [f"/static/creation_{creation_id}/{os.path.basename(p)}" for p in mockup_commercial_paths]
            creation.commercial_mockup_paths = comm_urls
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}" if os.path.exists(zip_path) else None
        creation.status = "completed"
        creation.current_step = "Terminé ✓"
        db.commit()
    except Exception as e:
        print(f"[pipeline] Background processing failed: {e}")
        import traceback
        traceback.print_exc()
        if creation_id:
            _update_creation(creation_id, status="failed", failed_reason=str(e), current_step="Erreur")
    finally:
        db.close()


def run_downstream_pipeline_operations(creation_id: int, local_path: str, asset_type: str):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
        
        if asset_type == "master_stencil":
            from ..services.image_engine import local_binarize_opaque
            local_binarize_opaque(local_path, local_path)
            reprocess_creation_assets(creation.id)

        elif asset_type == "split_element":
            from ..services.image_engine import convert_to_transparent_png
            convert_to_transparent_png(local_path, local_path, 3)

            settings = get_or_create_settings(db)
            creation_dir = os.path.dirname(local_path)
            import re
            safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
            if not safe_theme:
                safe_theme = f"design_{creation.id}"

            # 1. Regenerate vector/CAD files for this specific split element
            from ..services.vector import png_to_svg, svg_to_dxf
            from ..services.export_formats import svg_to_ai, svg_to_eps
            from ..services.image import png_to_pdf

            base_name = os.path.splitext(os.path.basename(local_path))[0]
            svg_el_path = os.path.join(creation_dir, f"{base_name}.svg")
            dxf_el_path = os.path.join(creation_dir, f"{base_name}.dxf")
            ai_el_path = os.path.join(creation_dir, f"{base_name}.ai")
            eps_el_path = os.path.join(creation_dir, f"{base_name}.eps")
            pdf_el_path = os.path.join(creation_dir, f"{base_name}.pdf")
            upscale_png_el = os.path.join(creation_dir, f"{base_name}.png")

            # Upscale transparent PNG
            convert_to_transparent_png(local_path, upscale_png_el, 3)
            # Vectorize
            png_to_svg(settings.potrace_path, local_path, svg_el_path, settings.inkscape_path)
            # Convert CAD
            if os.path.exists(svg_el_path):
                svg_to_dxf(settings.inkscape_path, svg_el_path, dxf_el_path, local_path)
                svg_to_ai(settings.inkscape_path, svg_el_path, ai_el_path)
                svg_to_eps(settings.inkscape_path, svg_el_path, eps_el_path)
                # Export PDF
                svg_to_pdf(settings.inkscape_path, svg_el_path, pdf_el_path, upscale_png_el if os.path.exists(upscale_png_el) else local_path)

            # Re-generate mockup & zip for this split element
            import time
            ts = int(time.time())
            match = re.search(r'_(\d+)$', base_name)
            idx = int(match.group(1)) if match else 1

            mockup_raw_path = os.path.join(creation_dir, f"Fichier_Import_mockup_raw_{idx}_{ts}.jpg")
            
            temp_bg = None
            try:
                backdrop_bytes = generate_mockup_backdrop(
                    creation.theme or "Design",
                    settings.openai_key,
                    custom_prompt=settings.prompt_image_generation,
                    model=settings.mockup_image_provider,
                    quality=settings.mockup_image_quality
                )
                temp_bg = os.path.join(creation_dir, f"temp_bg_{creation_id}.jpg")
                with open(temp_bg, 'wb') as f_bg:
                    f_bg.write(backdrop_bytes)
            except Exception as mockup_err:
                print(f"[pipeline] split_element backdrop generation failed: {mockup_err}. Trying static backgrounds.")

            if not temp_bg:
                bg_candidates = [
                    os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/classic_living_room.jpg")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets/backgrounds/classic_living_room.jpg")),
                ]
                temp_bg = next((p for p in bg_candidates if os.path.exists(p)), None)

            try:
                # Raw Mockup ONLY
                composite_stencil_on_bg(
                    stencil_path=local_path,
                    bg_path=temp_bg,
                    output_path=mockup_raw_path,
                    material="matte_black_metal",
                    apply_tp_overlay=False
                )
            finally:
                if temp_bg and os.path.exists(temp_bg) and "temp_bg" in os.path.basename(temp_bg):
                    try:
                        os.remove(temp_bg)
                    except Exception:
                        pass

            creation.mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
            # Update mockup_paths list
            if os.path.exists(mockup_raw_path):
                existing_mockups = creation.mockup_paths or []
                new_mockup_url = f"/static/creation_{creation.id}/{os.path.basename(mockup_raw_path)}"
                if new_mockup_url not in existing_mockups:
                    existing_mockups.append(new_mockup_url)
                creation.mockup_paths = existing_mockups

            # Clear commercial mockups paths
            creation.real_mockup_path = None
            creation.real_mockup_paths = []

            # Rebuild assets list for ZIP and package it
            assets_to_zip = []
            for path_list_name in ["svg_paths", "dxf_paths", "ai_paths", "eps_paths", "pdf_paths", "png_paths", "mockup_paths"]:
                urls = getattr(creation, path_list_name, []) or []
                for url in urls:
                    if url:
                        p = url.replace("/static/", STORAGE_DIR + "/")
                        if os.path.exists(p) and p not in assets_to_zip:
                            assets_to_zip.append(p)

            # Ensure the newly generated/updated files are also included if they weren't in the lists yet
            for p in [svg_el_path, dxf_el_path, ai_el_path, eps_el_path, pdf_el_path, upscale_png_el, mockup_raw_path]:
                if os.path.exists(p) and p not in assets_to_zip:
                    assets_to_zip.append(p)

            zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
            if assets_to_zip:
                package_assets(assets_to_zip, zip_path)
                creation.zip_path = f"/static/creation_{creation.id}/{os.path.basename(zip_path)}"

            creation.status = "completed"
            creation.current_step = "Terminé ✓"
            db.commit()
            
    except Exception as e:
        print(f"[pipeline] Background processing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# MODULAR PIPELINE GENERATOR (ASYNC GENERATOR)
# ─────────────────────────────────────────────────────────────────────────────
async def _modular_pipeline_generator(
    creation_id: int,
    generate_ai_stencil: bool,
    vectorize: bool,
    convert_cad: bool,
    format_pdf: bool,
    upscale: bool,
    generate_real_mockup: bool,
    use_ai_mockup: bool,
    package: bool,
    generate_seo: bool,
    theme: str,
    image_ai_provider: Optional[str] = "openai",
    text_ai_provider: Optional[str] = "gemini",
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True,
    mockup_styles: Optional[str] = None,
    session_token: Optional[str] = None,
    n_images: int = 1,
    apply_tp_overlay: bool = False,
    apply_binarization: bool = True
) -> AsyncGenerator[str, None]:
    """Streams progress for a modular pipeline on an already-created row."""
    db = SessionLocal()
    db_theme = None
    existing_source_png_path = None
    bundle_size = 1
    db_source_type = "text_prompt"
    variants = []
    try:
        settings = get_or_create_settings(db)
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            yield _sse("error", {"msg": f"Creation {creation_id} not found."})
            return
        db_theme = creation.theme
        existing_source_png_path = creation.source_png_path
        variants = creation.source_png_variants
        bundle_size = creation.bundle_size or 1
        db_source_type = creation.source_type or "text_prompt"
        settings_snap = {
            "gemini_key":   settings.gemini_key,
            "mistral_key":  settings.mistral_key,
            "openai_key":   settings.openai_key,
            "banana_key":   settings.banana_key,
            "replicate_key": settings.replicate_key,
            "openrouter_key": settings.openrouter_key,
            "huggingface_key": settings.huggingface_key,
            "anthropic_key": settings.anthropic_key,
            "stability_key": getattr(settings, "stability_key", None),
            "potrace_path": settings.potrace_path,
            "inkscape_path":settings.inkscape_path,
            "image_ai_provider": preferred_image_provider or image_ai_provider or getattr(settings, "image_ai_provider", "openai") or "openai",
            "stencil_image_provider": preferred_image_provider or image_ai_provider or getattr(settings, "stencil_image_provider", None) or getattr(settings, "image_ai_provider", "openai") or "openai",
            "mockup_image_provider": getattr(settings, "mockup_image_provider", None) or getattr(settings, "image_ai_provider", "openai") or "openai",
            "stencil_image_quality": getattr(settings, "stencil_image_quality", "auto") or "auto",
            "mockup_image_quality": getattr(settings, "mockup_image_quality", "auto") or "auto",
            "text_ai_provider":  preferred_text_provider or text_ai_provider or getattr(settings, "text_ai_provider", "gemini-2.0-flash-lite") or "gemini-2.0-flash-lite",
            "prompt_image_generation": getattr(settings, "prompt_image_generation", None),
        }
        creation.status = "processing"
        db.commit()
    finally:
        db.close()

    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme or db_theme or "").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"

    resolved_source_type = (source_type or db_source_type or "text_prompt").lower().strip()
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    
    # Resolve source_filename safely in case of multiple files upload
    source_filename = None
    if existing_source_png_path:
        test_path = os.path.join(creation_dir, os.path.basename(existing_source_png_path))
        if os.path.exists(test_path):
            source_filename = os.path.basename(existing_source_png_path)
        elif variants:
            first_var_name = os.path.basename(variants[0])
            first_var_path = os.path.join(creation_dir, first_var_name)
            if os.path.exists(first_var_path):
                source_filename = first_var_name
                # Fix DB entry
                _update_creation(creation_id, source_png_path=f"/static/creation_{creation_id}/{first_var_name}")
                existing_source_png_path = f"/static/creation_{creation_id}/{first_var_name}"
                
    if not source_filename:
        source_filename = os.path.basename(existing_source_png_path) if existing_source_png_path else f"{safe_theme}_source.png"
        
    source_png  = os.path.join(creation_dir, source_filename)
    binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
    svg_path    = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path    = os.path.join(creation_dir, f"{safe_theme}.dxf")
    ai_path     = os.path.join(creation_dir, f"{safe_theme}.ai")
    eps_path    = os.path.join(creation_dir, f"{safe_theme}.eps")
    pdf_path    = os.path.join(creation_dir, f"{safe_theme}.pdf")
    upscale_png   = os.path.join(creation_dir, f"{safe_theme}.png")
    mockup_path   = os.path.join(creation_dir, f"{safe_theme}_mockup.jpg")
    zip_path    = os.path.join(creation_dir, f"{safe_theme}.zip")
    inkscape_bin = settings_snap["inkscape_path"]

    init_image_path = None
    if existing_source_png_path:
        existing_source = os.path.join(STORAGE_DIR, f"creation_{creation_id}", os.path.basename(existing_source_png_path))
        if os.path.exists(existing_source):
            init_image_path = existing_source + ".init.png"
            if not os.path.exists(init_image_path):
                shutil.copy(existing_source, init_image_path)

    step = 0
    try:
        # ── PREPARATION / GENERATION ──
        if resolved_source_type == "vector_svg":
            source_svg_uploaded = os.path.join(creation_dir, f"{safe_theme}_source.svg")
            uploaded_file = source_svg_uploaded if os.path.exists(source_svg_uploaded) else source_png
            is_valid_svg = False
            if os.path.exists(uploaded_file):
                try:
                    with open(uploaded_file, "r", encoding="utf-8", errors="ignore") as f_svg:
                        content = f_svg.read(1000).strip()
                        if "<svg" in content or "svg" in content.lower():
                            is_valid_svg = True
                            if uploaded_file != svg_path:
                                shutil.copy(uploaded_file, svg_path)
                except Exception as svg_err:
                    print(f"Error copying/validating SVG: {svg_err}")

            rendered = await asyncio.to_thread(
                svg_to_high_quality_png, inkscape_bin, svg_path, upscale_png, 300
            )
            if not rendered or not os.path.exists(upscale_png):
                if os.path.exists(svg_path):
                    try:
                        from PIL import Image
                        fallback_img = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
                        fallback_img.save(upscale_png, "PNG")
                    except Exception as ie:
                        print(f"[pipeline] Failed to create transparent PNG fallback: {ie}")
            
            if os.path.exists(upscale_png):
                shutil.copy(upscale_png, source_png)

            _update_creation(
                creation_id,
                svg_path=f"/static/creation_{creation_id}/{os.path.basename(svg_path)}" if os.path.exists(svg_path) else None,
                source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}" if os.path.exists(source_png) else None,
                upscale_png_path=f"/static/creation_{creation_id}/{os.path.basename(upscale_png)}" if os.path.exists(upscale_png) else None
            )
            yield _sse("image_ready", {
                "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}" if os.path.exists(source_png) else None
            })
            yield _sse("assets_ready", {
                "upscale_png_path": f"/static/creation_{creation_id}/{os.path.basename(upscale_png)}" if os.path.exists(upscale_png) else None
            })

        elif resolved_source_type in ("raw_image", "text_prompt"):
            if generate_ai_stencil:
                step += 1
                yield _status(step, "Génération IA du pochoir N&B...")
                _update_creation(creation_id, current_step="Génération Pochoir...")
                
                try:
                    stencil_result = await asyncio.to_thread(
                        generate_stencil_image,
                        provider=settings_snap.get("stencil_image_provider") or settings_snap.get("image_ai_provider"),
                        banana_key=settings_snap["banana_key"],
                        openai_key=settings_snap["openai_key"],
                        theme=theme or "Design",
                        output_path=source_png,
                        init_image_path=init_image_path,
                        bundle_size=bundle_size,
                        design_style=design_style,
                        gemini_key=settings_snap.get("gemini_key"),
                        replicate_key=settings_snap.get("replicate_key"),
                        openrouter_key=settings_snap.get("openrouter_key"),
                        huggingface_key=settings_snap.get("huggingface_key"),
                        stability_key=settings_snap.get("stability_key"),
                        strict_fidelity=strict_fidelity,
                        n_images=n_images,
                        quality=settings_snap.get("stencil_image_quality", "auto"),
                        mockup_provider=settings_snap.get("mockup_image_provider"),
                        mockup_quality=settings_snap.get("mockup_image_quality", "auto"),
                        apply_binarization=apply_binarization
                    )
                    
                    stencil_mod_provider = stencil_result.get("provider", settings_snap["image_ai_provider"]) if isinstance(stencil_result, dict) else settings_snap["image_ai_provider"]
                    stencil_mod_prompt = stencil_result.get("prompt", "") if isinstance(stencil_result, dict) else ""
                    vision_description = stencil_result.get("vision_description", "") if isinstance(stencil_result, dict) else ""
                    
                    # Resolve variants list
                    raw_saved_paths = stencil_result.get("saved_paths", []) if isinstance(stencil_result, dict) else [source_png]
                    static_variants = [f"/static/creation_{creation_id}/{os.path.basename(p)}" for p in raw_saved_paths]
                    
                    # Update database with all generated variants
                    _update_creation(
                        creation_id,
                        source_png_path=static_variants[0] if static_variants else f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        source_png_variants=static_variants
                    )
                    
                    yield _sse("image_ready", {
                        "source_png_path": static_variants[0] if static_variants else f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        "provider": stencil_mod_provider,
                        "prompt": stencil_mod_prompt,
                        "vision_description": vision_description,
                        "status": "success",
                        "source_png_variants": static_variants
                    })
                except Exception as e:
                    print(f"CRITICAL STENCIL ERROR CAUGHT: {e}")
                    _update_creation(creation_id, status="failed", failed_reason=f"Stencil generation failed: {e}", current_step="Échec")
                    yield _sse("stencil_failed", {"error": str(e)})
                    return

        elif resolved_source_type == "ready_bw_image":
            step += 1
            yield _status(step, "Binarisation et détourage de l'image...")
            _update_creation(creation_id, current_step="Détourage image...")
            try:
                await asyncio.to_thread(local_binarize_opaque, source_png, source_png, apply_binarization)
                _update_creation(
                    creation_id,
                    source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                )
                yield _sse("image_ready", {
                    "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                })
            except Exception as e:
                print(f"[pipeline] Binarization error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"Binarization failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La binarisation a échoué: {e}", "creation_id": creation_id})
                return

        # ── ELEMENT SPLITTING ──
        source_files = [source_png]
        assembled_paths = []
        if output_assembled:
            assembled_paths.append(source_png)

        element_paths = []
        if output_split and resolved_source_type != "vector_svg":
            step += 1
            yield _status(step, "Détection et séparation des éléments du pack...")
            try:
                for idx, s_file in enumerate(source_files):
                    split_res = await asyncio.to_thread(
                        split_multielement_image, s_file, creation_dir, bundle_size
                    )
                    element_paths.extend(split_res)
            except Exception as e:
                print(f"[pipeline] Splitting error: {e}")

        all_paths = list(dict.fromkeys(assembled_paths + element_paths))
        elements = []
        for idx, el_png in enumerate(all_paths):
            el_name = safe_theme if len(all_paths) == 1 else f"{safe_theme}_{idx+1}"
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

        # ── VECTORIZATION (PNG → SVG) ──
        if vectorize and resolved_source_type != "vector_svg":
            step += 1
            yield _status(step, f"Vectorisation (PNG → SVG) pour {len(elements)} éléments...")
            svg_urls = []
            try:
                for el in elements:
                    if os.path.exists(el["source_png"]):
                        await asyncio.to_thread(png_to_svg, settings_snap["potrace_path"], el["source_png"], el["svg_path"], settings_snap["inkscape_path"])
                        if os.path.exists(el["svg_path"]):
                            svg_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['svg_path'])}")
                
                if svg_urls:
                    master_svg = svg_urls[0]
                    connectivity = await asyncio.to_thread(analyze_svg_connectivity, elements[0]["svg_path"])
                    _update_creation(
                        creation_id,
                        svg_path=master_svg,
                        svg_paths=svg_urls,
                        connectivity_warnings=max(0, connectivity.get("island_count", 1) - 1)
                    )
                    yield _sse("vector_ready", {
                        "svg_path": master_svg,
                        "svg_paths": svg_urls,
                        "connectivity": connectivity
                    })
                    if connectivity.get("severity") in ("warning", "critical"):
                        yield _sse("connectivity_warning", connectivity)
            except Exception as e:
                print(f"[pipeline] Vectorization error: {e}")

        # ── CONVERT CAD (SVG → DXF + AI + EPS) ──
        if convert_cad:
            step += 1
            yield _status(step, f"Génération DXF, AI, EPS ({len(elements)} éléments)...")
            dxf_urls, ai_urls, eps_urls = [], [], []
            try:
                for el in elements:
                    if os.path.exists(el["svg_path"]):
                        await asyncio.to_thread(svg_to_dxf, inkscape_bin, el["svg_path"], el["dxf_path"], el["source_png"])
                        await asyncio.to_thread(svg_to_ai, inkscape_bin, el["svg_path"], el["ai_path"])
                        await asyncio.to_thread(svg_to_eps, inkscape_bin, el["svg_path"], el["eps_path"])
                        if os.path.exists(el["dxf_path"]):
                            dxf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['dxf_path'])}")
                        if os.path.exists(el["ai_path"]):
                            ai_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['ai_path'])}")
                        if os.path.exists(el["eps_path"]):
                            eps_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['eps_path'])}")
                
                _update_creation(
                    creation_id,
                    dxf_path=dxf_urls[0] if dxf_urls else None,
                    dxf_paths=dxf_urls,
                    ai_path=ai_urls[0] if ai_urls else None,
                    ai_paths=ai_urls,
                    eps_path=eps_urls[0] if eps_urls else None,
                    eps_paths=eps_urls,
                )
                yield _sse("assets_ready", {
                    "dxf_path": dxf_urls[0] if dxf_urls else None,
                    "dxf_paths": dxf_urls,
                    "ai_path":  ai_urls[0] if ai_urls else None,
                    "ai_paths":  ai_urls,
                    "eps_path": eps_urls[0] if eps_urls else None,
                    "eps_paths": eps_urls,
                })
            except Exception as e:
                print(f"[pipeline] CAD conversion error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"CAD conversion failed: {e}", current_step="Échec")

        # ── UPSCALING ──
        if upscale:
            step += 1
            yield _status(step, f"Upscaling PNG transparent x3 ({len(elements)} éléments)...")
            png_urls = []
            try:
                for el in elements:
                    if os.path.exists(el["source_png"]):
                        await asyncio.to_thread(convert_to_transparent_png, el["source_png"], el["upscale_png"], 3)
                        if os.path.exists(el["upscale_png"]):
                            png_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['upscale_png'])}")
                if png_urls:
                    _update_creation(
                        creation_id,
                        upscale_png_path=png_urls[0],
                        png_paths=png_urls
                    )
                    yield _sse("assets_ready", {
                        "upscale_png_path": png_urls[0],
                        "png_paths": png_urls
                    })
            except Exception as e:
                print(f"[pipeline] Upscaling error: {e}")

        # ── PDF EXPORT ──
        if format_pdf:
            step += 1
            yield _status(step, f"Génération PDF ({len(elements)} éléments)...")
            pdf_urls = []
            try:
                for el in elements:
                    png_src = el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"]
                    if os.path.exists(png_src):
                        await asyncio.to_thread(png_to_pdf, png_src, el["pdf_path"])
                        if os.path.exists(el["pdf_path"]):
                            pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
                
                _update_creation(creation_id, pdf_path=pdf_urls[0] if pdf_urls else None, pdf_paths=pdf_urls)
                yield _sse("assets_ready", {"pdf_path": pdf_urls[0] if pdf_urls else None, "pdf_paths": pdf_urls})
            except Exception as e:
                print(f"[pipeline] PDF generation failed: {e}")

        # ── MARKETING & MOCKUPS ──
        first_raw_path = None
        first_comm_path = None
        mockup_raw_paths = []
        mockup_comm_paths = []

        if generate_real_mockup:
            step += 1
            yield _status(step, "Création des mockups e-commerce...")

            parsed_styles = []
            if mockup_styles:
                try:
                    parsed_styles = json.loads(mockup_styles)
                except Exception:
                    parsed_styles = [x.strip() for x in mockup_styles.split(",") if x.strip()]
            if not parsed_styles:
                parsed_styles = ["classic_living_room"]

            # Persist styles to DB column so reprocess_creation_assets can recover them
            _update_creation(creation_id, mockup_styles=json.dumps(parsed_styles))
            # Also write JSON file as backward-compat fallback
            styles_file = os.path.join(creation_dir, "mockup_styles.json")
            try:
                with open(styles_file, "w", encoding="utf-8") as f_styles:
                    json.dump({"styles": parsed_styles}, f_styles)
            except Exception as e:
                print(f"Failed to write mockup_styles.json: {e}")

            # --- Resolve best available PNG for mockup compositing ---
            # Priority: first upscaled element > first source element > DB paths
            png_for_mockup = None
            for el in elements:
                if os.path.exists(el["upscale_png"]):
                    png_for_mockup = el["upscale_png"]
                    break
            if not png_for_mockup:
                for el in elements:
                    if os.path.exists(el["source_png"]):
                        png_for_mockup = el["source_png"]
                        break
            if not png_for_mockup and existing_source_png_path:
                candidate = os.path.join(creation_dir, os.path.basename(existing_source_png_path))
                if os.path.exists(candidate):
                    png_for_mockup = candidate
            if not png_for_mockup:
                print(f"[pipeline] No source PNG found for mockup compositing in creation_{creation_id}, skipping.")
                generate_real_mockup = False  # abort this block cleanly

            if generate_real_mockup:
                import time
                ts = int(time.time())

                for s_idx, style in enumerate(parsed_styles):
                    try:
                        style_prompt = MOCKUP_STYLE_PROMPTS.get(style, style)
                        bg_source = None

                        if use_ai_mockup:
                            try:
                                # Generate AI backdrop via DALL-E
                                backdrop_bytes = generate_mockup_backdrop(
                                    style_prompt,
                                    settings_snap["openai_key"],
                                    custom_prompt=settings_snap.get("prompt_image_generation"),
                                    model=settings_snap.get("mockup_image_provider"),
                                    quality=settings_snap.get("mockup_image_quality")
                                )
                                temp_bg = os.path.join(creation_dir, f"temp_bg_{style}_{s_idx}.jpg")
                                with open(temp_bg, 'wb') as f_bg:
                                    f_bg.write(backdrop_bytes)
                                bg_source = temp_bg
                            except Exception as ai_err:
                                print(f"[pipeline] AI backdrop generation failed: {ai_err}. Trying static backgrounds.")

                        if not bg_source:
                            # Use static background from assets/backgrounds if available
                            bg_candidates = [
                                os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/{style}.jpg"),
                                os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/classic_living_room.jpg"),
                                os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/{style}.jpg")),
                                os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/classic_living_room.jpg")),
                                os.path.abspath(os.path.join(os.path.dirname(__file__), f"../assets/backgrounds/{style}.jpg")),
                                os.path.abspath(os.path.join(os.path.dirname(__file__), f"../assets/backgrounds/classic_living_room.jpg")),
                            ]
                            bg_source = next((p for p in bg_candidates if os.path.exists(p)), None)
                            
                            if not bg_source and not use_ai_mockup:
                                # Fallback to AI if no static bg found
                                try:
                                    backdrop_bytes = generate_mockup_backdrop(
                                        style_prompt,
                                        settings_snap["openai_key"],
                                        custom_prompt=settings_snap.get("prompt_image_generation"),
                                        model=settings_snap.get("mockup_image_provider"),
                                        quality=settings_snap.get("mockup_image_quality")
                                    )
                                    temp_bg = os.path.join(creation_dir, f"temp_bg_{style}_{s_idx}.jpg")
                                    with open(temp_bg, 'wb') as f_bg:
                                        f_bg.write(backdrop_bytes)
                                    bg_source = temp_bg
                                except Exception as ai_err:
                                    print(f"[pipeline] Fallback AI backdrop generation failed: {ai_err}.")

                        # Raw Mockup ONLY (without tp overlay)
                        mockup_raw = os.path.join(creation_dir, f"Fichier_Import_mockup_raw_{s_idx+1}_{ts}.jpg")
                        composite_stencil_on_bg(png_for_mockup, bg_source, mockup_raw, "matte_black_metal", False)

                        if s_idx == 0:
                            first_raw_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}"

                        if os.path.exists(mockup_raw):
                            mockup_raw_paths.append(f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}")

                            # Generate commercial mockup if apply_tp_overlay is True
                            if apply_tp_overlay:
                                import re
                                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', db_theme or "design").strip('_')
                                if not safe_theme:
                                    safe_theme = f"design_{creation_id}"
                                mockup_comm_filename = f"{safe_theme}_commercial_{s_idx+1}_{ts}.jpg"
                                mockup_comm_path = os.path.join(creation_dir, mockup_comm_filename)
                                try:
                                    from ..services.mockup_engine import apply_commercial_template_overlay
                                    apply_commercial_template_overlay(mockup_raw, mockup_comm_path)
                                    if os.path.exists(mockup_comm_path):
                                        comm_web_path = f"/static/creation_{creation_id}/{mockup_comm_filename}"
                                        mockup_comm_paths.append(comm_web_path)
                                        if s_idx == 0:
                                            first_comm_path = comm_web_path
                                except Exception as tp_err:
                                    print(f"[pipeline] Failed to apply tp overlay to mockup: {tp_err}")

                        # Clean up temp background
                        temp_bg_path = os.path.join(creation_dir, f"temp_bg_{style}_{s_idx}.jpg")
                        if os.path.exists(temp_bg_path):
                            try: os.remove(temp_bg_path)
                            except Exception: pass
                    except Exception as me:
                        import traceback
                        print(f"[pipeline] Failed composite for style '{style}': {me}")
                        print(traceback.format_exc())

                _update_creation(
                    creation_id,
                    mockup_path=first_raw_path,
                    mockup_paths=mockup_raw_paths,
                    real_mockup_path=first_comm_path,
                    real_mockup_paths=mockup_comm_paths,
                    commercial_mockup_paths=mockup_comm_paths,
                )
                if mockup_comm_paths:
                    db_loc = SessionLocal()
                    try:
                        creation_loc = db_loc.query(Creation).filter(Creation.id == creation_id).first()
                        if creation_loc:
                            existing_selected = [p.strip() for p in (creation_loc.selected_images_raw or "").split(",") if p.strip()]
                            for p in mockup_comm_paths:
                                if p not in existing_selected:
                                    existing_selected.append(p)
                            creation_loc.selected_images_raw = ",".join(existing_selected)
                            db_loc.commit()
                    except Exception as e:
                        print(f"[pipeline] Failed to auto-select commercial mockups for Etsy: {e}")
                    finally:
                        db_loc.close()

                yield _sse("mockup_ready", {
                    "mockup_path": first_raw_path,
                    "mockup_paths": mockup_raw_paths,
                    "real_mockup_path": first_comm_path,
                    "real_mockup_paths": mockup_comm_paths,
                    "commercial_mockup_paths": mockup_comm_paths
                })

        elif apply_tp_overlay:
            step += 1
            yield _status(step, "Application de la template commerciale sur l'image...")
            
            # --- Resolve best available PNG for mockup compositing ---
            png_for_mockup = None
            for el in elements:
                if os.path.exists(el["upscale_png"]):
                    png_for_mockup = el["upscale_png"]
                    break
            if not png_for_mockup:
                for el in elements:
                    if os.path.exists(el["source_png"]):
                        png_for_mockup = el["source_png"]
                        break
            if not png_for_mockup and existing_source_png_path:
                candidate = os.path.join(creation_dir, os.path.basename(existing_source_png_path))
                if os.path.exists(candidate):
                    png_for_mockup = candidate

            if png_for_mockup:
                import time
                ts = int(time.time())
                import re
                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', db_theme or "design").strip('_')
                if not safe_theme:
                    safe_theme = f"design_{creation_id}"
                mockup_comm_filename = f"{safe_theme}_commercial_direct_{ts}.jpg"
                mockup_comm_path = os.path.join(creation_dir, mockup_comm_filename)
                try:
                    from ..services.mockup_engine import apply_commercial_template_overlay
                    apply_commercial_template_overlay(png_for_mockup, mockup_comm_path)
                    if os.path.exists(mockup_comm_path):
                        comm_web_path = f"/static/creation_{creation_id}/{mockup_comm_filename}"
                        first_comm_path = comm_web_path
                        mockup_comm_paths = [comm_web_path]
                        
                        _update_creation(
                            creation_id,
                            real_mockup_path=first_comm_path,
                            real_mockup_paths=mockup_comm_paths,
                            commercial_mockup_paths=mockup_comm_paths,
                        )
                        
                        db_loc = SessionLocal()
                        try:
                            creation_loc = db_loc.query(Creation).filter(Creation.id == creation_id).first()
                            if creation_loc:
                                existing_selected = [p.strip() for p in (creation_loc.selected_images_raw or "").split(",") if p.strip()]
                                for p in mockup_comm_paths:
                                    if p not in existing_selected:
                                        existing_selected.append(p)
                                creation_loc.selected_images_raw = ",".join(existing_selected)
                                db_loc.commit()
                        except Exception as e:
                            print(f"[pipeline] Failed to auto-select commercial mockups for Etsy: {e}")
                        finally:
                            db_loc.close()

                        yield _sse("mockup_ready", {
                            "mockup_path": None,
                            "mockup_paths": [],
                            "real_mockup_path": first_comm_path,
                            "real_mockup_paths": mockup_comm_paths,
                            "commercial_mockup_paths": mockup_comm_paths
                        })
                except Exception as tp_err:
                    print(f"[pipeline] Failed to apply direct tp overlay: {tp_err}")

        # ── ZIP PACKAGING ──
        if package:
            step += 1
            yield _status(step, "Création de l'archive ZIP...")
            assets_to_zip = []
            for el in elements:
                for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                    p = el[path_key]
                    if p and os.path.exists(p):
                        assets_to_zip.append(p)
            
            # Add mockup paths to ZIP
            for raw_p in mockup_raw_paths:
                full_raw_p = os.path.join(creation_dir, os.path.basename(raw_p))
                if os.path.exists(full_raw_p):
                    assets_to_zip.append(full_raw_p)

            if assets_to_zip:
                assets_to_zip = list(dict.fromkeys(assets_to_zip))
                await asyncio.to_thread(package_assets, assets_to_zip, zip_path)
                _update_creation(creation_id, zip_path=f"/static/creation_{creation_id}/{os.path.basename(zip_path)}")
                yield _sse("assets_ready", {"zip_path": f"/static/creation_{creation_id}/{os.path.basename(zip_path)}"})

        # ── SEO AND COPYWRITING ──
        if generate_seo:
            if not theme:
                step += 1
                yield _status(step, "⚠️ SEO ignoré : le thème est vide. Renseignez un thème pour générer le SEO.", "warning")
            else:
                step += 1
                yield _status(step, f"Rédaction SEO bilingue ({settings_snap['text_ai_provider']})...")
                seo_image_path = upscale_png if os.path.exists(upscale_png) else (binarized_png if os.path.exists(binarized_png) else source_png)
                try:
                    seo = await asyncio.to_thread(
                        generate_etsy_seo,
                        theme=theme,
                        provider=settings_snap["text_ai_provider"],
                        gemini_key=settings_snap["gemini_key"],
                        mistral_key=settings_snap["mistral_key"],
                        openai_key=settings_snap["openai_key"],
                        replicate_key=settings_snap.get("replicate_key"),
                        openrouter_key=settings_snap.get("openrouter_key"),
                        huggingface_key=settings_snap.get("huggingface_key"),
                        anthropic_key=settings_snap.get("anthropic_key"),
                        db=None,
                        image_path=seo_image_path,
                        bundle_size=bundle_size
                    )

                    def _tag_list(t):
                        if not t: return []
                        return [x.strip() for x in t.split(",") if x.strip()] if isinstance(t, str) else t

                    def _tag_csv(t):
                        if not t: return ""
                        return ",".join(t) if isinstance(t, list) else t

                    def _description_fr(s):
                        return s.get("description_fr") or s.get("description") or ""

                    tags_fr = _tag_list(seo.get("tags_fr"))
                    tags_en = _tag_list(seo.get("tags_en"))

                    _update_creation(
                        creation_id,
                        title_fr=seo.get("title_fr"),
                        title_en=seo.get("title_en"),
                        description=_description_fr(seo),
                        description_en=seo.get("description_en"),
                        tags_fr=_tag_csv(tags_fr),
                        tags_en=_tag_csv(tags_en),
                    )
                    yield _sse("seo_ready", {
                        "title_fr":       seo.get("title_fr"),
                        "title_en":       seo.get("title_en"),
                        "description":    _description_fr(seo),
                        "description_fr": _description_fr(seo),
                        "description_en": seo.get("description_en"),
                        "tags_fr":        tags_fr,
                        "tags_en":        tags_en,
                    })
                except Exception as e:
                    print(f"[pipeline] SEO generation error: {e}")

        # ── COMPLIANCE CHECK ──
        # Runs run_compliance_check on the first element if SEO was generated
        try:
            db_fresh = SessionLocal()
            creation_fresh = db_fresh.query(Creation).filter(Creation.id == creation_id).first()
            if creation_fresh:
                compliance = await asyncio.to_thread(
                    run_compliance_check,
                    title_fr=creation_fresh.title_fr or "",
                    title_en=creation_fresh.title_en or "",
                    description=creation_fresh.description or "",
                    description_en=creation_fresh.description_en or "",
                    tags_fr=creation_fresh.tags_fr or "",
                    tags_en=creation_fresh.tags_en or "",
                )
                _update_creation(creation_id, compliance_warnings=compliance.to_json())
                yield _sse("compliance_result", compliance.to_dict())
            db_fresh.close()
        except Exception as ce:
            print(f"[pipeline] Compliance check failed: {ce}")

        _update_creation(creation_id, status="completed", current_step="Terminé ✓")
        yield _status(step + 1, "Modular pipeline execution completed! 🎉", status="complete")
        yield _sse("done", {"creation_id": creation_id})

    except Exception as e:
        print(f"[pipeline] Modular generator error: {e}")
        import traceback
        traceback.print_exc()
        _update_creation(creation_id, status="failed", failed_reason=str(e), current_step="Échec")
        yield _sse("error", {"msg": str(e), "creation_id": creation_id})


# ─────────────────────────────────────────────────────────────────────────────
# MODULAR PIPELINE STREAM ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stream/modular")
async def stream_modular_pipeline(
    creation_id: int,
    theme: str = "",
    generate_ai_stencil: bool = False,
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_real_mockup: bool = False,
    use_ai_mockup: bool = False,
    apply_tp_overlay: bool = False,
    package: bool = False,
    generate_seo: bool = False,
    image_ai_provider: Optional[str] = None,
    text_ai_provider: Optional[str] = None,
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True,
    session_token: Optional[str] = None,
    mockup_styles: Optional[str] = None,
    profile_tier: Optional[str] = "free",
    n_images: int = 1,
    apply_binarization: bool = True
):
    pref_img = preferred_image_provider or image_ai_provider
    pref_txt = preferred_text_provider or text_ai_provider
    return StreamingResponse(
        _modular_pipeline_generator(
            creation_id=creation_id,
            generate_ai_stencil=generate_ai_stencil,
            vectorize=vectorize,
            convert_cad=convert_cad,
            format_pdf=format_pdf,
            upscale=upscale,
            generate_real_mockup=generate_real_mockup,
            use_ai_mockup=use_ai_mockup,
            package=package,
            generate_seo=generate_seo,
            theme=theme,
            image_ai_provider=pref_img,
            text_ai_provider=pref_txt,
            design_style=design_style,
            source_type=source_type,
            output_assembled=output_assembled,
            output_split=output_split,
            strict_fidelity=strict_fidelity,
            mockup_styles=mockup_styles,
            session_token=session_token,
            n_images=n_images,
            apply_tp_overlay=apply_tp_overlay,
            apply_binarization=apply_binarization
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/stream/image")
async def stream_image(
    prompt: str,
    init_image_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    settings = get_or_create_settings(db)
    openai_key = settings.openai_key or os.getenv("OPENAI_API_KEY") or ""
    if not openai_key:
        raise HTTPException(status_code=400, detail="OpenAI API Key is missing.")
    return StreamingResponse(
        stream_dalle_image_progressive(openai_key, prompt, init_image_path, settings.image_ai_provider),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD FILE FOR MODULAR MODE
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/upload", response_model=CreationResponse)
async def upload_source_file(
    files: Optional[list[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    theme: str = Form("Fichier Importé"),
    bundle_size: int = Form(1),
    design_style: str = Form("classic"),
    source_type: Optional[str] = Form(None),
    source_is_multi_element: str = Form("single"),
    output_assembled: bool = Form(True),
    output_split: bool = Form(False),
    strict_fidelity: bool = Form(True),
    db: Session = Depends(get_db),
):
    uploaded_files = []
    if files:
        uploaded_files = files
    elif file:
        uploaded_files = [file]

    if not uploaded_files and not image_url and source_type != "text_prompt":
        raise HTTPException(status_code=400, detail="Aucun fichier ou image_url fourni.")

    # Intercept mask upload to strictly save it in tempfile directory to prevent DB pollution
    if theme.startswith("mask_") or theme.startswith("mask"):
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()

        # Save uploaded file
        if uploaded_files:
            with open(temp_file_path, "wb") as f_out:
                shutil.copyfileobj(uploaded_files[0].file, f_out)
        elif image_url:
            resp = requests.get(image_url, timeout=15)
            resp.raise_for_status()
            with open(temp_file_path, "wb") as f_out:
                f_out.write(resp.content)

        return {
            "id": 0,
            "theme": theme,
            "source_png_path": temp_file_path,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "is_published_etsy": False,
            "bundle_size": 1,
            "source_type": "ready_bw_image"
        }

    # Determine first file
    ref_filename = uploaded_files[0].filename if uploaded_files else (image_url or "file.png")
    inferred_type = source_type
    if not inferred_type:
        inferred_type = "raw_image"
        if ref_filename.lower().endswith(".svg"):
            inferred_type = "vector_svg"

    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
        bundle_size=bundle_size if len(uploaded_files) <= 1 else len(uploaded_files),
        source_type=inferred_type,
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)

    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme).strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation.id}"

    saved_paths = []
    is_svg = ref_filename.lower().endswith(".svg") or inferred_type == "vector_svg"

    def _save_upload_sync(file_file, path):
        with open(path, "wb") as f_out:
            shutil.copyfileobj(file_file, f_out)

    def _download_url_sync(url, path):
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(path, "wb") as f_out:
            f_out.write(resp.content)

    for idx, f_obj in enumerate(uploaded_files):
        suffix = f"_{idx+1}" if len(uploaded_files) > 1 else ""
        if is_svg:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.svg")
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
            saved_paths.append(target_path)
        else:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.png")
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
            saved_paths.append(target_path)

    # Handle image url fallback
    if not uploaded_files and image_url:
        suffix = ""
        if is_svg:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.svg")
            await asyncio.to_thread(_download_url_sync, image_url, target_path)
            saved_paths.append(target_path)
        else:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.png")
            await asyncio.to_thread(_download_url_sync, image_url, target_path)
            saved_paths.append(target_path)

    # Set variants to the paths we saved
    static_saved = [f"/static/creation_{creation.id}/{os.path.basename(p)}" for p in saved_paths]
    creation.source_png_variants = static_saved

    # Setup paths
    if static_saved:
        creation.source_png_path = static_saved[0]
    elif is_svg:
        creation.source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.svg"
    else:
        creation.source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
    
    db.commit()
    db.refresh(creation)
    return creation


# ─────────────────────────────────────────────────────────────────────────────
# INPAINTING & LOCAL CORRECTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/inpainting")
async def pipeline_inpainting(
    background_tasks: BackgroundTasks,
    image_path: str = Form(...),
    mask_path: str = Form(...),
    prompt: str = Form(...),
    output_path: str = Form(...),
    creation_id: int = Form(...)
):
    try:
        from ..routers.settings import get_or_create_settings
        db = SessionLocal()
        settings = get_or_create_settings(db)
        openai_key = settings.openai_key
        db.close()
        
        # Strip local server domain prefix
        for var_name in ["image_path", "mask_path", "output_path"]:
            val = locals().get(var_name)
            if val and (val.startswith("http://") or val.startswith("https://")):
                parsed_url = urllib.parse.urlparse(val)
                if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                    if var_name == "image_path": image_path = parsed_url.path
                    elif var_name == "mask_path": mask_path = parsed_url.path
                    elif var_name == "output_path": output_path = parsed_url.path

        image_path_clean = image_path.split("?")[0]
        mask_path_clean = mask_path.split("?")[0]
        output_path_clean = output_path.split("?")[0]
        
        local_img = image_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_mask = mask_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_out = output_path_clean.replace("/static/", STORAGE_DIR + "/")
        
        os.makedirs(os.path.dirname(local_out), exist_ok=True)

        try:
            model_provider = None
            try:
                model_provider = settings.image_ai_provider
            except Exception:
                pass
            await asyncio.to_thread(
                execute_inpainting,
                local_img,
                local_mask,
                prompt,
                local_out,
                openai_key,
                model_provider
            )
        finally:
            # Delete mask file from filesystem after call finishes
            if os.path.exists(local_mask) and STORAGE_DIR in local_mask:
                try:
                    os.remove(local_mask)
                    print(f"[pipeline] Cleaned up temporary mask: {local_mask}")
                except Exception as cleanup_err:
                    print(f"[pipeline] Failed to delete mask: {cleanup_err}")

        # Binarize output
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths
        _update_creation(creation_id, source_png_path=output_path_clean)
        
        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-correction")
async def pipeline_local_correction(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    creation_id: int = Form(...),
    output_path: str = Form(...)
):
    try:
        # Strip local server domain prefix
        if output_path.startswith("http://") or output_path.startswith("https://"):
            parsed_url = urllib.parse.urlparse(output_path)
            output_path = parsed_url.path

        output_path_clean = output_path.split("?")[0]
        local_out = output_path_clean.replace("/static/", STORAGE_DIR + "/")
        os.makedirs(os.path.dirname(local_out), exist_ok=True)
        
        def _write_bytes():
            with open(local_out, "wb") as f_out:
                shutil.copyfileobj(file.file, f_out)
        await asyncio.to_thread(_write_bytes)

        # Binarize output to ensure it remains a pure black/white stencil
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths
        _update_creation(creation_id, source_png_path=output_path_clean)
        
        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# WORKSPACE CANVAS SAVE ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/save-workspace", status_code=202)
async def save_workspace_canvas(
    req: SaveWorkspaceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        creation = db.query(Creation).filter(Creation.id == req.creation_id).first()
        if not creation:
            raise HTTPException(status_code=404, detail="Creation non trouvée")

        asset_path = req.asset_path
        if asset_path:
            if asset_path.startswith("http://") or asset_path.startswith("https://"):
                asset_path = "/" + asset_path.split("/", 3)[-1]
            local_path = asset_path.replace("/static/", STORAGE_DIR + "/")
        else:
            source_png_path = creation.source_png_path
            if not source_png_path:
                import re
                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
                if not safe_theme:
                    safe_theme = f"design_{creation.id}"
                source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
                creation.source_png_path = source_png_path
                db.commit()
            local_path = source_png_path.replace("/static/", STORAGE_DIR + "/")

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        canvas_data_raw = req.canvas_data or req.canvasData
        if not canvas_data_raw:
            raise HTTPException(status_code=400, detail="Missing canvasData or canvas_data")
        header, encoded = canvas_data_raw.split(",", 1)

        # Decode base64
        import base64
        decoded_bytes = base64.b64decode(encoded)

        def _write_bytes():
            with open(local_path, "wb") as f:
                f.write(decoded_bytes)
        await asyncio.to_thread(_write_bytes)

        asset_type = req.asset_type or "master_stencil"
        
        creation.status = "processing"
        creation.current_step = "Régénération des assets..."
        db.commit()

        # Schedule heavy processing as background task
        background_tasks.add_task(
            run_downstream_pipeline_operations,
            creation_id=creation.id,
            local_path=local_path,
            asset_type=asset_type
        )

        return {
            "status": "processing",
            "message": "Workspace saved. Downstream generation started in background."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


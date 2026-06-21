"""
SSE Streaming Pipeline Router — v3.0
Runs the full Etsy Laser Automation pipeline step by step and streams
real-time progress events to the frontend via Server-Sent Events.

Changements v3.0 :
- session_token pour la recovery côté client
- Export .ai et .eps intégrés (Step 3)
- Détection d'îles SVG (Step 2)
- Compliance check Etsy (Step 6)
- description_en sauvegardée en DB
- ZIP inclut SVG + DXF + AI + EPS + PDF + PNG
"""
import asyncio
import json
import os
import requests
import shutil
import base64
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import Creation
from ..routers.settings import get_or_create_settings
from ..services.image_engine import generate_stencil_image, split_multielement_image, local_binarize_image, local_binarize_opaque, stream_dalle_image_progressive
from ..services.seo_engine import generate_etsy_seo
from ..services.mockup_engine import generate_ai_mockup, composite_stencil_on_bg, create_real_mockup
from ..services.vector import png_to_svg, svg_to_dxf
from ..services.image import convert_to_transparent_png, package_assets, png_to_pdf
from ..services.export_formats import svg_to_ai, svg_to_eps, svg_to_high_quality_png
from ..services.svg_analyzer import analyze_svg_connectivity
from ..services.compliance import run_compliance_check

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline SSE"])

    os.path.join(os.path.dirname(__file__), "../../storage")
)
os.makedirs(STORAGE_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# SSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            if i in reconstructed_lines:
                # Find the best variant
                variants = reconstructed_lines[i]
                chosen_code = None
                # Try priority folders
                for pref in folder_priority:
                    for folder, code in variants:
                        if folder == pref:
                            chosen_code = code
                            break
                    if chosen_code is not None:
                        break
                if chosen_code is None:
                    # Fallback to the first one available
                    chosen_code = variants[0][1]
                out.write(chosen_code + "\n")
            else:
                out.write(f"# MISSING LINE {i}\n")
                
    print("Saved to reconstructed_all_folders.py")
    
    # Calculate missing lines in the reconstructed file
    missing = []
    with open("reconstructed_all_folders.py", "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if line.startswith("# MISSING LINE"):
                missing.append(idx + 1)
    print(f"Number of missing lines in reconstructed_all_folders.py: {len(missing)}")
    if missing:
        # Print ranges of missing lines
        ranges = []
        start = missing[0]
        prev = missing[0]
        for m in missing[1:]:
            if m == prev + 1:
                prev = m
            else:
                ranges.append((start, prev))
                start = m
                prev = m
        ranges.append((start, prev))
        print("Missing ranges:")
        for r in ranges:
            print(f"Lines {r[0]} to {r[1]} ({r[1] - r[0] + 1} lines)")

    creation_id: Optional[int] = None,
    design_style: str = "classic",
    bundle_size: int = 4,
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Pipeline complet avec 9 étapes :
    1. DALL-E 3 Image
    2. Binarisation (Otsu) — image standard (élimine anti-aliasing)
    3. Upscale ×3 du binaire propre — UNIQUEMENT pour PDF + PNG client transparent
    4. Vectorisation SVG (Potrace sur image binarisée standard, pas upscaled)
    5. Exports multi-format (DXF + AI + EPS)
    6. PDF depuis PNG upscalé x3 (haute résolution client)
    7. Mockup e-commerce
    8. ZIP packaging (tous les formats)
    9. SEO Gemini bilingue (FR + EN)
    10. Compliance check Etsy
    """
    db = SessionLocal()
    existing_source_png_path = None
    try:
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
            "text_ai_provider":  preferred_text_provider or getattr(settings, "text_ai_provider", "gemini-2.0-flash-lite") or "gemini-2.0-flash-lite",
            "potrace_path": getattr(settings, "potrace_path", "potrace"),
            "inkscape_path":getattr(settings, "inkscape_path", "inkscape"),
        }
    finally:
        db.close()

    # Yield creation_id + session_token pour le localStorage frontend
    yield _sse("created", {"creation_id": cid, "session_token": session_token})

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{cid}")
    os.makedirs(creation_dir, exist_ok=True)


    init_image_path = None
    if creation_id and existing_source_png_path:
        existing_source = os.path.join(STORAGE_DIR, f"creation_{cid}", os.path.basename(existing_source_png_path))

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

    # Initialize resilient pipeline status dictionary
    comp_status = {
        "stencil": {"status": "success", "paths": [], "error": None},
        "seo": {"status": "success", "data": None, "error": None},
        "mockup": {"status": "success", "paths": [], "error": None}
    }

    try:
        # ── STEP 1: Image AI Generation ────────────────────────────────────
        yield _status(1, f"Génération du motif IA ({settings_snap.get('image_ai_provider', 'banana')})...")
        _update_creation(cid, current_step="Génération d'Image...")
        try:
            result = await asyncio.to_thread(
                generate_stencil_image,
                settings_snap.get("image_ai_provider", "banana"),
                settings_snap.get("banana_key"),
                settings_snap.get("openai_key"),
                theme,
                source_png,
                init_image_path=init_image_path,
                bundle_size=bundle_size,
                design_style=design_style,
                gemini_key=settings_snap.get("gemini_key"),
                replicate_key=settings_snap.get("replicate_key"),
                openrouter_key=settings_snap.get("openrouter_key"),
                huggingface_key=settings_snap.get("huggingface_key"),
                stability_key=settings_snap.get("stability_key")
            )
            comp_status["stencil"]["paths"] = [f"/sta
            comp_status["stencil"]["paths"] = [f"/static/creation_{cid}/{os.path.basename(source_png)}"]
            # Capture prompt info from return dict (v5.0+ returns {"provider": ..., "prompt": ...})
            stencil_prompt = result.get("prompt", "") if isinstance(result, dict) else ""
            _update_creation(
                cid,
                source_png_path=f"/static/creation_{cid}/{os.path.basename(source_png)}",
                current_step="Image générée ✓",
                pipeline_status=json.dumps(comp_status)
            )
            yield _sse("image_ready", {
                "source_png_path": f"/static/creation_{cid}/{os.path.basename(source_png)}",
                "provider": stencil_provider,
                "prompt": stencil_prompt
            })
        except Exception as se:
            print(f"[pipeline] Stencil generation failed: {se}")
            comp_status["stencil"]["status"] = "failed"
            comp_status["stencil"]["error"] = str(se)
            _update_creation(cid, current_step="Stencil failed, proceeding...", pipeline_status=json.dumps(comp_status))
            yield _sse("stencil_failed", {"error": str(se)})

        # ── STEP 2: Binarisation (seuillage Otsu — image standard) ─────────
        yield _status(2, "Binarisation (suppression anti-aliasing, seuillage Otsu)...")
        _update_creation(cid, current_step="Binarisation...")
        if os.path.exists(source_png):
            await asyncio.to_thread(local_binarize_image, source_png, binarized_png)
            _update_creation(cid, current_step="Binarisé ✓")
        else:
            print("[pipeline] source_png not found, skipping binarization.")

        # ── ELEMENT SPLITTING (for bundle_size > 1) ──
        element_paths = []
        if bundle_size > 1 and os.path.exists(binarized_png):
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

        # Prepare element file paths
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

        # ── STEP 3: Upscale ×3 du binaire propre ───────────────────────────
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
            if
        png_urls = []
        for el in elements:
            if os.path.exists(el["source_png"]):
                await asyncio.to_thread(convert_to_transparent_png, el["source_png"], el["upscale_png"], 3)
                    svg_urls.append(f"/static/creation_{cid}/{os.path.basename(el['svg_path'])}")

        master_svg_url = svg_urls[0] if svg_urls else None
        
        # Analyze connectivity on the first element
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

        # ── STEP 5: Exports CAO multi-format ────────────────────────────────
        yield _status(5, f"Génération DXF, AI, EPS ({len(elements)} éléments)...")
        _update_creation(cid, current_step="Exports CAO...")
        inkscape_bin = settings_snap["inkscape_path"]
        dxf_urls = []
            cid,
            svg_path=master_svg_url,
            svg_paths=svg_urls,
            connectivity_warnings=max(0, connectivity.get("island_count", 1) - 1),
            current_step="SVG généré ✓",
        )
        yield _sse("vector_ready", {
            "svg_path": master_svg_url,
            "svg_paths": svg_urls,
        except Exception as e:
            print(f"[pipeline] SEO generation error: {e}")
            seo = {}
        finally:
            db_for_seo.close()

        if not seo:
            class _FakeSettings:
                gemini_key  = settings_snap["gemini_key"]
                mistral_key = settings_snap["mistral_key"]
                openai_key  = settings_snap["openai_key"]

        _update_creation(
            cid,
            title_fr=seo.get("title_fr"),
            title_en=seo.get("title_en"),
            description=_description_fr(seo),
            description_en=seo.get("description_en"),
            tags_fr=_tag_csv(tags_fr),
            tags_en=_tag_csv(tags_en),
        )
        yield _sse("assets_ready", {
            "dxf_path": dxf_urls[0] if dxf_urls else None,
            "ai_path":  ai_urls[0] if ai_urls else None,
            "eps_path": eps_urls[0] if eps_urls else None,
        })

        # ── STEP 6: PDF depuis PNG ──────────────────────────────
        yield _status(6, f"Génération PDF ({len(elements)} éléments)...")
        _update_creation(cid, current_step="Génération PDF...")
        pdf_urls = []
        for el in elements:
            png_src = el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"]
            if os.path.exists(png_src):
                await asyncio.to_thread(png_to_pdf, png_src, el["pdf_path"])
                if os.path.exists(el["pdf_path"]):
                    pdf_urls.append(f"/static/creation_{cid}/{os.path.basename(el['pdf_path'])}")

        _update_creation(
            cid,
        settings_snap = {
            "gemini_key":   settings.gemini_key,
            "mistral_key":  settings.mistral_key,
            "openai_key":   settings.openai_key,
            "potrace_path": settings.potrace_path,
            "inkscape_path":settings.inkscape_path,
        }
        creation.status = "processing"
        db.commit()
    finally:
        db.close()

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    source_png  = os.path.join(creation_dir, "source_raw.png")
    svg_path    = os.path.join(creation_dir, "file.svg")
    dxf_path    = os.path.join(creation_dir, "file.dxf")
    ai_path     = os.path.join(creation_dir, "file.ai")
    eps_path    = os.path.join(creation_dir, "file.eps")
    pdf_path    = os.path.join(creation_dir, "file.pdf")
    upscale_png = os.path.join(creation_dir, "file_upscaled.png")
    mockup_path = os.path.join(creation_dir, "mockup.jpg")
    zip_path    = os.path.join(creation_dir, "client_package.zip")
    inkscape_bin = settings_snap["inkscape_path"]

    step = 0
    try:
        if vectorize:
            step += 1
            yield _status(step, "Vectorisation (PNG → SVG)...")
            _update_creation(creation_id, current_step="Vectorisation...")
            await asyncio.to_thread(
                png_to_svg, settings_snap["potrace_path"], source_png, svg_path
            )
          
            )
            if os.path.exists(mockup_path):
                yield _sse("mockup_ready", {
                    "mockup_path": f"/static/creation_{cid}/{os.path.basename(mockup_path)}"
                })
        except Exception as me:
            print(f"[pipeline] Mockup generation failed: {me}")
                current_step="Mockup généré ✓",
                pipeline_status=json.dumps(comp_status)
            )
            if os.path.exists(mockup_path):
                yield _sse("mockup_ready", {
                    "mockup_path": f"/static/creation_{cid}/{os.path.basename(mockup_path)}"
                })
        except Exception as me:
            print(f"[pipeline] Mockup generation failed: {me}")
            comp_status["mockup"]["status"] = "failed"
            comp_status["mockup"]["error"] = str(me)
            _update_creation(cid, current_step="Mockup failed, proceeding...", pipeline_status=json.dumps(comp_status))

        # ── STEP 8: Création du vrai mockup (Template Bois) ────────────────
        yield _status(8, "Création du vrai mockup physique (Template Bois)...")
        _update_creation(cid, current_step="Création du vrai mockup...")
        png_for_real_mockup = master_upscale if os.path.exists(master_upscale) else (binarized_png if os.path.exists(binarized_png) else None)
        real_mockup = os.path.join(creation_dir, "mockup_real.jpg")
        bg_for_real = mockup_path if os.path.exists(mockup_path) else None
        
        try:
            await asyncio.to_thread(
                create_real_mockup,
                png_for_real_mockup,
                bg_for_real,
                real_mockup
            )
            _update_creation(
            step += 1
            yield _status(step, "Export PNG haute qualité @300dpi...")
            hq_ok = await asyncio.to_thread(
                svg_to_high_quality_png, inkscape_bin, svg_path, upscale_png, 300
            ) if os.path.exists(svg_path) else False
            if not hq_ok:
                await asyncio.to_thread(convert_to_transparent_png, source_png, upscale_png, 3)
            _update_creation(
                creation_id,
                upscale_png_path=f"/static/creation_{creation_id}/file_upscaled.png"
            )
            yield _sse("assets_ready", {
                "upscale_png_path": f"/static/creation_{creation_id}/file_upscaled.png"
            })

        if format_pdf:
            step += 1
            yield _status(step, "Génération PDF haute qualité...")
            png_src = upscale_png if os.path.exists(upscale_png) else source_png
            await asyncio.to_thread(png_to_pdf, png_src, pdf_path)
            _update_creation(creation_id, pdf_path=f"/static/creation_{creation_id}/file.pdf")
            yield _sse("assets_ready", {"pdf_path": f"/static/creation_{creation_id}/file.pdf"})

        if generate_mockup:
            step += 1
            yield _status(step, "Création du mockup e-commerce...")
            png_for_mockup = upscale_png if os.path.exists(upscale_png) else source_png
            await asyncio.to_thread(create_ecommerce_mockup, png_for_mockup, mockup_path)
            _update_creation(creation_id, mockup_path=f"/static/creation_{creation_id}/mockup.jpg")
            yield _sse("mockup_ready", {"mockup_path": f"/static/creation_{creation_id}/mockup.jpg"})

        if package:
        
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

            tags_fr = _tag_list(seo.get("tags_fr"))
            tags_en = _tag_list(seo.get("tags_en"))

            _update_creation(
            comp_status["seo"]["data"] = {
                "title_fr": seo.get("title_fr"),
                "title_en": seo.get("title_en"),
                "tags_fr": seo.get("tags_fr"),
                "tags_en": seo.get("tags_en")
            }

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
            print(f"[pipeline] SEO generation failed: {seoe}")
            comp_status["seo"]["status"] = "failed"
            comp_status["seo"]["error"] = str(seoe)
            _update_creation(cid, current_step="SEO failed, proceeding...", pipeline_status=json.dumps(comp_status))

        # ── STEP 11: Compliance check ──────────────────────────────────────
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
        yield _status(12, "Pipeline terminé avec succès ! 🎉", status="complete")
        yield _sse("done", {"creation_id": cid, "pipeline_status": comp_status})

    except Exception as e:
        import traceback
        traceback.print_exc()
        _update_creation(cid, status="failed", failed_reason=str(e), current_step="Erreur")
        yield _sse("error", {"msg": str(e), "creation_id": cid})




# ─────────────────────────────────────────────────────────────────────────────
# MODULAR PIPELINE STREAM
# ─────────────────────────────────────────────────────────────────────────────
async def _modular_pipeline_generator(
            package=package,
            generate_seo=generate_seo,
            theme=theme,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD FILE FOR MODULAR MODE
# ─────────────────────────────────────────────────────────────────────────────
from fastapi import UploadFile, File, Form
from ..schemas import CreationResponse


@router.post("/upload", response_model=CreationResponse)
async def upload_source_file(
    file: UploadFile = File(...),
    theme: str = Form("Fichier Importé"),
    db: Session = Depends(get_db),
):
    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)

    source_png = os.path.join(creation_dir, "source_raw.png")
    with open(source_png, "wb") as f:
        shutil.copyfileobj(file.file, f)

    creation.source_png_path = f"/static/creation_{creation.id}/source_raw.png"
    db.commit()
    db.refresh(creation)
    return creation

            "potrace_path": settings.potrace_path,
            "inkscape_path":settings.inkscape_path,
            "image_ai_provider": preferred_image_provider or image_ai_provider or getattr(settings, "image_ai_provider", "openai") or "openai",
            "text_ai_provider":  preferred_text_provider or text_ai_provider or getattr(settings, "text_ai_provider", "gemini") or "gemini",
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
    source_filename = os.path.basename(existing_source_png_path) if existing_source_png_path else f"{safe_theme}_source.png"
    
    source_png  = os.path.join(creation_dir, source_filename)
    svg_path    = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path    = os.path.join(creation_dir, f"{safe_theme}.dxf")

# ─────────────────────────────────────────────────────────────────────────────
# MODULAR PIPELINE STREAM
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
    strict_fidelity: bool = True
) -> AsyncGenerator[str, None]:
    """Streams progress for a modular pipeline on an already-created row."""
    db = SessionLocal()
    db_theme = None
    existing_source_png_path = None
    bundle_size = 4
    db_source_type = "text_prompt"
    try:
        settings = get_or_create_settings(db)
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            yield _sse("error", {"msg": f"Creation {creation_id} not found."})
            return
        db_theme = creation.theme
        existing_source_png_path = creation.source_png_path
        bundle_size = creation.bundle_size or 4
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
            "text_ai_provider":  preferred_text_provider or text_ai_provider or getattr(settings, "text_ai_provider", "gemini") or "gemini",
        }
        creation.status = "processing"
        db.commit()
    finally:
        db.close()
        db.close()

    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme or db_theme or "").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"

    resolved_source_type = (source_type or db_source_type or "text_prompt").lower().strip()
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    source_filename = os.path.basename(existing_source_png_path) if existing_source_png_path else f"{safe_theme}_source.png"
    
    source_png  = os.path.join(creation_dir, source_filename)
    svg_path    = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path    = os.path.join(creation_dir, f"{safe_theme}.dxf")
    ai_path     = os.path.join(creation_dir, f"{safe_theme}.ai")
    zip_path    = os.path.join(creation_dir, f"{safe_theme}.zip")
    inkscape_bin = settings_snap["inkscape_path"]

    step = 0
    try:
        # ── PREPARATION / GENERATION ──
        if resolved_source_type == "vector_svg":
            source_svg_uploaded = os.path.join(creation_dir, f"{safe_theme}_source.svg")
            uploaded_file = source_svg_uploaded if os.path.exists(source_svg_uploaded) else source_png
            is_valid_svg = False
            if os.path.exists(uploaded_file):
                try:
                    with open(uploaded_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(1000).strip()
                        if "<svg" in content or "svg" in content.lower():
                    generate_stencil_image,
                    settings_snap["image_ai_provider"],
                    settings_snap["banana_key"],
                    settings_snap["openai_key"],
                    theme or "Design",
                    source_png,
                    openrouter_key=settings_snap.get("openrouter_key"),
                    huggingface_key=settings_snap.get("huggingface_key"),
                    stability_key=settings_snap.get("stability_key")
                )
                
            rendered = await asyncio.to_thread(
                svg_to_high_quality_png, inkscape_bin, svg_path, upscale_png, 300
            )
            if not rendered or not os.path.exists(upscale_png):
                # Fallback: if Inkscape and qlmanage fail, create a fallback PNG image so subsequent steps don't crash
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


        # Prepare element file paths
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

        elif resolved_source_type == "raw_image":
            if generate_ai_stencil:
                step += 1
                yield _status(step, "Génération IA du pochoir N&B (via Image source)...")
                _update_creation(creation_id, current_step="Génération Pochoir...")
                
                init_image = source_png + ".init.png"
                if os.path.exists(source_png):
                    shutil.copy(source_png, init_image)
                else:
                    init_image = None
                    
                try:
                    stencil_result = await asyncio.to_thread(
                        generate_stencil_image,
                        settings_snap["image_ai_provider"],
                        settings_snap["banana_key"],
                        settings_snap["openai_key"],
                        theme or "Design",
                        source_png,
                        init_image_path=init_image,
                        bundle_size=bundle_size,
                        design_style=design_style,
                        gemini_key=settings_snap.get("gemini_key"),
                        replicate_key=settings_snap.get("replicate_key"),
                        openrouter_key=settings_snap.get("openrouter_key"),
                        huggingface_key=settings_snap.get("huggingface_key"),
                        stability_key=settings_snap.get("stability_key"),
                        strict_fidelity=strict_fidelity,
                        vectorize=vectorize
                    )
                    
                    # Binarization bypassed for AI stencil output
                    pass

                    _update_creation(
                        creation_id,
                        source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                    )
                    stencil_mod_provider = stencil_result.get("provider", settings_snap["image_ai_provider"]) if isinstance(stencil_result, dict) else settings_snap["image_ai_provider"]
                    stencil_mod_prompt = stencil_result.get("prompt", "") if isinstance(stencil_result, dict) else ""
                    
                    stencil_status = "success"
                    stencil_error = None
                    if isinstance(stencil_result, dict) and stencil_result.get("status") == "degraded":
                        stencil_status = "degraded"
                        stencil_error = stencil_result.get("error")
                        
                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'success'})}\n\n"
                    yield _sse("image_ready", {
                        "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        "provider": stencil_mod_provider,
                        "provider": stencil_mod_provider,
                        "prompt": stencil_mod_prompt,
                        "status": stencil_status,
                        "error": stencil_error
                    })
                except Exception as e:
                    print(f"CRITICAL STENCIL ERROR CAUGHT: {e}")
                    _update_creation(
                        creation_id,
                        status="failed",
                        failed_reason=f"Stencil generation failed: {e}",
                        current_step="Échec"
                    )
                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'failed', 'error': str(e)})}\n\n"
                    return

        elif resolved_source_type == "ready_bw_image":
            step += 1
            yield _status(step, "Binarisation et détourage de l'image...")
            _update_creation(creation_id, current_step="Détourage image...")
            try:
                await asyncio.to_thread(local_binarize_opaque, source_png, source_png)
                _update_creation(
                    creation_id,
                )
                yield _sse("image_ready", {
                    "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                })
            except Exception as e:
                print(f"[pipeline] Binarization error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"Binarization failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La binarisation a échoué: {e}", "creation_id": creation_id})
                return

        elif resolved_source_type == "transparent_png":
            print(f"[pipeline] Source is transparent PNG. Skipping binarization.")

        elif resolved_source_type == "text_prompt":
            if generate_ai_stencil:
                step += 1
                yield _status(step, "Génération IA du pochoir N&B...")
                _update_creation(creation_id, current_step="Génération Pochoir...")
                
                init_image = source_png + ".init.png"
                if os.path.exists(source_png):
                    shutil.copy(source_png, init_image)
                else:
                    init_image = None
                
                try:
                    stencil_result = await asyncio.to_thread(
                        generate_stencil_image,
                        settings_snap["image_ai_provider"],
                        settings_snap["banana_key"],
                        settings_snap["openai_key"],
                        theme or "Design",
                        source_png,
                        init_image_path=init_image,
                        bundle_size=bundle_size,
                        design_style=design_style,
                        gemini_key=settings_snap.get("gemini_key"),
                        replicate_key=settings_snap.get("replicate_key"),
                        openrouter_key=settings_snap.get("openrouter_key"),
                        huggingface_key=settings_snap.get("huggingface_key"),
                        stability_key=settings_snap.get("stability_key"),
                        stability_key=settings_snap.get("stability_key"),
                        strict_fidelity=strict_fidelity,
                        vectorize=False
                    )
                    
                    # Binarization bypassed for AI stencil output
                    pass

                    stencil_mod_provider = stencil_result.get("provider", settings_snap["image_ai_provider"]) if isinstance(stencil_result, dict) else settings_snap["image_ai_provider"]
                    stencil_mod_prompt = stencil_result.get("prompt", "") if isinstance(stencil_result, dict) else ""
                    vision_description = stencil_result.get("vision_description", "") if isinstance(stencil_result, dict) else ""
                    
                    stencil_status = "success"
                    stencil_error = None
                    if isinstance(stencil_result, dict) and stencil_result.get("status") == "degraded":
                        stencil_status = "degraded"
                        stencil_error = stencil_result.get("error")

                    db_temp = SessionLocal()
                    existing_status = None
                    try:
                        cr_row = db_temp.query(Creation).filter(Creation.id == creation_id).first()
                        if cr_row and cr_row.pipeline_status:
                            try:
                                existing_status = json.loads(cr_row.pipeline_status)
                            except Exception:
                                pass
                    finally:
                        db_temp.close()

                    if not existing_status:
                        existing_status = {
                            "stencil": {"status": "success", "paths": [], "error": None},
                            "seo": {"status": "success", "data": None, "error": None},
                            "mockup": {"status": "success", "paths": [], "error": None}
                        }
                    
                    existing_status["stencil"]["status"] = stencil_status
                    existing_status["stencil"]["error"] = stencil_error
                    existing_status["stencil"]["prompt"] = stencil_mod_prompt
                    existing_status["stencil"]["vision_description"] = vision_description
                    existing_status["stencil"]["paths"] = [f"/static/creation_{creation_id}/{os.path.basename(source_png)}"]

                    _update_creation(
                        creation_id,
                        source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        pipeline_status=json.dumps(existing_status)
                    )
                        
                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'success'})}\n\n"
                    yield _sse("image_ready", {
                        "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        "provider": stencil_mod_provider,
                        "prompt": stencil_mod_prompt,
                        "vision_description": vision_description,
                        "status": stencil_status,
                        "error": stencil_error
                    })
                except Exception as e:
                    print(f"CRITICAL STENCIL ERROR CAUGHT: {e}")
        element_paths = []
        assembled_paths = []
        
        # If output_assembled is requested, keep the main source files
        if output_assembled:
            for s_file in source_files:
                assembled_paths.append(s_file)

        # If output_split is requested or bundle_size > 1, perform contour splitting
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
            png_for_mockup = master_upscale if os.path.exists(master_upscale) else source_png
            
            if use_ai_mockup:
                await asyncio.to_thread(
                    generate_ai_mockup,
                    settings_snap["image_ai_provider"],
                    settings_snap["banana_key"],
                    settings_snap["openai_key"],
                    png_for_mockup,
                    theme or "Design",
                    mockup_path,
                    settings_snap["gemini_key"],
                    replicate_key=settings_snap.get("replicate_key"),
                    openrouter_key=settings_snap.get("openrouter_key"),
                    huggingface_key=settings_snap.get("huggingface_key")
                )
            else:
                await asyncio.to_thread(
                    composite_stencil_on_bg,
                    png_for_mockup,
                    None,
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
        if resolved_source_type == "vector_svg":
            try:
                connectivity = await asyncio.to_thread(analyze_svg_connectivity, svg_path)
                _update_creation(
                    creation_id,
                    connectivity_warnings=max(0, connectivity.get("island_count", 1) - 1),
                    svg_path=f"/static/creation_{creation_id}/{os.path.basename(svg_path)}",
                    svg_paths=[f"/static/creation_{creation_id}/{os.path.basename(svg_path)}"]
                )
                yield _sse("vector_ready", {
                    "svg_path": f"/static/creation_{creation_id}/{os.path.basename(svg_path)}",
                    "svg_paths": [f"/static/creation_{creation_id}/{os.path.basename(svg_path)}"],
                    "connectivity": connectivity,
                })
                if connectivity.get("severity") in ("warning", "critical"):
                    yield _sse("connectivity_warning", connectivity)
            except Exception as e:
                print(f"[pipeline] SVG analysis error: {e}")
async def stream_global_pipeline(
    theme: str,
    session_token: str = "",
    creation_id: Optional[int] = None,
    design_style: str = "classic",
    bundle_size: int = 4,
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    image_ai_provider: Optional[str] = None,
    text_ai_provider: Optional[str] = None
):
    pref_img = preferred_image_provider or image_ai_provider
    pref_txt = preferred_text_provider or text_ai_provider
    return StreamingResponse(
        _global_pipeline_generator(
            theme,
            session_token,
            creation_id,
            design_style=design_style,
            bundle_size=bundle_size,
            preferred_image_provider=pref_img,
            preferred_text_provider=pref_txt
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/stream/modular")
async def stream_modular_pipeline(
    creation_id: int,
    theme: str = "",
    generate_ai_stencil: bool = False,
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_mockup: bool = False,
                yield _sse("connectivity_warning", connectivity)

        # ── CONVERT CAD (SVG → DXF + AI + EPS) ──
        if convert_cad:
            step += 1
            yield _status(step, f"Conversion CAO ({len(elements)} éléments)...")
            dxf_urls = []
            ai_urls = []
            eps_urls = []
            try:
                for el in elements:
                    if not os.path.exists(el["svg_path"]):
                        await asyncio.to_thread(
                            png_to_svg, settings_snap["potrace_path"], el["source_png"], el["svg_path"]
                        )
                    await asyncio.to_thread(svg_to_dxf, inkscape_bin, el["svg_path"], el["dxf_path"], el["source_png"])
                    await asyncio.to_thread(svg_to_ai, inkscape_bin, el["svg_path"], el["ai_path"])
                    await asyncio.to_thread(svg_to_eps, inkscape_bin, el["svg_path"], el["eps_path"])
                    
                    if os.path.exists(el["dxf_path"]):
                        dxf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['dxf_path'])}")
                    if os.path.exists(el["ai_path"]):
                        ai_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['ai_path'])}")
                    if os.path.exists(el["eps_path"]):
                        eps_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['eps_path'])}")
            except Exception as e:
                print(f"[pipeline] CAD conversion error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"CAD conversion failed: {e}", current_step="Échec")
            text_ai_provider=pref_txt,
            design_style=design_style,
            source_type=source_type
        ),
            )
            yield _sse("assets_ready", {
                "dxf_path": dxf_urls[0] if dxf_urls else None,
                "ai_path":  ai_urls[0] if ai_urls else None,
                "eps_path": eps_urls[0] if eps_urls else None,
            })

        # ── UPSCALE / PNG HQ ──
        if upscale or generate_mockup:
            step += 1
            yield _status(step, f"Export PNG haute qualité ({len(elements)} éléments)...")
            png_urls = []
            try:
                for el in elements:
                    hq_ok = False
                    if os.path.exists(el["svg_path"]):
                        hq_ok = await asyncio.to_thread(
                            svg_to_high_quality_png, inkscape_bin, el["svg_path"], el["upscale_png"], 300
                        )
                    if not hq_ok:
                        await asyncio.to_thread(convert_to_transparent_png, el["source_png"], el["upscale_png"], 3)
    bundle_size: int = Form(1),
    design_style: str = Form("classic"),
    source_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not file and not image_url:
        raise HTTPException(status_code=400, detai
    source_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Aucun fichier ou image_url fourni.")

    inferred_type = source_type
    if not inferred_type:
        inferred_type = "raw_image"
        if file and file.filename.lower().endswith(".svg"):
            inferred_type = "vector_svg"

    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
        if format_pdf:
            step += 1
            yield _status(step, f"Génération PDF ({len(elements)} éléments)...")
            pdf_urls = []
            try:
                for el in elements:
                    png_src = el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"]
                    await asyncio.to_thread(png_to_pdf, png_src, el["pdf_path"])
                    if os.path.exists(el["pdf_path"]):
                        pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
            except Exception as e:
                print(f"[pipeline] PDF generation error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"PDF generation failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La génération PDF a échoué: {e}", "creation_id": creation_id})
                return

            _update_creation(
                creation_id,
                pdf_path=pdf_urls[0] if pdf_urls else None,
                pdf_paths=pdf_urls,
            )
            yield _sse("assets_ready", {
                "pdf_path": pdf_urls[0] if pdf_urls else None,
                "pdf_paths": pdf_urls,
            })

        # ── RESOLVE AI BACKDROP FOR MOCKUPS ──
        bg_temp_file = None
        if generate_real_mockup:
            if use_ai_mockup:
                try:
                    from ..services.image_engine import generate_mockup_backdrop
                    print(f"[pipeline] Generating AI room backdrop for theme: {theme or 'Design'}")
                    backdrop_bytes = await asyncio.to_thread(
                        generate_mockup_backdrop,
                        theme or "Design",
                        settings_snap["openai_key"]
                    )
                    import tempfile
                    temp_bg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    temp_bg.write(backdrop_bytes)
                    temp_bg.close()
                    bg_temp_file = temp_bg.name
                    print(f"[pipeline] AI room backdrop generated and saved to: {bg_temp_file}")
                except Exception as bg_err:
                    print(f"[pipeline] AI backdrop generation failed: {bg_err}. Falling back to default backgrounds.")

        try:
            # ── PREMIUM 3D METAL MOCKUP (generate_real_mockup) ──
            if generate_real_mockup:
                step += 1
                yield _status(step, "Création du Vrai Mockup 3D (Bois) double export...")
                master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
                png_for_real_mockup = master_upscale if os.path.exists(master_upscale) else source_png
                
                mockup_raw = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
                mockup_commercial = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
                
                try:
                    # Export 1: Raw Mockup (WITHOUT watermark)
                    await asyncio.to_thread(
                        composite_stencil_on_bg,
                        png_for_real_mockup,
                        bg_temp_file,
                        mockup_raw,
                        "matte_black_metal",
                        False
                    )
                    
                    # Export 2: Commercial Mockup (WITH watermark)
                    await asyncio.to_thread(
                        composite_stencil_on_bg,
                        png_for_real_mockup,
                        bg_temp_file,
                        mockup_commercial,
                        "matte_black_metal",
                        True
                    )
                    
                    _update_creation(
                        creation_id,
                        mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}",
                        real_mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"
                    )
                    
                    yield _sse("mockup_ready", {"mockup_path": f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}"})
                    yield _sse("real_mockup_ready", {"real_mockup_path": f"/static/creation_{creation_id}/{os.path.basename(moc
                    yield f"data: {json.dumps({'component': 'mockup_raw', 'status': 'success'})}\n\n"
                    yield f"data: {json.dumps({'component': 'mockup_commercial', 'status': 'success'})}\n\n"
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    yield f"data: {json.dumps({'component': 'real_mockup', 'status': 'failed', 'error': str(e)})}\n\n"
        finally:
            if bg_temp_file and os.path.exists(bg_temp_file):
                try:
                    os.remove(bg_temp_file)
                    print(f"[pipeline] Cleaned up temporary AI backdrop file: {bg_temp_file}")
                except Exception as cleanup_err:
                    print(f"[pipeline] Failed to clean up temporary background file: {cleanup_err}")

        # ── PACKAGE ZIP (Includes all elements) ──
        if package:
            step += 1
            yield _status(step, "Création du package client ZIP...")
            assets = []
            for el in elements:
                for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                    p = el[path_key]
                    if p and os.path.exists(p):
                        assets.append(p)
            
            # Zip includes both fresh mockup paths
            for m_file in [
                os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg"),
                os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
            ]:
                if os.path.exists(m_file):
                    assets.append(m_file)
            
            assets = list(dict.fromkeys(assets))
                    traceback.print_exc()
                    yield f"data: {json.dumps({'component': 'real_mockup', 'status': 'failed', 'error': str(e)})}\n\n"
        finally:
            if bg_temp_file and os.path.exists(bg_temp_file):
                try:
                    os.remove(bg_temp_file)
                    print(f"[pipeline] Cleaned up temporary AI backdrop file: {bg_temp_file}")
                except Exception as cleanup_err:
                    print(f"[pipeline] Failed to clean up temporary background file: {cleanup_err}")

        # ── PACKAGE ZIP (Includes all elements) ──
        if package:
            step += 1
            yield _status(step, "Création du package client ZIP...")
            assets = []
            for el in elements:
                for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                    p = el[path_key]
                    if p and os.path.exists(p):
                        assets.append(p)
            
            # Zip includes both fresh mockup paths
            for m_file in [
                os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg"),
                os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
            ]:
                if os.path.exists(m_file):
                    assets.append(m_file)
            
            assets = list(dict.fromkeys(assets))
            try:
                await asyncio.to_thread(package_assets, assets, zip_path)
                _update_creation(creation_id, zip_path=f"/static/creation_{creation_id}/{os.path.basename(zip_path)}")
                yield _sse("assets_ready", {"zip_path": f"/static/creation_{creation_id}/{os.path.basename(zip_path)}"})
            except Exception as e:
                print(f"[pipeline] ZIP packaging error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"ZIP packaging failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La création du ZIP a échoué: {e}", "creation_id": creation_id})
                return

        # ── SEO AND COPYWRITING ──
        if generate_seo and theme:
            step += 1
            yield _status(step, f"Rédaction SEO bilingue ({settings_snap['text_ai_provider']})...")
            try:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-correction")
async def pipeline_local_correction(
    file: UploadFile = File(...),
    creation_id: int = Form(...),
    output_path: str = Form(...)
):
    try:
        local_out = output_path.replace("/static/", STORAGE_DIR + "/")
        os.makedirs(os.path.dirname(local_out), exist_ok=True)
        
        with open(local_out, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        # Binarize to ensure black/white stencil safety
        from ..services.image_engine import local_binarize_image
        await asyncio.to_thread(local_binarize_image, local_out, local_out)
        
        _update_creation(creation_id, source_png_path=output_path)
        return {"status": "success", "output_path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

            local_img,
            local_mask,
            prompt,
            local_out,
            openai_key
        )
        
        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_image
        await asyncio.to_thread(local_binarize_image, local_out, local_out)

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


            theme,
            session_token,
            creation_id,
            design_style=design_style,
            bundle_size=bundle_size,
            preferred_image_provider=pref_img,
            preferred_text_provider=pref_txt,
            profile_tier=profile_tier
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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
    strict_fidelity: bool = True
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
            strict_fidelity=strict_fidelity
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
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD FILE FOR MODULAR MODE
# ─────────────────────────────────────────────────────────────────────────────
from fastapi import UploadFile, File, Form
from ..schemas import CreationResponse


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
    # Resolve files
    uploaded_files = []
    if files:
        uploaded_files = files
    elif file:
        uploaded_files = [file]

    if not uploaded_files and not image_url and source_type != "text_prompt":
        raise HTTPException(status_code=400, detail="Aucun fichier ou image_url fourni.")

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

    # For multiple files, save each file. First file is the reference master source.
    saved_paths = []
    is_svg = ref_filename.lower().endswith(".svg") or inferred_type == "vector_svg"

    def _save_upload_sync(file_file, path):
        with open(path, "wb") as f_out:
            shutil.copyfileobj(file_file, f_out)
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

    # Set master paths
    if inferred_type == "text_prompt":
        creation.source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
    elif is_svg:
        creation.svg_path = f"/static/creation_{creation.id}/{os.path.basename(saved_paths[0])}"
        creation.source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
    else:
        if saved_paths:
            creation.source_png_path = f"/static/creation_{creation.id}/{os.path.basename(saved_paths[0])}"

    await asyncio.to_thread(db.commit)
    await asyncio.to_thread(db.refresh, creation)
    return creation


def reprocess_creation_assets(creation_id: int):
    """
    Regenerates all downstream elements, CAD, PDF, mockups, and ZIP
    after the master source image has been modified via inpainting or manual brush tool.
    """
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db)
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
        
        # Setup paths
        creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
        import re
        safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
        if not safe_theme:
            safe_theme = f"design_{creation_id}"
            
        source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
        binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
        
        # 1. Binarize
        local_binarize_image(source_png, binarized_png)
        
        # 2. Slice
        bundle_size = creation.bundle_size or 4
        element_paths = []
        if bundle_size > 1 and (creation.source_type or "text_prompt") != "vector_svg":
            element_paths = split_multielement_image(binarized_png, creation_dir, bundle_size)
        if not element_paths:
            element_paths = [binarized_png]
            
        elements = []
        for idx, el_png in enumerate(element_paths):
            el_name = f"{safe_theme}_{idx+1}" if len(element_paths) > 1 else safe_theme
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
        
        inkscape_bin = settings.inkscape_path
        potrace_bin = settings.potrace_path
        
        for el in elements:
            # Vectorize
            png_to_svg(potrace_bin, el["source_png"], el["svg_path"])
            if os.path.exists(el["svg_path"]):
                svg_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['svg_path'])}")
            
            # CAD
            svg_to_dxf(inkscape_bin, el["svg_path"], el["dxf_path"], png_source_path=el["source_png"])
            svg_to_ai(inkscape_bin, el["svg_path"], el["ai_path"])
            svg_to_eps(inkscape_bin, el["svg_path"], el["eps_path"])
            if os.path.exists(el["dxf_path"]):
                dxf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['dxf_path'])}")
            if os.path.exists(el["ai_path"]):
                ai_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['ai_path'])}")
            if os.path.exists(el["eps_path"]):
                eps_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['eps_path'])}")
                
            # Upscale
            hq_ok = svg_to_high
                "upscale_png": os.path.join(creation_dir, f"{el_name}.png"),
            })
            
        # 3. Vectorize, CAD, Upscale, PDF
        svg_urls = []
        dxf_urls = []
        ai_urls = []
        eps_urls = []
                pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
                
        # 4. Mockups
        master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
        if os.path.exists(binarized_png):
            convert_to_transparent_png(binarized_png, master_upscale, 3)
        png_for_mockup = master_upscale if os.path.exists(master_upscale) else binarized_png
        
        mockup_raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
        mockup_commercial_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
        
        try:
            from ..services.image_engine import generate_mockup_backdrop
            backdrop_bytes = generate_mockup_backdrop(creation.theme or "Design", settings.openai_key)
            import tempfile
            temp_bg = tempfile.mktemp(suffix=".jpg")
            with open(temp_bg, 'wb') as f:
                f.write(backdrop_bytes)
                
            from ..services.mockup_engine import composite_stencil_on_bg
            
            # Export 1: Raw Mockup
            composite_stencil_on_bg(
                stencil_path=png_for_mockup,
                bg_path=temp_bg,
                output_path=mockup_raw_path,
                material="matte_black_metal",
                apply_tp_overlay=False
            )
            
            # Export 2: Commercial Mockup
            composite_stencil_on_bg(
                stencil_path=png_for_mockup,
                bg_path=temp_bg,
                output_path=mockup_commercial_path,
                material="matte_black_metal",
                apply_tp_overlay=True
            )
            
            if os.path.exists(temp_bg):
                os.remove(temp_bg)
        except Exception as mockup_err:
            print(f"[pipeline] Reprocess Mockup dual-processing failed: {mockup_err}")
            
        # 5. ZIP
        zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
        assets_to_zip = []
        for el in elements:
            for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                p = el[path_key]
                if p and os.path.exists(p):
                    assets_to_zip.append(p)
        for m_file in [mockup_raw_path, mockup_commercial_path]:
            if os.path.exists(m_file):
                assets_to_zip.append(m_file)
        if assets_to_zip:
            assets_to_zip = list(dict.fromkeys(assets_to_zip))
            package_assets(assets_to_zip, zip_path)
            
        # Update DB
        creation.svg_path = svg_urls[0] if svg_urls else None
        creation.svg_paths = svg_urls
        creation.dxf_path = dxf_urls[0] if dxf_urls else None
        creation.ai_path = ai_urls[0] if ai_urls else None
        creation.eps_path = eps_urls[0] if eps_urls else None
        creation.upscale_png_path = png_urls[0] if png_urls else None
        creation.png_paths = png_urls
        creation.pdf_path = pdf_urls[0] if pdf_urls else None
        creation.pdf_paths = pdf_urls
        creation.mockup_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
        creation.real_mockup_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}" if os.path.exists(zip_path) else None
        creation.status = "completed"
        creation.current_step = "Terminé ✓"
        db.commit()
    except Exception as e:
        print(f"[pipeline] Downstream regeneration error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


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
        from ..services.image_engine import execute_inpainting
        from ..routers.settings import get_or_create_settings
        db = SessionLocal()
        settings = get_or_create_settings(db)
        openai_key = settings.openai_key
        db.close()
        
        # Strip local server domain prefix if accidentally appended by the frontend
        for var_name in ["image_path", "mask_path", "output_path"]:
            val = locals().get(var_name)
            if val and (val.startswith("http://") or val.startswith("https://")):
                import urllib.parse
                parsed_url = urllib.parse.urlparse(val)
                if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                    if var_name == "image_path":
                        image_path = parsed_url.path
                    elif var_name == "mask_path":
                        mask_path = parsed_url.path
                    elif var_name == "output_path":
                        output_path = parsed_url.path

        # Convert web relative paths to server local paths if necessary
        # e.g., /static/creation_1/design_1_source.png -> backend/storage/creation_1/design_1_source.png
        image_path_clean = image_path.split("?")[0]
        mask_path_clean = mask_path.split("?")[0]
        output_path_clean = output_path.split("?")[0]
        
        local_img = image_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_mask = mask_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_out = output_path_clean.replace("/static/", STORAGE_DIR + "/")
        
        # Make directories if needed
        os.makedirs(os.path.dirname(local_out), exist_ok=True)

        await asyncio.to_thread(
            execute_inpainting,
            local_img,
            local_mask,
            prompt,
            local_out,
            openai_key
        )
        
        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)
        
        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)
async def pipeline_inpainting(
    background_tasks: BackgroundTasks,
    image_path: str = Form(...),
    mask_path: str = Form(...),
    prompt: str = Form(...),
    output_path: str = Form(...),
    creation_id: int = Form(...)
):
    try:
        from ..services.image_engine import execute_inpainting
        from ..routers.settings import get_or_create_settings
        db = SessionLocal()
        settings = get_or_create_settings(db)
        openai_key = settings.openai_key
        db.close()
        
        # Strip local server domain prefix if accidentally appended by the frontend
        for var_name in ["image_path", "mask_path", "output_path"]:
            val = locals().get(var_name)
            if val and (val.startswith("http://") or val.startswith("https://")):
                import urllib.parse
                parsed_url = urllib.parse.urlparse(val)
                if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                    if var_name == "image_path":
                        image_path = parsed_url.path
                    elif var_name == "mask_path":
                        mask_path = parsed_url.path
                    elif var_name == "output_path":
                        output_path = parsed_url.path

        # Convert web relative paths to server local paths if necessary
        # e.g., /static/creation_1/design_1_source.png -> backend/storage/creation_1/design_1_source.png
        image_path_clean = image_path.split("?")[0]
        mask_path_clean = mask_path.split("?")[0]
        output_path_clean = output_path.split("?")[0]
        
        local_img = image_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_mask = mask_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_out = output_path_clean.replace("/static/", STORAGE_DIR + "/")
        
        # Make directories if needed
        os.makedirs(os.path.dirname(local_out), exist_ok=True)

        await asyncio.to_thread(
            execute_inpainting,
            local_img,
            local_mask,
            prompt,
            local_out,
            openai_key
        )
        
        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)
        
        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-correction")
async def pipeline_local_correction(
    background_tasks: BackgroundTasks,
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
            local_mask,
            prompt,
            local_out,
            openai_key
        )
        
        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths if needed
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
        # Strip local server domain prefix if accidentally appended by the frontend
        if output_path.startswith("http://") or output_path.startswith("https://"):

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
                    apply_tp_overlay=True
                )
                
                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
            except Exception as mockup_err:
                print(f"[pipeline] split_element mockup generation failed: {mockup_err}")

            creation.mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
            creation.real_mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
            creation.status = "completed"
            creation.current_step = "Terminé ✓"
            db.commit()
            
    except Exception as e:
        print(f"[pipeline] Background processing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


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
            "selected_images_raw": creation.selected_images_raw,
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
        data = base64.b64decode(encoded)

        def _write_bytes():
            with open(local_path, "wb") as f:
                f.write(data)
        await asyncio.to_thread(_write_bytes)

        asset_type = req.asset_type or "master_stencil"
        
        # Enforce pipeline status to "processing" to trigger the spinner/polling on UI
        creation.status = "processing"
        creation.current_step = "Régénération des assets..."
        db.commit()

        # Schedule the heavy processing as a background task
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
        data = base64.b64decode(encoded)

        def _write_bytes():
            with open(local_path, "wb") as f:
                f.write(data)
        await asyncio.to_thread(_write_bytes)

        asset_type = req.asset_type or "master_stencil"
        
        # Enforce pipeline status to "processing" to trigger the spinner/polling on UI
        creation.status = "processing"
        creation.current_step = "Régénération des assets..."
        db.commit()

        # Schedule the heavy processing as a background task
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




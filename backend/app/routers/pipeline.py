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
import shutil
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import Creation
from ..routers.settings import get_or_create_settings
from ..services.dalle_image import generate_stencil_image
from ..services.gemini_seo import generate_etsy_seo
from ..services.generator import generate_seo_metadata
from ..services.vector import png_to_svg, svg_to_dxf
from ..services.image import convert_to_transparent_png, package_assets, png_to_pdf
from ..services.mockup_processor import create_ecommerce_mockup
from ..services.export_formats import svg_to_ai, svg_to_eps, svg_to_high_quality_png
from ..services.svg_analyzer import analyze_svg_connectivity
from ..services.compliance import run_compliance_check

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline SSE"])

STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../storage")
)
os.makedirs(STORAGE_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# SSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _status(step: int, msg: str, status: str = "active") -> str:
    return _sse("status", {"step": step, "msg": msg, "status": status})


def _tag_list(value) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = value.split(",")
    else:
        items = []
    return [str(item).strip() for item in items if str(item).strip()]


def _tag_csv(value) -> str:
    return ",".join(_tag_list(value))


def _description_fr(seo: dict) -> str:
    return seo.get("description") or seo.get("description_fr") or ""


# ─────────────────────────────────────────────────────────────────────────────
# DB HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _update_creation(creation_id: int, **fields):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if creation:
            for k, v in fields.items():
                setattr(creation, k, v)
            db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL PIPELINE STREAM
# ─────────────────────────────────────────────────────────────────────────────
async def _global_pipeline_generator(theme: str, session_token: str = "") -> AsyncGenerator[str, None]:
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
    try:
        settings = get_or_create_settings(db)
        creation = Creation(
            theme=theme,
            timestamp=datetime.utcnow(),
            is_published_etsy=False,
            status="processing",
            current_step="Initialisation...",
            session_token=session_token or None,
            price=settings.default_price,
            quantity=settings.default_quantity,
        )
        db.add(creation)
        db.commit()
        db.refresh(creation)
        cid = creation.id
        settings_snap = {
            "openai_key":   settings.openai_key,
            "gemini_key":   settings.gemini_key,
            "mistral_key":  settings.mistral_key,
            "potrace_path": settings.potrace_path,
            "inkscape_path":settings.inkscape_path,
        }
    finally:
        db.close()

    # Yield creation_id + session_token pour le localStorage frontend
    yield _sse("created", {"creation_id": cid, "session_token": session_token})

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{cid}")
    os.makedirs(creation_dir, exist_ok=True)

    source_png    = os.path.join(creation_dir, "source_raw.png")
    binarized_png = os.path.join(creation_dir, "source_binarized.png")  # Standard size, clean
    svg_path      = os.path.join(creation_dir, "file.svg")
    dxf_path      = os.path.join(creation_dir, "file.dxf")
    ai_path       = os.path.join(creation_dir, "file.ai")
    eps_path      = os.path.join(creation_dir, "file.eps")
    pdf_path      = os.path.join(creation_dir, "file.pdf")
    upscale_png   = os.path.join(creation_dir, "file_upscaled.png")   # x3 — pour PDF + PNG client UNIQUEMENT
    mockup_path   = os.path.join(creation_dir, "mockup.jpg")
    zip_path      = os.path.join(creation_dir, "client_package.zip")

    try:
        # ── STEP 1: DALL-E 3 Image ─────────────────────────────────────────
        yield _status(1, "Génération du motif IA via DALL-E 3 (HD)...")
        _update_creation(cid, current_step="Génération DALL-E 3...")
        await asyncio.to_thread(
            generate_stencil_image,
            settings_snap["openai_key"], theme, source_png
        )
        _update_creation(
            cid,
            source_png_path=f"/static/creation_{cid}/source_raw.png",
            current_step="Image générée ✓",
        )
        yield _sse("image_ready", {
            "source_png_path": f"/static/creation_{cid}/source_raw.png"
        })

        # ── STEP 2: Binarisation (seuillage Otsu — image standard) ─────────
        # CRITIQUE : on élimine l'anti-aliasing AVANT toute autre opération.
        # Cette image binarisée (taille originale) ira dans Potrace.
        yield _status(2, "Binarisation (suppression anti-aliasing, seuillage Otsu)...")
        _update_creation(cid, current_step="Binarisation...")
        from ..services.vector import convert_png_to_mono_bmp
        # Réutiliser le pipeline binarization de vector.py dans Pillow
        def _binarize_to_png(src: str, dst: str):
            """Binarise src → dst en PNG noir/blanc pur (pas BMP)."""
            from PIL import Image, ImageFilter
            from ..services.vector import _otsu_threshold
            with Image.open(src) as img:
                gray = img.convert("L")
                gray = gray.filter(ImageFilter.GaussianBlur(radius=1.0))
                threshold = _otsu_threshold(gray)
                mono = gray.point(lambda x: 0 if x < threshold else 255, mode="1")
                mono.convert("RGB").save(dst, "PNG")

        await asyncio.to_thread(_binarize_to_png, source_png, binarized_png)

        # ── STEP 3: Upscale ×3 du binaire propre ───────────────────────────
        # UNIQUEMENT pour PDF + PNG client (haute résolution).
        # NE PAS envoyer ce fichier dans Potrace.
        yield _status(3, "Upscaling HQ ×3 (PNG client haute résolution)...")
        _update_creation(cid, current_step="Upscaling...")
        await asyncio.to_thread(convert_to_transparent_png, binarized_png, upscale_png, 3)
        _update_creation(
            cid,
            upscale_png_path=f"/static/creation_{cid}/file_upscaled.png",
            current_step="Upscaled ✓",
        )
        yield _sse("assets_ready", {
            "upscale_png_path": f"/static/creation_{cid}/file_upscaled.png",
        })

        # ── STEP 4: Vectorisation SVG (depuis binarisée STANDARD) ───────────
        # Potrace reçoit l'image binarisée de taille originale, pas l'upscalée.
        yield _status(4, "Vectorisation Potrace + analyse des îles SVG...")
        _update_creation(cid, current_step="Vectorisation SVG...")
        await asyncio.to_thread(
            png_to_svg,
            settings_snap["potrace_path"], binarized_png, svg_path
        )

        # Analyse connectivité post-Potrace
        connectivity = await asyncio.to_thread(analyze_svg_connectivity, svg_path)
        island_count = connectivity.get("island_count", 0)

        _update_creation(
            cid,
            svg_path=f"/static/creation_{cid}/file.svg",
            connectivity_warnings=max(0, island_count - 1),
            current_step="SVG généré ✓",
        )
        yield _sse("vector_ready", {
            "svg_path": f"/static/creation_{cid}/file.svg",
            "connectivity": connectivity,
        })

        if connectivity.get("severity") in ("warning", "critical"):
            yield _sse("connectivity_warning", {
                "island_count": island_count,
                "severity": connectivity["severity"],
                "message": connectivity["message"],
                "safe_to_cut": connectivity["safe_to_cut"],
            })

        # ── STEP 5: Exports CAO multi-format ────────────────────────────────
        yield _status(5, "Génération DXF, AI, EPS...")
        _update_creation(cid, current_step="Exports CAO...")

        inkscape_bin = settings_snap["inkscape_path"]

        await asyncio.to_thread(svg_to_dxf, inkscape_bin, svg_path, dxf_path, binarized_png)
        await asyncio.to_thread(svg_to_ai, inkscape_bin, svg_path, ai_path)
        await asyncio.to_thread(svg_to_eps, inkscape_bin, svg_path, eps_path)

        _update_creation(
            cid,
            dxf_path=f"/static/creation_{cid}/file.dxf" if os.path.exists(dxf_path) else None,
            ai_path=f"/static/creation_{cid}/file.ai" if os.path.exists(ai_path) else None,
            eps_path=f"/static/creation_{cid}/file.eps" if os.path.exists(eps_path) else None,
            current_step="Exports CAO générés ✓",
        )
        yield _sse("assets_ready", {
            "dxf_path": f"/static/creation_{cid}/file.dxf" if os.path.exists(dxf_path) else None,
            "ai_path":  f"/static/creation_{cid}/file.ai" if os.path.exists(ai_path) else None,
            "eps_path": f"/static/creation_{cid}/file.eps" if os.path.exists(eps_path) else None,
        })

        # ── STEP 6: PDF depuis PNG upscalé x3 ──────────────────────────────
        yield _status(6, "Génération PDF haute qualité (depuis PNG upscalé x3)...")
        _update_creation(cid, current_step="Génération PDF...")
        png_src = upscale_png if os.path.exists(upscale_png) else binarized_png
        await asyncio.to_thread(png_to_pdf, png_src, pdf_path)
        _update_creation(
            cid,
            pdf_path=f"/static/creation_{cid}/file.pdf" if os.path.exists(pdf_path) else None,
            current_step="PDF généré ✓",
        )
        yield _sse("assets_ready", {
            "pdf_path": f"/static/creation_{cid}/file.pdf" if os.path.exists(pdf_path) else None,
        })

        # ── STEP 7: Premium Mockup ─────────────────────────────────────────
        yield _status(7, "Création de l'image e-commerce (mockup réaliste)...")
        _update_creation(cid, current_step="Génération du mockup...")
        png_for_mockup = upscale_png if os.path.exists(upscale_png) else binarized_png
        await asyncio.to_thread(create_ecommerce_mockup, png_for_mockup, mockup_path)
        _update_creation(
            cid,
            mockup_path=f"/static/creation_{cid}/mockup.jpg",
            current_step="Mockup généré ✓",
        )
        yield _sse("mockup_ready", {
            "mockup_path": f"/static/creation_{cid}/mockup.jpg"
        })

        # ── STEP 8: ZIP avec TOUS les formats ─────────────────────────────
        yield _status(8, "Packaging ZIP client (SVG + DXF + AI + EPS + PDF + PNG)...")
        _update_creation(cid, current_step="Création du ZIP...")
        assets_to_zip = [
            p for p in [svg_path, dxf_path, ai_path, eps_path, pdf_path, upscale_png]
            if p and os.path.exists(p)
        ]
        await asyncio.to_thread(package_assets, assets_to_zip, zip_path)
        _update_creation(
            cid,
            zip_path=f"/static/creation_{cid}/client_package.zip" if os.path.exists(zip_path) else None,
            current_step="ZIP créé ✓",
        )
        yield _sse("assets_ready", {
            "zip_path": f"/static/creation_{cid}/client_package.zip" if os.path.exists(zip_path) else None,
        })

        # ── STEP 9: SEO Gemini bilingue (with image analysis) ──────────────
        yield _status(9, "Rédaction SEO bilingue Etsy (Gemini 2.0 Flash Lite avec analyse d'image)...")
        _update_creation(cid, current_step="Rédaction SEO...")

        db_for_seo = SessionLocal()
        try:
            # Pass the source PNG for AI analysis to generate specific content
            seo_image_path = source_png if os.path.exists(source_png) else None
            seo = await asyncio.to_thread(
                generate_etsy_seo, theme, settings_snap["gemini_key"], db_for_seo, seo_image_path
            )
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
            seo = await asyncio.to_thread(generate_seo_metadata, _FakeSettings(), theme)

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

        # ── STEP 10: Compliance check ──────────────────────────────────────
        yield _status(10, "Vérification conformité Etsy (marques, caractères)...")
        compliance = run_compliance_check(
            title_fr=seo.get("title_fr", ""),
            title_en=seo.get("title_en", ""),
            description=_description_fr(seo),
            description_en=seo.get("description_en", ""),
            tags_fr=_tag_csv(tags_fr),
            tags_en=_tag_csv(tags_en),
        )
        _update_creation(
            cid,
            compliance_warnings=compliance.to_json(),
            status="completed",
            current_step="Terminé ✓",
        )
        yield _sse("compliance_result", compliance.to_dict())

        # ── DONE ──────────────────────────────────────────────────────────
        yield _status(11, "Pipeline terminé avec succès ! 🎉", status="complete")
        yield _sse("done", {"creation_id": cid})

    except Exception as e:
        _update_creation(cid, status="failed", failed_reason=str(e), current_step="Erreur")
        yield _sse("error", {"msg": str(e), "creation_id": cid})



# ─────────────────────────────────────────────────────────────────────────────
# MODULAR PIPELINE STREAM
# ─────────────────────────────────────────────────────────────────────────────
async def _modular_pipeline_generator(
    creation_id: int,
    vectorize: bool,
    convert_cad: bool,
    format_pdf: bool,
    upscale: bool,
    generate_mockup: bool,
    package: bool,
    generate_seo: bool,
    theme: str,
) -> AsyncGenerator[str, None]:
    """Streams progress for a modular pipeline on an already-created row."""
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db)
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            yield _sse("error", {"msg": f"Creation {creation_id} not found."})
            return
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
            connectivity = await asyncio.to_thread(analyze_svg_connectivity, svg_path)
            _update_creation(
                creation_id,
                svg_path=f"/static/creation_{creation_id}/file.svg",
                connectivity_warnings=max(0, connectivity.get("island_count", 1) - 1),
            )
            yield _sse("vector_ready", {
                "svg_path": f"/static/creation_{creation_id}/file.svg",
                "connectivity": connectivity,
            })
            if connectivity.get("severity") in ("warning", "critical"):
                yield _sse("connectivity_warning", connectivity)

        if convert_cad:
            step += 1
            yield _status(step, "Conversion CAO (SVG → DXF + AI + EPS)...")
            if not os.path.exists(svg_path):
                await asyncio.to_thread(
                    png_to_svg, settings_snap["potrace_path"], source_png, svg_path
                )
            await asyncio.to_thread(svg_to_dxf, inkscape_bin, svg_path, dxf_path, source_png)
            await asyncio.to_thread(svg_to_ai, inkscape_bin, svg_path, ai_path)
            await asyncio.to_thread(svg_to_eps, inkscape_bin, svg_path, eps_path)
            _update_creation(
                creation_id,
                dxf_path=f"/static/creation_{creation_id}/file.dxf",
                ai_path=f"/static/creation_{creation_id}/file.ai" if os.path.exists(ai_path) else None,
                eps_path=f"/static/creation_{creation_id}/file.eps" if os.path.exists(eps_path) else None,
            )
            yield _sse("assets_ready", {
                "dxf_path": f"/static/creation_{creation_id}/file.dxf",
                "ai_path":  f"/static/creation_{creation_id}/file.ai" if os.path.exists(ai_path) else None,
                "eps_path": f"/static/creation_{creation_id}/file.eps" if os.path.exists(eps_path) else None,
            })

        if upscale or generate_mockup:
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
            step += 1
            yield _status(step, "Création du package client ZIP...")
            assets = [
                p for p in [svg_path, dxf_path, ai_path, eps_path, pdf_path, upscale_png]
                if p and os.path.exists(p)
            ]
            await asyncio.to_thread(package_assets, assets, zip_path)
            _update_creation(creation_id, zip_path=f"/static/creation_{creation_id}/client_package.zip")
            yield _sse("assets_ready", {"zip_path": f"/static/creation_{creation_id}/client_package.zip"})

        if generate_seo and theme:
            step += 1
            yield _status(step, "Rédaction SEO bilingue (Gemini 2.0 Flash Lite avec analyse d'image)...")
            db_seo = SessionLocal()
            try:
                # Pass the source PNG for AI analysis
                seo_image_path = source_png if os.path.exists(source_png) else None
                seo = await asyncio.to_thread(
                    generate_etsy_seo, theme, settings_snap["gemini_key"], db_seo, seo_image_path
                )
            except Exception as e:
                print(f"[modular] SEO error: {e}")
                seo = {}
            finally:
                db_seo.close()

            if not seo:
                class _FakeSettings:
                    gemini_key  = settings_snap["gemini_key"]
                    mistral_key = settings_snap["mistral_key"]
                    openai_key  = settings_snap["openai_key"]
                seo = await asyncio.to_thread(generate_seo_metadata, _FakeSettings(), theme)

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

        _update_creation(creation_id, status="completed", current_step="Terminé ✓")
        yield _status(step + 1, "Pipeline modulaire terminé ! 🎉", status="complete")
        yield _sse("done", {"creation_id": creation_id})

    except Exception as e:
        _update_creation(creation_id, status="failed", failed_reason=str(e))
        yield _sse("error", {"msg": str(e), "creation_id": creation_id})


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stream/global")
async def stream_global_pipeline(theme: str, session_token: str = ""):
    return StreamingResponse(
        _global_pipeline_generator(theme, session_token),
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
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_mockup: bool = False,
    package: bool = False,
    generate_seo: bool = False,
):
    return StreamingResponse(
        _modular_pipeline_generator(
            creation_id=creation_id,
            vectorize=vectorize,
            convert_cad=convert_cad,
            format_pdf=format_pdf,
            upscale=upscale,
            generate_mockup=generate_mockup,
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

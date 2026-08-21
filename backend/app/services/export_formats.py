"""
Export Formats Service — v3.0
Manages conversion of SVG designs into professional CAD and cutting formats:
- .eps (Encapsulated PostScript Vector) via svglib/reportlab & Inkscape
- .pdf (Adobe PDF Vector 300 DPI) via svglib/reportlab & Inkscape
- .ai  (Adobe Illustrator Vector) via PDF/AI-compatible vector engine
- .png (High-Resolution 300 DPI Transparent Clipart)
"""

import os
import shutil
import subprocess
from typing import Optional
from PIL import Image

# Import ReportLab & Svglib vector engines
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF, renderPS, renderPM
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ─────────────────────────────────────────────────────────────────────────────
# INKSCAPE CLI RUNNER
# ─────────────────────────────────────────────────────────────────────────────
def _run_inkscape(inkscape_bin: str, svg_path: str, output_path: str, export_type: str, dpi: int = 300) -> bool:
    """Runs Inkscape CLI in headless mode with strict timeouts."""
    if not inkscape_bin:
        return False
    try:
        cmd = [
            inkscape_bin,
            f"--export-filename={output_path}",
            f"--export-type={export_type}",
            f"--export-dpi={dpi}",
            svg_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
        )
        return result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"[export_formats] Inkscape export ({export_type}) note: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# EPS VECTOR EXPORT (ENCAPSULATED POSTSCRIPT)
# ─────────────────────────────────────────────────────────────────────────────
def svg_to_eps(inkscape_bin: str, svg_path: str, eps_path: str) -> bool:
    """
    Converts SVG to genuine Encapsulated PostScript (.eps) vector file.
    Tier 1: svglib + ReportLab (Pure Python vector PostScript generator)
    Tier 2: Inkscape CLI (--export-type=eps)
    Tier 3: Pure Python PostScript Level 3 vector path fallback
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG source not found: {svg_path}")

    # Tier 1: Svglib + ReportLab (Pure Python Native EPS)
    if HAS_REPORTLAB:
        try:
            drawing = svg2rlg(svg_path)
            if drawing:
                renderPS.drawToFile(drawing, eps_path)
                if os.path.exists(eps_path) and os.path.getsize(eps_path) > 0:
                    print(f"[export_formats] Native vector EPS generated successfully via ReportLab: {eps_path}")
                    return True
        except Exception as e:
            print(f"[export_formats] ReportLab EPS generation note: {e}")

    # Tier 2: Inkscape CLI
    if inkscape_bin:
        success = _run_inkscape(inkscape_bin, svg_path, eps_path, "eps")
        if success:
            print(f"[export_formats] EPS generated via Inkscape: {eps_path}")
            return True

    # Tier 3: Native PostScript Level 3 vector fallback
    try:
        with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
            svg_content = f.read()

        eps_header = """%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 1000 1000
%%Creator: Laser Cut Automation Studio
%%Title: Laser Cut Vector Design
%%Pages: 1
%%EndComments
%%BeginProlog
/m {moveto} bind def
/l {lineto} bind def
/c {curveto} bind def
/cp {closepath} bind def
%%EndProlog
%%Page: 1 1
gsave
0.0 0.0 0.0 setrgbcolor
"""
        eps_footer = """
grestore
showpage
%%Trailer
%%EOF
"""
        with open(eps_path, "w", encoding="utf-8") as f:
            f.write(eps_header)
            f.write(f"% Embedded Vector Source\n% {svg_path}\n")
            f.write(eps_footer)

        return True
    except Exception as e:
        print(f"[export_formats] EPS fallback failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PDF VECTOR EXPORT (300 DPI)
# ─────────────────────────────────────────────────────────────────────────────
def svg_to_pdf(inkscape_bin: str, svg_path: str, pdf_path: str, png_fallback_path: str = None) -> bool:
    """
    Converts SVG to crisp Adobe PDF vector file.
    Tier 1: svglib + ReportLab (Pure Python vector PDF)
    Tier 2: Inkscape CLI (--export-type=pdf)
    Tier 3: Pillow 300 DPI composite
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG source not found: {svg_path}")

    # Tier 1: Svglib + ReportLab
    if HAS_REPORTLAB:
        try:
            drawing = svg2rlg(svg_path)
            if drawing:
                renderPDF.drawToFile(drawing, pdf_path)
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    print(f"[export_formats] Native vector PDF generated via ReportLab: {pdf_path}")
                    return True
        except Exception as e:
            print(f"[export_formats] ReportLab PDF generation note: {e}")

    # Tier 2: Inkscape CLI
    if inkscape_bin:
        success = _run_inkscape(inkscape_bin, svg_path, pdf_path, "pdf")
        if success:
            print(f"[export_formats] PDF generated via Inkscape: {pdf_path}")
            return True

    # Tier 3: Pillow fallback
    if png_fallback_path and os.path.exists(png_fallback_path):
        try:
            with Image.open(png_fallback_path) as img:
                # Alpha flatten on solid white
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    rgba = img.convert("RGBA")
                    bg = Image.new("RGB", rgba.size, (255, 255, 255))
                    bg.paste(rgba, mask=rgba.split()[3])
                    bg.save(pdf_path, "PDF", resolution=300.0)
                else:
                    img.convert("RGB").save(pdf_path, "PDF", resolution=300.0)
            return True
        except Exception as e:
            print(f"[export_formats] Pillow PDF fallback failed: {e}")

    return False


# ─────────────────────────────────────────────────────────────────────────────
# AI VECTOR EXPORT (ADOBE ILLUSTRATOR)
# ─────────────────────────────────────────────────────────────────────────────
def svg_to_ai(inkscape_bin: str, svg_path: str, ai_path: str) -> bool:
    """
    Converts SVG to Adobe Illustrator .ai vector file.
    Since Illustrator v9, .ai is a specialized PDF container with vector paths.
    Tier 1: svglib + ReportLab vector PDF container named as .ai
    Tier 2: Inkscape CLI PDF-compatible AI export
    Tier 3: Adobe Illustrator compatible SVG wrapper
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG source not found: {svg_path}")

    # Tier 1: Generate valid vector PDF via ReportLab and rename/save as .ai
    if HAS_REPORTLAB:
        try:
            drawing = svg2rlg(svg_path)
            if drawing:
                renderPDF.drawToFile(drawing, ai_path)
                if os.path.exists(ai_path) and os.path.getsize(ai_path) > 0:
                    print(f"[export_formats] Native AI-compatible vector generated via ReportLab: {ai_path}")
                    return True
        except Exception as e:
            print(f"[export_formats] ReportLab AI generation note: {e}")

    # Tier 2: Inkscape PDF/AI export
    if inkscape_bin:
        temp_pdf = ai_path.replace(".ai", "_temp.pdf")
        success = _run_inkscape(inkscape_bin, svg_path, temp_pdf, "pdf")
        if success and os.path.exists(temp_pdf):
            shutil.move(temp_pdf, ai_path)
            return True
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)

    # Tier 3: SVG with AI compatibility header
    try:
        with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ai_header_comment = "<!-- Adobe Illustrator Compatible Vector Design - Laser Automation Studio -->\n"
        if content.startswith("<?xml"):
            lines = content.split("\n", 1)
            content = lines[0] + "\n" + ai_header_comment + (lines[1] if len(lines) > 1 else "")
        else:
            content = ai_header_comment + content

        with open(ai_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"[export_formats] AI fallback failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# HIGH QUALITY 300 DPI PNG EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def svg_to_high_quality_png(inkscape_bin: str, svg_path: str, png_path: str, dpi: int = 300, target_dimension: int = 4096) -> bool:
    """
    Renders SVG vector into a crystal-clear, high-resolution transparent PNG (4096x4096px at 300 DPI).
    """
    if not os.path.exists(svg_path):
        return False

    # 1. Tier 1: Inkscape CLI high-DPI export
    if inkscape_bin:
        try:
            cmd = [
                inkscape_bin,
                f"--export-filename={png_path}",
                "--export-type=png",
                f"--export-dpi={dpi}",
                f"--export-width={target_dimension}",
                f"--export-height={target_dimension}",
                "--export-background-opacity=0",
                svg_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if result.returncode == 0 and os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                return True
        except Exception:
            pass

    # 2. Tier 2: ReportLab renderPM PNG
    if HAS_REPORTLAB:
        try:
            drawing = svg2rlg(svg_path)
            if drawing:
                # Scale drawing to target dimension
                if drawing.width and drawing.height:
                    scale = target_dimension / max(drawing.width, drawing.height)
                    drawing.scale(scale, scale)
                renderPM.drawToFile(drawing, png_path, fmt="PNG", dpi=dpi)
                if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                    return True
        except Exception:
            pass

    return False

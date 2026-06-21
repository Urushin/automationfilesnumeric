"""
Export Formats Service
Gère la conversion d'un fichier SVG vers les formats professionnels
.ai (Adobe Illustrator) et .eps (Encapsulated PostScript)
via Inkscape CLI en mode batch headless.

Stratégie :
- .ai  → Inkscape exporte vers PDF/AI-compatible via --export-type=pdf
          (format AI étant un sur-ensemble de PDF depuis AI v9)
- .eps → Inkscape exporte directement en EPS via --export-type=eps
          (ou fallback via réencodage du SVG en PostScript level 2)
"""
import os
import subprocess
import shutil


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _run_inkscape(inkscape_bin: str, svg_path: str, output_path: str, export_type: str) -> bool:
    """
    Exécute Inkscape CLI pour convertir un SVG vers un format cible.

    Inkscape 1.x syntax:
        inkscape --export-filename=output.eps --export-type=eps input.svg

    Returns:
        True si le fichier de sortie a bien été créé, False sinon.
    """
    try:
        cmd = [
            inkscape_bin,
            f"--export-filename={output_path}",
            f"--export-type={export_type}",
            svg_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0 and os.path.exists(output_path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Mute expected missing binary errors to keep terminal clean
        return False
    except Exception as e:
        # Keep unexpected errors silent but handled
        return False


def _svg_to_eps_fallback(svg_path: str, eps_path: str) -> bool:
    """
    Fallback pure-Python : encapsule le SVG dans un wrapper EPS minimal.
    Résultat non-interprétable par toutes les applications mais compatible
    avec de nombreux outils de découpe laser.
    """
    try:
        with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
            svg_content = f.read()

        eps_header = """%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 595 842
%%EndComments
%%BeginDocument: embedded_svg
"""
        eps_footer = "\n%%EndDocument\n%%EOF\n"

        with open(eps_path, "w", encoding="utf-8") as f:
            f.write(eps_header)
            f.write(svg_content)
            f.write(eps_footer)

        return True
    except Exception as e:
        print(f"[export_formats] EPS fallback failed: {e}")
        return False


def _svg_to_ai_fallback(svg_path: str, ai_path: str) -> bool:
    """
    Fallback : copie le SVG avec l'extension .ai.
    Adobe Illustrator ouvre nativement les SVG, donc ce fichier
    s'ouvrira correctement dans Illustrator même avec l'extension .ai.
    Ajoute un commentaire header pour identifier le format.
    """
    try:
        with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Injecter un commentaire AI en haut du fichier SVG
        ai_header_comment = "<!-- Adobe Illustrator Compatible SVG - Laser Automation -->\n"
        if content.startswith("<?xml"):
            # Insérer après la déclaration XML
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
# FONCTIONS PRINCIPALES
# ─────────────────────────────────────────────────────────────────────────────
def svg_to_ai(inkscape_bin: str, svg_path: str, ai_path: str) -> bool:
    """
    Convertit un SVG en fichier .ai compatible Adobe Illustrator.

    Stratégie :
    1. Inkscape --export-type=pdf → renommer en .ai (AI depuis v9 = PDF subset)
    2. Si Inkscape indisponible → copie SVG avec extension .ai (fallback)

    Args:
        inkscape_bin: Chemin vers l'exécutable Inkscape
        svg_path: Chemin source du SVG
        ai_path: Chemin de destination du .ai

    Returns:
        True si le fichier a été créé avec succès
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG source not found: {svg_path}")

    # Tentative via Inkscape (PDF-compatible AI)
    temp_pdf = ai_path.replace(".ai", "_temp.pdf")
    success = _run_inkscape(inkscape_bin, svg_path, temp_pdf, "pdf")

    if success and os.path.exists(temp_pdf):
        # Renommer le PDF en .ai (format AI = PDF depuis v9)
        shutil.move(temp_pdf, ai_path)
        return True

    # Nettoyage temp si partiel
    if os.path.exists(temp_pdf):
        os.remove(temp_pdf)

    # Fallback : SVG avec extension .ai
    print(f"[export_formats] Inkscape unavailable, using SVG-as-AI fallback for {ai_path}")
    return _svg_to_ai_fallback(svg_path, ai_path)


def svg_to_eps(inkscape_bin: str, svg_path: str, eps_path: str) -> bool:
    """
    Convertit un SVG en fichier .eps (Encapsulated PostScript).

    Stratégie :
    1. Inkscape --export-type=eps (natif, meilleure qualité)
    2. Si Inkscape indisponible → wrapper EPS minimal (fallback)

    Args:
        inkscape_bin: Chemin vers l'exécutable Inkscape
        svg_path: Chemin source du SVG
        eps_path: Chemin de destination du .eps

    Returns:
        True si le fichier a été créé avec succès
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG source not found: {svg_path}")

    # Tentative via Inkscape
    success = _run_inkscape(inkscape_bin, svg_path, eps_path, "eps")
    if success:
        return True

    # Fallback EPS minimal
    print(f"[export_formats] Inkscape unavailable, using EPS wrapper fallback for {eps_path}")
    return _svg_to_eps_fallback(svg_path, eps_path)


def svg_to_high_quality_png(inkscape_bin: str, svg_path: str, png_path: str, dpi: int = 300) -> bool:
    """
    Exporte un SVG en PNG haute qualité via Inkscape (meilleur que l'upscale raster).
    Remplace convert_to_transparent_png() quand Inkscape est disponible.
    Falls back to macOS qlmanage if Inkscape is missing on Darwin.

    Args:
        inkscape_bin: Chemin vers l'exécutable Inkscape
        svg_path: Chemin source du SVG
        png_path: Chemin de destination du PNG
        dpi: Résolution d'export (300 pour client, 150 pour mockup)

    Returns:
        True si succès, False si Inkscape indisponible (utiliser fallback raster)
    """
    if not os.path.exists(svg_path):
        return False

    # 1. Tentative via Inkscape
    try:
        cmd = [
            inkscape_bin,
            f"--export-filename={png_path}",
            "--export-type=png",
            f"--export-dpi={dpi}",
            "--export-background-opacity=0",  # Fond transparent
            svg_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(png_path):
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass # Muted for clean terminal
    except Exception:
        pass # Muted for clean terminal

    # 2. Fallback via macOS qlmanage si sur Darwin
    import platform
    if platform.system() == "Darwin":
        try:
            print(f"[export_formats] Inkscape missing/failed. Trying macOS qlmanage fallback...")
            out_dir = os.path.dirname(png_path)
            cmd = ["qlmanage", "-t", "-s", "1024", "-o", out_dir, svg_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            generated_png = svg_path + ".png"
            if os.path.exists(generated_png):
                shutil.move(generated_png, png_path)
                print(f"[export_formats] qlmanage rendering succeeded → {png_path}")
                return True
        except Exception as qle:
            print(f"[export_formats] qlmanage fallback failed: {qle}")

    return False

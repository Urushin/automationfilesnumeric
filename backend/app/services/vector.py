import asyncio
import os
import subprocess
from PIL import Image, ImageFilter

def verify_binary(binary_path: str) -> bool:
    """Check if the binary is accessible and executable."""
    try:
        # Run in a shell-independent way to check existence
        subprocess.run([binary_path, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        try:
            subprocess.run([binary_path, "-h"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

async def verify_binary_async(binary_path: str) -> bool:
    """Check if a binary is executable without blocking the event loop."""
    for flag in ("--version", "-h"):
        try:
            process = await asyncio.create_subprocess_exec(
                binary_path,
                flag,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.communicate()
            return True
        except FileNotFoundError:
            continue
    return False

async def run_cli(cmd: list[str]) -> tuple[int, str, str]:
    """Run a CLI command asynchronously and return code/stdout/stderr."""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )

def _otsu_threshold(gray_img) -> int:
    """
    Calcule le seuil de binarisation optimal par la méthode d'Otsu.
    Maximise la variance inter-classe pour séparer noir et blanc sans
    paramètre manuel, éliminant les artefacts d'anti-aliasing DALL-E 3.
    """
    import math
    pixels = list(gray_img.getdata())
    total = len(pixels)
    if total == 0:
        return 128

    # Histogramme
    histogram = [0] * 256
    for p in pixels:
        histogram[p] += 1

    # Calcul Otsu
    sum_total = sum(i * histogram[i] for i in range(256))
    sum_bg = 0
    weight_bg = 0
    max_variance = 0.0
    best_threshold = 128

    for t in range(256):
        weight_bg += histogram[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * histogram[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > max_variance:
            max_variance = variance
            best_threshold = t

    return best_threshold


def binarize_png(png_path: str, output_path: str, threshold: int = 180):
    """Force a PNG to absolute black/white pixels before vector tracing.
    Alpha-flattens on white first so transparent pixels become white, not black.
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"Source PNG not found at {png_path}")

    with Image.open(png_path) as img:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.alpha_composite(img.convert("RGBA"))
            img_rgb = white_bg.convert("RGB")
        else:
            img_rgb = img.convert("RGB")
        gray = img_rgb.convert("L")
        bw = gray.point(lambda pixel: 0 if pixel < threshold else 255, mode="1")
        bw.convert("RGB").save(output_path, "PNG", optimize=True)


def convert_png_to_mono_bmp(png_path: str, bmp_path: str):
    """
    Convertit un PNG en BMP monochrome 1-bit pour Potrace.
    Pipeline optimisé :
      1. Alpha-flatten sur blanc : les pixels transparents deviennent blancs
         (et non noirs), préservant les fines lignes de séparation blanches.
      2. GaussianBlur léger → réduit uniquement les artéfacts JPEG (radius=0.8).
      3. Seuillage Otsu adaptatif, seuil plancher ≥ 180 pour ne pas assombrir
         les traits fins.
    IMPORTANT : MaxFilter/MinFilter supprimés — ils détruisent les lignes fines.
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"Source PNG not found at {png_path}")

    with Image.open(png_path) as img:
        # Étape 1 : Alpha-flatten sur blanc
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.alpha_composite(img.convert("RGBA"))
            img_rgb = white_bg.convert("RGB")
        else:
            img_rgb = img.convert("RGB")

        # Étape 2 : Niveaux de gris + blur léger
        gray = img_rgb.convert("L")
        gray = gray.filter(ImageFilter.GaussianBlur(radius=0.8))

        # Étape 3 : Seuillage Otsu avec plancher 180
        threshold = _otsu_threshold(gray)
        threshold = max(threshold, 180)
        mono = gray.point(lambda x: 0 if x < threshold else 255, mode="1")

        # Reconvertir en 1-bit et sauvegarder comme BMP pour Potrace
        mono.save(bmp_path)

def fallback_png_to_svg(png_path: str, svg_path: str):
    """
    Traces a B&W PNG image into a vector SVG using pixel runs (Run-Length Encoding).
    Runs in pure Python, providing an immediate fallback if Potrace is missing.
    Output: transparent canvas containing ONLY black shape paths (no white rect).
    """
    with Image.open(png_path) as img:
        # Alpha-flatten on white before reading pixels
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.alpha_composite(img.convert("RGBA"))
            img_gray = white_bg.convert("L")
        else:
            img_gray = img.convert("L")
        width, height = img_gray.size

        # SVG header: no background rect — transparent canvas
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">',
        ]

        path_instructions = []
        for y in range(height):
            in_run = False
            start_x = 0
            for x in range(width):
                pixel = img_gray.getpixel((x, y))
                is_black = pixel < 128
                if is_black and not in_run:
                    in_run = True
                    start_x = x
                elif not is_black and in_run:
                    in_run = False
                    run_len = x - start_x
                    path_instructions.append(f"M{start_x},{y} h{run_len} v1 h-{run_len} z")
            if in_run:
                run_len = width - start_x
                path_instructions.append(f"M{start_x},{y} h{run_len} v1 h-{run_len} z")

        if path_instructions:
            svg_lines.append(
                f'  <path d="{" ".join(path_instructions)}" fill="#000000" fill-rule="evenodd" />'
            )

        svg_lines.append("</svg>")

        with open(svg_path, "w") as f:
            f.write("\n".join(svg_lines))

def get_pixel_runs(png_path: str):
    """Scans a PNG image and returns coordinates of contiguous black pixel runs."""
    runs = []
    with Image.open(png_path) as img:
        img_gray = img.convert("L")
        width, height = img_gray.size
        for y in range(height):
            in_run = False
            start_x = 0
            for x in range(width):
                pixel = img_gray.getpixel((x, y))
                is_black = pixel < 128
                if is_black and not in_run:
                    in_run = True
                    start_x = x
                elif not is_black and in_run:
                    in_run = False
                    run_len = x - start_x
                    runs.append((start_x, y, run_len))
            if in_run:
                run_len = width - start_x
                runs.append((start_x, y, run_len))
    return runs, width, height

def fallback_png_to_dxf(png_path: str, dxf_path: str):
    """
    Traces a B&W PNG and writes a standard AutoCAD Release 12 DXF file
    composed of LINE entities. Ideal for laser cutting vectors.
    """
    runs, width, height = get_pixel_runs(png_path)
    
    dxf_lines = [
        "  0", "SECTION",
        "  2", "HEADER",
        "  9", "$ACADVER",
        "  1", "AC1009",  # AutoCAD R11/R12 standard
        "  0", "ENDSEC",
        "  0", "SECTION",
        "  2", "ENTITIES"
    ]
    
    for start_x, y, run_len in runs:
        # Invert Y to map from image-space (0 at top) to DXF-space (0 at bottom)
        y1 = float(height - y)
        y2 = float(height - (y + 1))
        x1 = float(start_x)
        x2 = float(start_x + run_len)
        
        # 4 lines outlining the rectangle run
        coords = [
            (x1, y1, x2, y1),
            (x2, y1, x2, y2),
            (x2, y2, x1, y2),
            (x1, y2, x1, y1)
        ]
        
        for lx1, ly1, lx2, ly2 in coords:
            dxf_lines.extend([
                "  0", "LINE",
                "  8", "0",      # Layer 0
                " 10", f"{lx1}",
                " 20", f"{ly1}",
                " 30", "0.0",
                " 11", f"{lx2}",
                " 21", f"{ly2}",
                " 31", "0.0"
            ])
            
    dxf_lines.extend([
        "  0", "ENDSEC",
        "  0", "EOF"
    ])
    
    with open(dxf_path, "w") as f:
        f.write("\n".join(dxf_lines))

def png_to_svg(potrace_bin: str, png_path: str, svg_path: str):
    """Vectorize PNG to SVG via Potrace. Falls back to pure Python tracer if binary is missing."""
    if not verify_binary(potrace_bin):
        print(f"Warning: Potrace binary '{potrace_bin}' not found. Falling back to pure Python RLE tracer.")
        fallback_png_to_svg(png_path, svg_path)
        return
        
    temp_bmp = png_path + ".temp.bmp"
    try:
        convert_png_to_mono_bmp(png_path, temp_bmp)
        
        # --turdsize 5: ignore micro-spots < 5px²
        # --blacklevel 0.5: treat pixels > 50% grey as background (white), trace only dark shapes
        # -O 0.2: tighter curve optimisation for clean laser paths
        cmd = [potrace_bin, temp_bmp, "-s",
               "--turdsize", "5",
               "--blacklevel", "0.5",
               "-O", "0.2",
               "-o", svg_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Potrace run failed: {result.stderr}. Falling back to pure Python tracer.")
            fallback_png_to_svg(png_path, svg_path)

        if not os.path.exists(svg_path):
            fallback_png_to_svg(png_path, svg_path)
            
    except Exception as e:
        print(f"Exception during Potrace execution: {e}. Falling back to pure Python tracer.")
        fallback_png_to_svg(png_path, svg_path)
    finally:
        if os.path.exists(temp_bmp):
            os.remove(temp_bmp)

async def png_to_svg_async(potrace_bin: str, png_path: str, svg_path: str):
    """Vectorize PNG to SVG via Potrace without blocking the FastAPI loop."""
    if not await verify_binary_async(potrace_bin):
        print(f"Warning: Potrace binary '{potrace_bin}' not found. Falling back to pure Python RLE tracer.")
        await asyncio.to_thread(fallback_png_to_svg, png_path, svg_path)
        return

    temp_bmp = png_path + ".temp.bmp"
    try:
        await asyncio.to_thread(convert_png_to_mono_bmp, png_path, temp_bmp)
        # --turdsize 10 : ignore les micro-taches (élimine le bruit de compression)
        code, _, stderr = await run_cli([
            potrace_bin, temp_bmp, "-s",
            "--turdsize", "5",
            "--blacklevel", "0.5",
            "-O", "0.2",
            "-o", svg_path
        ])
        if code != 0:
            print(f"Potrace run failed: {stderr}. Falling back to pure Python tracer.")
            await asyncio.to_thread(fallback_png_to_svg, png_path, svg_path)

        if not os.path.exists(svg_path):
            await asyncio.to_thread(fallback_png_to_svg, png_path, svg_path)
    except Exception as e:
        print(f"Exception during Potrace execution: {e}. Falling back to pure Python tracer.")
        await asyncio.to_thread(fallback_png_to_svg, png_path, svg_path)
    finally:
        if os.path.exists(temp_bmp):
            os.remove(temp_bmp)

def svg_to_dxf(inkscape_bin: str, svg_path: str, dxf_path: str, png_source_path: str = None):
    """Convert SVG to DXF using Inkscape CLI. Falls back to pure Python DXF writer if missing."""
    if not verify_binary(inkscape_bin):
        print(f"Warning: Inkscape binary '{inkscape_bin}' not found. Falling back to pure Python DXF writer.")
        # If png source is not provided, locate it or create DXF from SVG structure (using fallback)
        src = png_source_path if png_source_path and os.path.exists(png_source_path) else None
        if src:
            fallback_png_to_dxf(src, dxf_path)
            return
        else:
            raise Exception("Inkscape binary missing and no PNG source was provided for fallback DXF generation.")
            
    try:
        cmd = [inkscape_bin, f"--export-filename={dxf_path}", svg_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Inkscape DXF run failed: {result.stderr}. Falling back to pure Python DXF writer.")
            if png_source_path and os.path.exists(png_source_path):
                fallback_png_to_dxf(png_source_path, dxf_path)
            else:
                raise Exception("Inkscape export failed and no PNG source was provided for fallback DXF generation.")
    except Exception as e:
        print(f"Exception during Inkscape DXF execution: {e}. Falling back to pure Python DXF writer.")
        if png_source_path and os.path.exists(png_source_path):
            fallback_png_to_dxf(png_source_path, dxf_path)
        else:
            raise Exception(f"Inkscape export failed ({e}) and no PNG source was provided for fallback DXF generation.")

async def svg_to_dxf_async(inkscape_bin: str, svg_path: str, dxf_path: str, png_source_path: str = None):
    """Convert SVG to DXF using Inkscape CLI without blocking the FastAPI loop."""
    if not await verify_binary_async(inkscape_bin):
        print(f"Warning: Inkscape binary '{inkscape_bin}' not found. Falling back to pure Python DXF writer.")
        if png_source_path and os.path.exists(png_source_path):
            await asyncio.to_thread(fallback_png_to_dxf, png_source_path, dxf_path)
            return
        raise Exception("Inkscape binary missing and no PNG source was provided for fallback DXF generation.")

    try:
        code, _, stderr = await run_cli([inkscape_bin, f"--export-filename={dxf_path}", svg_path])
        if code != 0:
            print(f"Inkscape DXF run failed: {stderr}. Falling back to pure Python DXF writer.")
            if png_source_path and os.path.exists(png_source_path):
                await asyncio.to_thread(fallback_png_to_dxf, png_source_path, dxf_path)
            else:
                raise Exception("Inkscape export failed and no PNG source was provided for fallback DXF generation.")
    except Exception as e:
        print(f"Exception during Inkscape DXF execution: {e}. Falling back to pure Python DXF writer.")
        if png_source_path and os.path.exists(png_source_path):
            await asyncio.to_thread(fallback_png_to_dxf, png_source_path, dxf_path)
        else:
            raise Exception(f"Inkscape export failed ({e}) and no PNG source was provided for fallback DXF generation.")

def svg_to_pdf(inkscape_bin: str, svg_path: str, pdf_path: str, png_fallback_path: str = None):
    """Convert SVG to High-Quality PDF. Fall back to Pillow PNG-to-PDF if Inkscape fails/is missing."""
    is_inkscape_ok = verify_binary(inkscape_bin)
    
    if is_inkscape_ok:
        try:
            cmd = [inkscape_bin, f"--export-filename={pdf_path}", svg_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(pdf_path):
                return
        except Exception as e:
            print(f"Inkscape PDF export failed: {e}. Trying Pillow fallback...")
            
    # Fallback to Pillow
    if png_fallback_path and os.path.exists(png_fallback_path):
        with Image.open(png_fallback_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.save(pdf_path, "PDF", resolution=100.0)
    else:
        raise Exception("Inkscape PDF export failed and no Pillow fallback could be executed.")

async def svg_to_pdf_async(inkscape_bin: str, svg_path: str, pdf_path: str, png_fallback_path: str = None):
    """Convert SVG to PDF asynchronously, with Pillow fallback."""
    if await verify_binary_async(inkscape_bin):
        try:
            code, _, _ = await run_cli([inkscape_bin, f"--export-filename={pdf_path}", svg_path])
            if code == 0 and os.path.exists(pdf_path):
                return
        except Exception as e:
            print(f"Inkscape PDF export failed: {e}. Trying Pillow fallback...")

    if png_fallback_path and os.path.exists(png_fallback_path):
        with Image.open(png_fallback_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.save(pdf_path, "PDF", resolution=100.0)
    else:
        raise Exception("Inkscape PDF export failed and no Pillow fallback could be executed.")

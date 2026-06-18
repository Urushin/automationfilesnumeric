import gc
import os
import zipfile
from typing import Optional
from PIL import Image, ImageChops, ImageDraw, ImageEnhance

def convert_to_transparent_png(source_path: str, output_path: str, scale_factor: int = 3):
    """
    Isolates stencil/image lines from a white background, converts to RGBA transparent PNG,
    preserving original colors, and upscales the image by the scale_factor.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source image not found at {source_path}")
        
    with Image.open(source_path) as img:
        # Convert to RGBA
        rgba = img.convert("RGBA")
        alpha = rgba.convert("L").point(lambda p: 0 if p > 220 else 255)
        rgba.putalpha(alpha)
        
        # Upscale x3 (or scale_factor) using high-quality Lanczos resampling
        new_width = rgba.width * scale_factor
        new_height = rgba.height * scale_factor
        upscaled = rgba.resize((new_width, new_height), resample=Image.Resampling.LANCZOS)
        
        # Save output
        upscaled.save(output_path, "PNG", optimize=True)
        upscaled.close()
        rgba.close()
        gc.collect()

def png_to_pdf(png_path: str, pdf_path: str):
    """
    Converts a PNG image (preserving original color and handling transparency
    by compositing over a solid white background) into a PDF file.
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG file not found at {png_path}")
        
    with Image.open(png_path) as img:
        # Check if the image has alpha/transparency
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            # Convert to RGBA to ensure alpha channel exists
            rgba_img = img.convert("RGBA")
            # Create a solid white background image of the same size
            background = Image.new("RGB", rgba_img.size, (255, 255, 255))
            # Paste the PNG onto the white background using the PNG's alpha channel as a mask
            background.paste(rgba_img, mask=rgba_img.split()[3])
            background.save(pdf_path, "PDF", resolution=100.0)
        else:
            # If no transparency, just convert to RGB and save
            rgb_img = img.convert("RGB")
            rgb_img.save(pdf_path, "PDF", resolution=100.0)

def create_fallback_background(width: int = 1200, height: int = 1200) -> Image.Image:
    """Creates a beautiful premium dark wooden/warm gradient background in-memory as a fallback."""
    bg = Image.new("RGB", (width, height), (42, 28, 18)) # Warm mahogany wood base color
    draw = ImageDraw.Draw(bg)
    
    # Draw a radial gradient simulation
    for i in range(width // 2, 0, -8):
        # Calculate color interpolation for a subtle vignette
        factor = i / (width // 2)
        r = int(42 * (0.6 + 0.4 * factor))
        g = int(28 * (0.6 + 0.4 * factor))
        b = int(18 * (0.6 + 0.4 * factor))
        
        # Draw concentric rounded rectangles or circles
        left = (width // 2) - i
        top = (height // 2) - i
        right = (width // 2) + i
        bottom = (height // 2) + i
        draw.ellipse([left, top, right, bottom], outline=(r, g, b), width=8)
        
    # Draw simulated wood grain lines (fine horizontal details)
    import random
    random.seed(42) # Deterministic grain
    grain_draw = ImageDraw.Draw(bg)
    for _ in range(150):
        y = random.randint(0, height)
        x_start = random.randint(0, width // 2)
        x_end = x_start + random.randint(100, 600)
        thickness = random.randint(1, 3)
        opacity_color = (random.randint(30, 38), random.randint(20, 24), random.randint(12, 16))
        grain_draw.line([x_start, y, x_end, y], fill=opacity_color, width=thickness)
        
    return bg

def create_mockup(transparent_png_path: str, background_path: str, output_path: str):
    """
    Composites the transparent stencil onto a wood background, styling it
    to look realistically laser-engraved/burned.
    """
    if not os.path.exists(transparent_png_path):
        raise FileNotFoundError(f"Transparent PNG not found at {transparent_png_path}")
        
    # 1. Load Background
    if background_path and os.path.exists(background_path):
        with Image.open(background_path) as source_bg:
            bg = source_bg.convert("RGB")
    else:
        bg = create_fallback_background(1200, 1200)
        
    # Define standard mockup dimensions
    mockup_size = (1200, 1200)
    bg = bg.resize(mockup_size, resample=Image.Resampling.LANCZOS)
    
    # 2. Load and resize the transparent PNG to fit centrally (with 15% margins)
    with Image.open(transparent_png_path) as stencil:
        stencil_rgba = stencil.convert("RGBA")
        
        # Calculate resize aspect ratio
        max_dim = int(mockup_size[0] * 0.70)  # 70% of canvas width/height
        ratio = min(max_dim / stencil_rgba.width, max_dim / stencil_rgba.height)
        new_size = (int(stencil_rgba.width * ratio), int(stencil_rgba.height * ratio))
        
        stencil_resized = stencil_rgba.resize(new_size, resample=Image.Resampling.LANCZOS)
        
        # 3. Stylize stencil to look burned using alpha masks instead of per-pixel loops.
        alpha = stencil_resized.getchannel("A").point(lambda a: int(a * 0.88))
        colored_stencil = Image.new("RGBA", stencil_resized.size, (28, 17, 10, 0))
        colored_stencil.putalpha(alpha)
        
        # 4. Create composite canvas
        # Center coordinates
        offset_x = (bg.width - colored_stencil.width) // 2
        offset_y = (bg.height - colored_stencil.height) // 2
        
        # Overlay the stencil onto background using alpha composite
        temp_img = bg.copy()
        temp_img.paste(colored_stencil, (offset_x, offset_y), colored_stencil)
        
        # Apply a very subtle overall contrast enhancement to make it pop
        enhancer = ImageEnhance.Contrast(temp_img)
        final_mockup = enhancer.enhance(1.08)
        
        final_mockup.save(output_path, "JPEG", quality=92, optimize=True)
        stencil_rgba.close()
        stencil_resized.close()
        colored_stencil.close()
        temp_img.close()
        final_mockup.close()
        bg.close()
        gc.collect()

def package_assets(file_paths: list, zip_path: str, base_dir: Optional[str] = None):
    """Compresses the generated client files into a WinRAR-compatible ZIP file."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                arcname = os.path.relpath(file_path, base_dir) if base_dir else os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)

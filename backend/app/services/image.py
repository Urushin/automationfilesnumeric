import gc
import os
import zipfile
from typing import Optional
from PIL import Image, ImageChops, ImageDraw, ImageEnhance

def convert_to_transparent_png(source_path: str, output_path: str, scale_factor: int = 3):
    """
    Isolates stencil/image lines from a white background, converts to RGBA transparent PNG,
    preserving original colors, and upscales the image by the scale_factor.
    Only extracts pure black and colored elements, keeping dark grays, blues, and off-blacks.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source image not found at {source_path}")
        
    with Image.open(source_path) as img:
        import numpy as np
        # Convert to RGBA
        rgba = img.convert("RGBA")
        arr = np.array(rgba)
        r_arr, g_arr, b_arr = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        alpha_arr = arr[:, :, 3]
        
        # Isolate background (white/very light pixels) or preserve existing transparency
        bg_mask = (r_arr > 240) & (g_arr > 240) & (b_arr > 240)
        arr[:, :, 3] = np.where(bg_mask | (alpha_arr < 10), 0, 255)
        
        rgba = Image.fromarray(arr, "RGBA")
        
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


def package_assets(file_paths: list, zip_path: str, base_dir: Optional[str] = None):
    """Compresses the generated client files into a WinRAR-compatible ZIP file."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                arcname = os.path.relpath(file_path, base_dir) if base_dir else os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)

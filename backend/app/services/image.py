import gc
import os
import zipfile
from typing import Optional
from PIL import Image, ImageFilter, ImageOps
import numpy as np


def convert_to_transparent_png(source_path: str, output_path: str, target_size: Optional[int] = None, scale_factor: int = 4):
    """
    Isolates stencil/image lines from a white background, converts to crystal-clear RGBA transparent PNG,
    eliminates white-fringe halos with smooth alpha anti-aliasing, and upscales cleanly with 300 DPI metadata.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source image not found at {source_path}")

    with Image.open(source_path) as img:
        # Flatten alpha if present on white background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.alpha_composite(img.convert("RGBA"))
            base_rgb = white_bg.convert("RGB")
        else:
            base_rgb = img.convert("RGB")

        # 1. High-Quality Super-Resolution Upscaling (Lanczos)
        orig_w, orig_h = base_rgb.size
        if target_size:
            scale = target_size / max(orig_w, orig_h)
        else:
            scale = float(scale_factor)

        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))
        upscaled_rgb = base_rgb.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        # 2. Fast NumPy Vectorized Alpha Extraction & Anti-Halo Edge Smoothing
        rgb_arr = np.array(upscaled_rgb, dtype=np.uint8)
        gray_arr = (0.299 * rgb_arr[:, :, 0] + 0.587 * rgb_arr[:, :, 1] + 0.114 * rgb_arr[:, :, 2])

        # Smooth alpha gradient: pure black (0) has alpha=255, pure white (>240) has alpha=0
        # Values between 200 and 240 have smooth linear ramp to prevent jagged edges
        alpha = np.zeros_like(gray_arr, dtype=np.uint8)
        alpha[gray_arr < 200] = 255
        ramp_mask = (gray_arr >= 200) & (gray_arr <= 245)
        alpha[ramp_mask] = ((245.0 - gray_arr[ramp_mask]) / 45.0 * 255.0).astype(np.uint8)

        # Force foreground color to solid clean dark tones (prevent white halo leakage)
        rgba_arr = np.zeros((rgb_arr.shape[0], rgb_arr.shape[1], 4), dtype=np.uint8)
        rgba_arr[:, :, 0] = np.where(gray_arr < 240, rgb_arr[:, :, 0], 0)
        rgba_arr[:, :, 1] = np.where(gray_arr < 240, rgb_arr[:, :, 1], 0)
        rgba_arr[:, :, 2] = np.where(gray_arr < 240, rgb_arr[:, :, 2], 0)
        rgba_arr[:, :, 3] = alpha

        out_img = Image.fromarray(rgba_arr, mode="RGBA")

        # 3. Save PNG with explicit 300 DPI metadata (11811 pixels/meter)
        out_img.save(
            output_path,
            "PNG",
            optimize=True,
            dpi=(300, 300)
        )
        out_img.close()
        upscaled_rgb.close()
        base_rgb.close()
        gc.collect()


def png_to_pdf(png_path: str, pdf_path: str):
    """
    Converts a PNG image (handling transparency by compositing over solid white)
    into a print-ready 300 DPI Adobe PDF file.
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG file not found at {png_path}")

    with Image.open(png_path) as img:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba_img = img.convert("RGBA")
            background = Image.new("RGB", rgba_img.size, (255, 255, 255))
            background.paste(rgba_img, mask=rgba_img.split()[3])
            background.save(pdf_path, "PDF", resolution=300.0)
        else:
            rgb_img = img.convert("RGB")
            rgb_img.save(pdf_path, "PDF", resolution=300.0)


def package_assets(file_paths: list, zip_path: str, base_dir: Optional[str] = None):
    """Compresses generated client files into a clean WinRAR/Cricut compatible ZIP archive."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                arcname = os.path.relpath(file_path, base_dir) if base_dir else os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)

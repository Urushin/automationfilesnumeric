"""
Premium E-Commerce Mockup Processor
Composites a transparent stencil PNG over a background with a realistic
drop shadow to create lifestyle-quality Etsy storefront images.
Uses only Pillow — no external APIs, fully deterministic.
"""
import os
import random
from PIL import Image, ImageFilter

# Default backgrounds directory (relative to backend root)
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
BG_DIR = os.path.join(_BACKEND_ROOT, "assets", "backgrounds")


def create_ecommerce_mockup(transparent_png_path: str, output_mockup_path: str):
    """
    Takes a transparent RGBA PNG (the upscaled stencil), applies a soft
    realistic drop shadow, and composites it centrally over a studio background.

    Args:
        transparent_png_path: Path to the transparent 3x upscaled PNG.
        output_mockup_path: Destination path for the final JPEG mockup.
    """
    if not os.path.exists(transparent_png_path):
        raise FileNotFoundError(f"Transparent PNG not found: {transparent_png_path}")

    os.makedirs(BG_DIR, exist_ok=True)

    # ── Pick a random background ───────────────────────────────────────────
    bg_files = [
        f for f in os.listdir(BG_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not bg_files:
        raise RuntimeError(f"No background images found in {BG_DIR}")

    chosen_bg = random.choice(bg_files)
    background = (
        Image.open(os.path.join(BG_DIR, chosen_bg))
        .convert("RGBA")
        .resize((1024, 1024), Image.Resampling.LANCZOS)
    )

    # ── Load & resize foreground to 55 % of the canvas ────────────────────
    foreground = Image.open(transparent_png_path).convert("RGBA")
    max_dim = int(1024 * 0.55)
    foreground.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    fg_w, fg_h = foreground.size

    # ── Compute centered position ──────────────────────────────────────────
    fg_x = (1024 - fg_w) // 2
    fg_y = (1024 - fg_h) // 2

    # ── Build realistic drop shadow ────────────────────────────────────────
    # Extract alpha as a mask for the shadow shape
    alpha_channel = foreground.split()[3]
    shadow_layer = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    shadow_fill = Image.new("RGBA", foreground.size, (10, 10, 10, 100))
    # Offset shadow by (14, 14) pixels to simulate natural overhead light
    shadow_layer.paste(shadow_fill, (fg_x + 14, fg_y + 14), mask=alpha_channel)
    # Blur to create soft ambient occlusion edges
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=12))

    # ── Composite: background → shadow → foreground ────────────────────────
    composite = Image.alpha_composite(background, shadow_layer)
    composite.paste(foreground, (fg_x, fg_y), mask=alpha_channel)

    # ── Save as high-quality JPEG ──────────────────────────────────────────
    composite.convert("RGB").save(output_mockup_path, "JPEG", quality=95)

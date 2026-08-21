"""
SEO & Image Generation Service — Tier 2 Refactor
Generates high-converting bilingual Etsy SEO packages (title_fr/en,
description_fr/en, tags_fr/en) directly via the google-genai SDK in
strict JSON mode, with a deterministic local fallback if the API is
unavailable or every retry fails validation.
"""
import json
import os
import re
import time
import unicodedata
import base64
from typing import List, Optional, Any
from PIL import Image

import requests
try:
    from google import genai
except ImportError:
    genai = None
from openai import OpenAI


# ─────────────────────────────────────────────────────────────────────────────
# DALL-E 3 STENCIL IMAGE GENERATION (unchanged — used by legacy /api/creations routes)
# ─────────────────────────────────────────────────────────────────────────────
def _save_fallback_stencil(theme: str, output_path: str):
    """Draws a beautiful, complex, 100% connected geometric mandala/star pattern locally as a fallback stencil."""
    import math
    from PIL import Image, ImageDraw
    
    img = Image.new("RGB", (1000, 1000), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    center = (500, 500)
    
    # Outer frame
    draw.ellipse([50, 50, 950, 950], outline=(0, 0, 0), width=20)
    # Inner border
    draw.ellipse([150, 150, 850, 850], outline=(0, 0, 0), width=12)
    
    # Geometric connected web
    num_points = 12
    points = []
    for i in range(num_points):
        angle = i * (2 * math.pi / num_points)
        x = center[0] + 350 * math.cos(angle)
        y = center[1] + 350 * math.sin(angle)
        points.append((x, y))
        
    for i in range(num_points):
        for j in range(i + 1, num_points):
            # Connect all points to make a beautiful complex web
            draw.line([points[i], points[j]], fill=(0, 0, 0), width=8)
            
    # Central medallion (filled white, with inner black circle)
    draw.ellipse([350, 350, 650, 650], fill=(255, 255, 255), outline=(0, 0, 0), width=15)
    draw.ellipse([430, 430, 570, 570], fill=(0, 0, 0))
    
    img.save(output_path, "JPEG")
    print(f"[generate_stencil_image] Saved beautiful local B&W stencil fallback to {output_path}")


def legacy_generate_stencil_image(provider: str, banana_key: str, openai_key: str, theme: str, output_path: str, init_image_path: str = None, custom_prompt: str = None, bundle_size: int = 4, design_style: str = "classic"):
    """
    Calls the selected Image AI provider to generate a pure black and white stencil.
    Ensures all black lines are structurally connected (no islands).
    Optionally uses an init_image_path to base the generation on an existing image.
    If custom_prompt is provided, it overrides the default stencil prompt.
    """
    if not provider or (provider not in ["imagen-3", "banana", "openai", "gemini", "google"] and not provider.startswith("gpt-image")):
        if openai_key:
            provider = "gpt-image-1-mini"
        elif banana_key:
            provider = "banana"
        else:
            provider = "gpt-image-1-mini"

    if provider == "openai":
        provider = "gpt-image-1-mini"
    elif provider in ("gemini", "google"):
        provider = "imagen-3"

    legacy_framed_filigree = (
        "Generate a strictly square image (1024x1024 resolution). An intricate, highly detailed, flat vector-style layered stencil silhouette art containing exactly {bundle_size} design(s) of '{theme}'. \n\n"
        "Strict Technical Constraints:\n"
        "- STRUCTURAL RING: The design MUST be entirely enclosed within a solid black circular outer frame ring acting as the primary structural support.\n"
        "- Solid black lines (#000000) on a pure white background (#FFFFFF) only. No gray, shadows, or gradients.\n"
        "- COMPLEX FILIGREE: Incorporate rich, elegant internal filigree and interlacing motifs.\n"
        "- ABSOLUTE STRUCTURAL INTEGRITY: Every internal element MUST be physically fused to neighboring lines or directly connected to the circular outer frame ring using clean, thick bridging joints. Zero floating islands. Optimized for flawless CNC routing."
    )
    legacy_classic = (
        "Generate a strictly square image (1024x1024 resolution). A crisp, perfect, flat vector-style silhouette bundle collection containing exactly {bundle_size} separate designs of '{theme}'. \n\n"
        "Strict Technical Constraints:\n"
        "- Solid black shapes and lines on a solid stark white background only. Pure black (#000000) on pure white (#FFFFFF).\n"
        "- CRITICAL STRUCTURAL CONSTRAINT: Every single black shape and element within each design MUST be physically connected to its main body to prevent floating islands. Must hold together as one connected piece for laser cutting.\n"
        "- Thick, clear, bold lines. NO gradients, shadows, grey pixels, sketchy lines, or text."
    )
    legacy_image_to_image = (
        "\n\nIMAGE-TO-IMAGE INSTRUCTIONS:\n"
        "- Treat the attached reference image strictly as a structural skeleton or shape template.\n"
        "- Output a flat 2D graphic only. Absolutely NO 3D effects, NO bevels, NO shadows, NO color gradients, and NO gray pixels. Every pixel must be either pure black #000000 or pure white #FFFFFF."
    )
    legacy_grad_cap = " Replicate the silhouette of a classic graduation cap / mortarboard from the reference, flattening it into a pure solid black silhouette shape on a stark white background."

    try:
        from ..database import SessionLocal
        from ..models import Setting
        db_s = SessionLocal()
        s = db_s.query(Setting).first()
        if s:
            if s.prompt_legacy_framed_filigree and s.prompt_legacy_framed_filigree.strip():
                legacy_framed_filigree = s.prompt_legacy_framed_filigree
            if s.prompt_legacy_classic and s.prompt_legacy_classic.strip():
                legacy_classic = s.prompt_legacy_classic
            if s.prompt_legacy_image_to_image and s.prompt_legacy_image_to_image.strip():
                legacy_image_to_image = s.prompt_legacy_image_to_image
            if s.prompt_legacy_grad_cap and s.prompt_legacy_grad_cap.strip():
                legacy_grad_cap = s.prompt_legacy_grad_cap
        db_s.close()
    except Exception:
        pass

    try:
        if custom_prompt:
            strict_prompt = custom_prompt
        else:
            if design_style == "framed_filigree":
                strict_prompt = legacy_framed_filigree.replace("{bundle_size}", str(bundle_size)).replace("{theme}", theme)
            else:
                strict_prompt = legacy_classic.replace("{bundle_size}", str(bundle_size)).replace("{theme}", theme)

        if provider.startswith("gpt-image") or provider == "dall-e-3":
            if not openai_key:
                raise ValueError("Clé API OpenAI manquante. Configurez-la dans les paramètres.")
            client = OpenAI(
                api_key=openai_key,
                base_url="https://api.openai.com/v1"
            )
            
            if init_image_path and os.path.exists(init_image_path):
                strict_prompt += legacy_image_to_image
                strict_prompt += legacy_grad_cap

            model_name = provider if provider.startswith("gpt-image") else "gpt-image-1-mini"
            response = client.images.generate(
                model=model_name,
                prompt=strict_prompt,
                n=1,
                size="1024x1024",
                quality="low"
            )
            img_item = response.data[0]
            if img_item.b64_json:
                img_data = base64.b64decode(img_item.b64_json)
            elif img_item.url:
                img_data = requests.get(img_item.url).content
            else:
                raise ValueError("No image URL or b64_json found in response data")
            with open(output_path, 'wb') as handler:
                handler.write(img_data)
                
        elif provider == "imagen-3" or (provider == "banana" and banana_key and (banana_key.startswith("AIza") or banana_key.startswith("AQ"))):
            if not banana_key:
                raise ValueError("Clé API Gemini/Imagen manquante. Configurez-la dans les paramètres.")
                
            try:
                from google.genai import types
                
                client = genai.Client(api_key=banana_key)
                response = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=strict_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type='image/jpeg',
                        negative_prompt='color, photo, 3d, rendering, drop shadow, inner shadow, gradient, shading, gray tones, realistic texture, sketch, blurry, floating parts, text, watermark, signature'
                    )
                )
                if not response.generated_images:
                    raise ValueError("Aucune image générée par Google Imagen 3.")
                
                image_bytes = response.generated_images[0].image.image_bytes
                with open(output_path, 'wb') as handler:
                    handler.write(image_bytes)
                    
            except Exception as e:
                raise ValueError(f"Erreur d'image via Google Imagen 3: {e}")
                
        elif provider == "banana":
            if not banana_key:
                raise ValueError("Clé API Nano Banana manquante. Configurez-la dans les paramètres.")
                
            url = "https://api.banana.dev/start/v4/"
            model_key = "sdxl-1.0-base" 

            payload = {
                "apiKey": banana_key,
                "modelKey": model_key,
                "modelInputs": {
                    "prompt": strict_prompt,
                    "negative_prompt": "colors, shading, gradients, grey, text, watermark, disconnected parts, 3d, realistic, rendering, drop shadow, inner shadow, gray tones, realistic texture",
                    "width": 1024,
                    "height": 1024,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 40
                }
            }
            
            if init_image_path and os.path.exists(init_image_path):
                with open(init_image_path, "rb") as f:
                    b64_image = base64.b64encode(f.read()).decode("utf-8")
                    payload["modelInputs"]["init_image"] = b64_image
                    payload["modelInputs"]["prompt_strength"] = 0.65

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            try:
                model_outputs = data.get("modelOutputs", [])
                if not model_outputs:
                    raise ValueError("L'API Nano Banana n'a retourné aucune image.")
                    
                image_b64 = model_outputs[0].get("image_base64")
                if image_b64:
                    img_data = base64.b64decode(image_b64)
                    with open(output_path, 'wb') as handler:
                        handler.write(img_data)
                else:
                    image_url = model_outputs[0].get("url")
                    if image_url:
                        img_data = requests.get(image_url).content
                        with open(output_path, 'wb') as handler:
                            handler.write(img_data)
                    else:
                        raise ValueError("Format de réponse d'image Nano Banana non reconnu.")
                        
            except Exception as e:
                raise ValueError(f"Erreur lors de l'extraction de l'image Nano Banana: {e}\nPayload reçu: {str(data)[:200]}")
        else:
            raise ValueError(f"Fournisseur d'IA d'image '{provider}' non supporté ou clé API manquante.")
    except Exception as api_err:
        print(f"[generate_stencil_image] AI Generation failed: {api_err}. Falling back to default stencil/Unsplash image.")
        _save_fallback_stencil(theme, output_path)


def regenerate_stencil_image_guided(
    provider: str,
    banana_key: str,
    openai_key: str,
    theme: str,
    current_image_path: str,
    init_image_path: str,
    instructions: str,
    output_path: str
):
    """
    Uses Gemini Multimodal to analyze differences between init_image_path and current_image_path,
    understands user's correction request, generates a revised text prompt,
    and runs the image generator (Imagen 3 / DALL-E 3) with this custom prompt.
    """
    if not banana_key:
        raise ValueError("Clé API Gemini/Imagen manquante pour la correction guidée.")

    from google.genai import types
    
    client = genai.Client(api_key=banana_key)

    def _encode_image(path: str) -> Optional[str]:
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    current_b64 = _encode_image(current_image_path)
    init_b64 = _encode_image(init_image_path)

    if not current_b64:
        legacy_generate_stencil_image(provider, banana_key, openai_key, theme, output_path)
        return

    contents = []

    if init_b64:
        contents.append("=== ORIGINAL BASE IMAGE ===")
        contents.append(
            types.Part.from_bytes(
                data=base64.b64decode(init_b64),
                mime_type="image/jpeg" if init_image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            )
        )

    contents.append("=== CURRENT GENERATED IMAGE (Has defects to correct) ===")
    contents.append(
        types.Part.from_bytes(
            data=base64.b64decode(current_b64),
            mime_type="image/jpeg" if current_image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        )
    )

    system_prompt = (
        "You are an expert prompt engineer for Text-to-Image models (DALL-E 3 and Imagen 3).\n"
        "Your role is to write a revised and corrected image prompt in English based on visual feedback.\n"
        "You are modifying a black and white stencil design for laser cutting.\n"
        "Analyze the original base image and the current generated image. "
        f"Then, read the user's correction instructions: '{instructions}'.\n"
        "Generate a highly detailed, optimized prompt in English for the image generator "
        "describing the final corrected image. The design MUST remain a stark black and white stencil silhouette "
        "with all black parts connected. Include style instructions to make it clean.\n"
        "Return ONLY the plain text prompt, with no markdown, no quotes, and no introductory/concluding text."
    )

    contents.append(f"Original Theme/Topic: {theme}")
    contents.append(f"User's Correction Request: {instructions}")

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=1024
            )
        )
        custom_prompt = response.text.strip()
        print(f"[guided_regeneration] Gemini generated custom prompt: {custom_prompt}")
    except Exception as e:
        print(f"[guided_regeneration] Gemini prompt generation failed: {e}. Falling back to default prompt with instructions.")
        custom_prompt = (
            f"A crisp black and white laser cut stencil of '{theme}' with these corrections: {instructions}. "
            "Solid black body, all lines connected, stark white background."
        )

    legacy_generate_stencil_image(
        provider=provider,
        banana_key=banana_key,
        openai_key=openai_key,
        theme=theme,
        output_path=output_path,
        init_image_path=init_image_path,
        custom_prompt=custom_prompt
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI MOCKUP GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def _extract_artwork_mask(image: Image.Image) -> Image.Image:
    from PIL import ImageOps, Image
    if "A" in image.getbands():
        alpha = image.getchannel("A")
        extrema = alpha.getextrema()
        if extrema[0] < 255:
            return alpha.point(lambda x: 255 if x > 128 else 0)
    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    temp = Image.new("RGBA", image.size)
    temp.paste(image, (0, 0))
    composited = Image.alpha_composite(white_bg, temp)
    gray = composited.convert("L")
    inverted = ImageOps.invert(gray)
    return inverted.point(lambda x: 255 if x > 55 else 0)


def _composite_stencil_on_mockup_bg(stencil_path: str, bg_path: str, output_path: str):
    """
    Composites the B&W stencil PNG onto the mockup background image, 
    making it look like a physical laser-cut wooden decoration.
    Applies double-layer drop shadows, wood grain colors, and contrast enhancements.
    """
    from PIL import Image, ImageFilter, ImageEnhance, ImageChops, ImageOps
    import shutil
    
    if bg_path and os.path.exists(bg_path):
        try:
            bg = Image.open(bg_path).convert("RGBA")
        except Exception:
            bg = Image.new("RGBA", (1024, 1024), (243, 241, 238))
    else:
        bg = Image.new("RGBA", (1024, 1024), (243, 241, 238))
    
    bg = bg.resize((1024, 1024), resample=Image.Resampling.LANCZOS)
    
    from app.services.image import convert_to_transparent_png
    temp_trans_path = stencil_path + ".trans.png"
    try:
        convert_to_transparent_png(stencil_path, temp_trans_path, scale_factor=1)
    except Exception:
        shutil.copy(stencil_path, temp_trans_path)
        
    try:
        with Image.open(temp_trans_path) as stencil:
            stencil_rgba = stencil.convert("RGBA")
    finally:
        if os.path.exists(temp_trans_path):
            try:
                os.remove(temp_trans_path)
            except Exception:
                pass

    max_dim = int(1024 * 0.55)
    stencil_rgba.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    fg_w, fg_h = stencil_rgba.size
    
    fg_x = (1024 - fg_w) // 2
    fg_y = (1024 - fg_h) // 2
    
    # Get alpha mask (isolate ONLY black pixels/transparent pixels to avoid white canvas & transparency traps)
    alpha_channel = _extract_artwork_mask(stencil_rgba)
    wood_layer = Image.new("RGBA", stencil_rgba.size, (48, 32, 20, 255))
    colored_stencil = Image.new("RGBA", stencil_rgba.size, (0, 0, 0, 0))
    colored_stencil.paste(wood_layer, (0, 0), mask=alpha_channel)
    
    dark_inner = Image.new("RGBA", stencil_rgba.size, (25, 15, 8, 255))
    eroded_alpha = alpha_channel.filter(ImageFilter.MinFilter(3))
    edge_mask = ImageChops.difference(alpha_channel, eroded_alpha)
    colored_stencil.paste(dark_inner, (0, 0), mask=edge_mask)

    ao_shadow_layer = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    ao_fill = Image.new("RGBA", stencil_rgba.size, (15, 12, 10, 65))
    ao_shadow_layer.paste(ao_fill, (fg_x + 8, fg_y + 8), mask=alpha_channel)
    ao_shadow_layer = ao_shadow_layer.filter(ImageFilter.GaussianBlur(radius=15))
    
    cast_shadow_layer = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    cast_fill = Image.new("RGBA", stencil_rgba.size, (5, 4, 3, 110))
    cast_shadow_layer.paste(cast_fill, (fg_x + 15, fg_y + 15), mask=alpha_channel)
    cast_shadow_layer = cast_shadow_layer.filter(ImageFilter.GaussianBlur(radius=6))
    
    composite = Image.alpha_composite(bg, ao_shadow_layer)
    composite = Image.alpha_composite(composite, cast_shadow_layer)
    composite.paste(colored_stencil, (fg_x, fg_y), mask=alpha_channel)
    
    composite_rgb = composite.convert("RGB")
    enhancer = ImageEnhance.Contrast(composite_rgb)
    final_mockup = enhancer.enhance(1.04)
    final_mockup.save(output_path, "JPEG", quality=95, optimize=True)
    print(f"[mockup_composite] Created coherent mockup at {output_path}")


def generate_ai_mockup(provider: str, banana_key: str, openai_key: str, stencil_path: str, theme: str, output_path: str):
    """
    Generates a highly realistic lifestyle mockup background using AI, then
    composites the actual B&W stencil onto it for 100% design coherence.
    """
    import tempfile
    import random
    
    if not stencil_path or not os.path.exists(stencil_path):
        raise FileNotFoundError("Stencil image required for AI mockup generation.")
        
    bg_prompt = (
        "E-commerce professional lifestyle presentation photography. Generate a strictly square image (1:1 aspect ratio, 1024x1024). \n\n"
        "CRITICAL IMAGE REFERENCE CONSTRAINT: \n"
        "You must perfectly replicate the exact shape, lines, and intricate details of the attached reference image. Do NOT alter, redraw, or deform the design. Render this exact design as a physical matte black metal laser-cut silhouette, mounted flat on a premium wall.\n\n"
        "DYNAMIC SCENE LAYOUT & AESTHETIC:\n"
        f"- The architectural style, wall texture, surrounding interior/exterior decor, props, and lighting MUST perfectly adapt to the cultural, historical, or visual essence of '{theme}'. \n"
        "- Examples: If '{theme}' is 'Koi Carp', use a serene Japanese onsen or zen garden backdrop with bamboo and shoji screens. If 'Arabic Calligraphy', use Islamic architectural elements, textured stucco walls, and warm Moroccan lantern lighting.\n"
        "- Constant Constraints: Regardless of the theme, the environment must look highly cozy, premium, ultra-realistic, and uncluttered. The foreground should feature subtle, theme-appropriate props.\n"
        "- Lighting & Focus: Soft, natural, cinematic lighting casting subtle, blurry, realistic drop-shadows on the wall behind the metal design. The laser-cut artwork must remain the absolute focal point, fully visible, strictly pure matte black, perfectly proportioned to the wall, and identical to the attached reference."
    )
    
    temp_bg = tempfile.mktemp(suffix=".jpg")
    bg_generated = False
    
    if not provider or (provider not in ["imagen-3", "banana", "openai", "gemini", "google"] and not provider.startswith("gpt-image")):
        if openai_key:
            provider = "gpt-image-1-mini"
        elif banana_key:
            provider = "imagen-3"
        else:
            provider = "gpt-image-1-mini"

    if provider == "openai":
        provider = "gpt-image-1-mini"
    elif provider in ("gemini", "google"):
        provider = "imagen-3"
    
    try:
        if provider.startswith("gpt-image") or provider == "dall-e-3":
            if not openai_key:
                raise ValueError("Clé API OpenAI manquante.")
            client = OpenAI(
                api_key=openai_key,
                base_url="https://api.openai.com/v1"
            )
            model_name = provider if provider.startswith("gpt-image") else "gpt-image-1-mini"
            response = client.images.generate(
                model=model_name,
                prompt=bg_prompt,
                n=1,
                size="1024x1024",
                quality="low"
            )
            img_item = response.data[0]
            if img_item.b64_json:
                img_data = base64.b64decode(img_item.b64_json)
            elif img_item.url:
                img_data = requests.get(img_item.url, timeout=15).content
            else:
                raise ValueError("No image URL or b64_json found in response data")
            with open(temp_bg, 'wb') as handler:
                handler.write(img_data)
            bg_generated = True
            print("[generate_ai_mockup] Generated DALL-E 3 background.")
            
        elif provider == "imagen-3" or (provider == "banana" and banana_key and (banana_key.startswith("AIza") or banana_key.startswith("AQ"))):
            if not banana_key:
                raise ValueError("Clé API Gemini/Imagen manquante.")
            from google.genai import types
            
            client = genai.Client(api_key=banana_key)
            response = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=bg_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type='image/jpeg',
                    negative_prompt='text, watermark, frames, paintings, poster, furniture blocking the wall'
                )
            )
            if response.generated_images:
                bg_bytes = response.generated_images[0].image.image_bytes
                with open(temp_bg, 'wb') as handler:
                    handler.write(bg_bytes)
                bg_generated = True
                print("[generate_ai_mockup] Generated Imagen 3 background.")
            else:
                raise ValueError("Aucun arrière-plan généré par Google Imagen 3.")
                
        elif provider == "banana":
            if not banana_key:
                raise ValueError("Clé API Nano Banana manquante.")
                
            url = "https://api.banana.dev/start/v4/"
            model_key = "sdxl-1.0-base"
            
            payload = {
                "apiKey": banana_key,
                "modelKey": model_key,
                "modelInputs": {
                    "prompt": bg_prompt,
                    "negative_prompt": "text, watermark, frames, paintings, poster, furniture blocking the wall",
                    "width": 1024,
                    "height": 1024,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 40
                }
            }
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            
            model_outputs = data.get("modelOutputs", [])
            if model_outputs:
                image_b64 = model_outputs[0].get("image_base64")
                if image_b64:
                    with open(temp_bg, 'wb') as handler:
                        handler.write(base64.b64decode(image_b64))
                    bg_generated = True
                    print("[generate_ai_mockup] Generated Banana background.")
                else:
                    image_url = model_outputs[0].get("url")
                    if image_url:
                        with open(temp_bg, 'wb') as handler:
                            handler.write(requests.get(image_url).content)
                        bg_generated = True
                        print("[generate_ai_mockup] Generated Banana background.")
            if not bg_generated:
                raise ValueError("Format de réponse d'image Nano Banana non reconnu.")
                
    except Exception as e:
        print(f"[generate_ai_mockup] Background AI generation failed: {e}. Downloading Unsplash fallback room photo.")
        
    if not bg_generated:
        fallback_urls = [
            "https://images.unsplash.com/photo-1615840287214-7fe58a8b668f?w=1024&q=80",
            "https://images.unsplash.com/photo-1606744824163-985d376605aa?w=1024&q=80",
            "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=1024&q=80",
            "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1024&q=80"
        ]
        url = random.choice(fallback_urls)
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                with open(temp_bg, 'wb') as handler:
                    handler.write(resp.content)
                bg_generated = True
                print(f"[generate_ai_mockup] Saved Unsplash fallback room background.")
        except Exception as err:
            print(f"[generate_ai_mockup] Unsplash download failed: {err}. Using local fallback studio background.")
            
    if bg_generated and os.path.exists(temp_bg):
        try:
            # Route to the advanced 3D metal cutout script instead of the old wood layer composite
            from .mockup_engine import composite_stencil_on_bg
            print(f"[generate_ai_mockup] Compositing premium 3D metal cutout onto AI backdrop...")
            composite_stencil_on_bg(stencil_path=stencil_path, bg_path=temp_bg, output_path=output_path, material="matte_black_metal")
        finally:
            try:
                os.remove(temp_bg)
            except Exception:
                pass
    else:
        from app.services.mockup_processor import create_ecommerce_mockup
        create_ecommerce_mockup(stencil_path, output_path)


# ─────────────────────────────────────────────────────────────────────────────
# JSON RESPONSE CLEANUP
# ─────────────────────────────────────────────────────────────────────────────
def clean_json_response(raw_text: str) -> dict:
    """Strips markdown code fences and isolates the first valid JSON object."""
    text = re.sub(r"```json\s*", "", raw_text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        raise json.JSONDecodeError("No JSON object found in response", text, 0)

    return json.loads(text[start:end])


# ─────────────────────────────────────────────────────────────────────────────
# TIER 2 — SEO SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────
SEO_SYSTEM_PROMPT = """You are an elite Etsy SEO copywriter and conversion specialist for the laser cutting / digital craft files niche (SVG, DXF, AI, EPS, PDF cut files for Cricut, Silhouette, Glowforge, xTool).

You MUST respond with a single, valid JSON object and nothing else. The JSON structure is STRICTLY:
{
  "title_fr": "...",
  "title_en": "...",
  "description_fr": "...",
  "description_en": "...",
  "tags_fr": ["tag1", "tag2", "... 13 items total ..."],
  "tags_en": ["tag1", "tag2", "... 13 items total ..."]
}

=== TITLE RULES (title_fr, title_en) ===
- HARD LIMIT: maximum 140 characters. Count strictly.
- Style: "Etsy 2025" Organic and fluid. Prioritize readability and buyer intent over rigid keyword stuffing. Use natural phrasing and em-dashes (–) instead of pipes (|).
- Front-load the product and quantity (e.g. read the incoming collection size constraint BUNDLE SIZE and write "[BUNDLE SIZE] [Subject] SVG Bundle" instead of a placeholder like "[X]"), followed by the purpose ("for Laser Cutting"), and finally the compatible machines.
- Example FR (if bundle size is 6): "6 Libellules Décoratives SVG pour Découpe Laser – Fichier Cricut, Glowforge et xTool pour Décoration Murale"
- Example EN (if bundle size is 6): "6 Dragonfly SVG Bundle for Laser Cutting – Decorative Garden Wall Art Files for Cricut, Glowforge & xTool"
- NEVER use trademarked character/brand names.

=== DESCRIPTION RULES (description_fr, description_en) ===
Produce a detailed bilingual description following this EXACT structure. Replace [bracketed placeholders] with content specific to the real theme. Dynamically read the incoming BUNDLE SIZE and write this number instead of [X] (e.g. "Ce pack comprend 6 design(s) unique(s)...").

FRENCH TEMPLATE (follow exactly):
"[Emoji du thème] [Phrase d'accroche courte, fluide et spécifique au design réel] !

Ce pack comprend [BUNDLE SIZE] design(s) unique(s) de [Thème], parfait(s) pour vos créations sur le thème de [mots-clés élargis liés au thème].

Ces fichiers numériques sont idéaux pour la gravure ou découpe laser, le vinyle, le papier, le flocage textile et de nombreux projets DIY.

👉 Tous les cliparts sont fournis en silhouette noire ou trait noir épais, avec un style moderne, épuré et facile à découper. Ils sont spécialement conçus pour offrir un résultat propre et professionnel avec les machines Cricut, Silhouette, ScanNCut, ainsi qu'avec les logiciels de découpe et gravure laser tels que LightBurn.

Parfait pour les projets de [mots-clés contextuels liés au thème] et gravure laser. 🚀

📁 FORMATS DE FICHIERS INCLUS
Vous recevrez les fichiers en haute qualité :
- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser
- PNG – fond transparent, haute résolution (Amélioré x3)
- DXF – Silhouette Studio, machines laser
- AI – fichiers vectoriels éditables Adobe Illustrator
- EPS – fichiers vectoriels éditables
- PDF - Impression haute définition (Amélioré x3)

✔ Compatibles avec :
Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, laser CO₂, laser diode, CNC

📥 TÉLÉCHARGEMENT NUMÉRIQUE
📌 Produit numérique – aucun article physique envoyé
Téléchargement immédiat après purchase sur Etsy.

📜 Conditions d'utilisation
✔ Utilisation personnelle
✔ Utilisation commerciale autorisée sur produits finis : Licence commerciale requise. Pour utiliser ce fichier à des fins commerciales, une licence est obligatoire. Vous pouvez choisir la licence adaptée à votre besoin.

👉 Les licences sont disponibles ici :
Licence pour 1 fichier : https://digitalfilesbymop.etsy.com/listing/4499076966
Licence pour tous les fichiers de la boutique : https://digitalfilesbymop.etsy.com/listing/4499075567

❌ Revente, partage ou redistribution des fichiers interdits"

ENGLISH TEMPLATE:
Mirror the French template section-for-section, naturally translated (not a literal word-for-word translation), same emojis, same section order, and the exact same two license URLs unchanged.

=== TAG RULES (tags_fr, tags_en) ===
- EXACTLY 13 tags per language.
- Every single tag MUST be a multi-word long-tail keyword (e.g., 'metal wall art'), but strictly UNDER 20 characters in total length. Discard any tag exceeding 20 characters.
- Strictly lowercase, ASCII only, no punctuation. 
- Order of priority: Specific subject terms first, then formats (svg, dxf), then machines (cricut, glowforge), then generic niche terms (wood laser, laser cut)."""


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _ascii_tag(value) -> str:
    """Normalizes a tag: ASCII only, lowercase, max 20 chars (matches existing house convention)."""
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9 ]+", " ", value).lower()
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) >= 20:
        return ""
    return value


def _normalize_tags_exact13(raw_tags, fallback_pool: list) -> list:
    """Normalizes tags and pads/truncates to exactly 13, preserving priority order."""
    items, seen = [], set()

    source = raw_tags if isinstance(raw_tags, list) else (
        [t.strip() for t in str(raw_tags or "").split(",")]
    )
    for t in source:
        tag = _ascii_tag(t)
        if tag and tag not in seen:
            items.append(tag)
            seen.add(tag)

    for t in fallback_pool:
        if len(items) >= 13:
            break
        tag = _ascii_tag(t)
        if tag and tag not in seen:
            items.append(tag)
            seen.add(tag)

    return items[:13]


def _safe_title(title: str, fallback: str) -> str:
    title = re.sub(r"\s+", " ", (title or fallback)).strip()
    if len(title) <= 140:
        return title
    return title[:137].rstrip(" |–-,") + "..."


def _theme_label(theme: str) -> str:
    return re.sub(r"\s+", " ", (theme or "Design Laser").strip()).title()[:80]


def _validate_seo_payload(data: dict) -> list:
    """Returns a list of validation errors (empty = valid)."""
    errors = []
    required = ["title_fr", "title_en", "description_fr", "description_en", "tags_fr", "tags_en"]
    for field in required:
        if not data.get(field):
            errors.append(f"Missing or empty field: {field}")

    if data.get("title_fr") and len(data["title_fr"]) > 140:
        errors.append(f"title_fr exceeds 140 chars ({len(data['title_fr'])})")
    if data.get("title_en") and len(data["title_en"]) > 140:
        errors.append(f"title_en exceeds 140 chars ({len(data['title_en'])})")

    for lang in ("tags_fr", "tags_en"):
        tags = data.get(lang)
        if isinstance(tags, list):
            too_long = [t for t in tags if len(str(t)) > 20]
            if too_long:
                errors.append(f"{lang} has tags over 20 chars: {too_long[:3]}")
        elif tags:
            errors.append(f"{lang} must be a list")

    for lang_field in ("description_fr", "description_en"):
        desc = str(data.get(lang_field) or "")
        required_markers = [
            "digitalfilesbymop.etsy.com/listing/4499076966",
            "digitalfilesbymop.etsy.com/listing/4499075567",
        ]
        missing = [m for m in required_markers if m not in desc]
        if missing:
            errors.append(f"{lang_field} missing required license links")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# DETERMINISTIC LOCAL FALLBACK (no LLM call)
# ─────────────────────────────────────────────────────────────────────────────
def get_fallback_seo(theme: str, bundle_size: int = 4) -> dict:
    """
    Deterministic, template-based bilingual SEO package used when no Gemini
    key is configured, or as the final safety net if every Gemini attempt
    fails. Mirrors the exact Tier 2 structure, without per-design AI
    customization.
    """
    label = _theme_label(theme)
    label_lower = label.lower()[:19]

    title_fr = _safe_title(
        f"🎨 {label} SVG DXF | Fichier Découpe Laser – Cricut Glowforge xTool | Pochoir Bois",
        f"🎨 {label} SVG DXF | Fichier Découpe Laser – Cricut Glowforge xTool | Pochoir Bois",
    )
    title_en = _safe_title(
        f"🎨 {label} SVG DXF | Laser Cut File – Cricut Glowforge xTool | Wood Stencil",
        f"🎨 {label} SVG DXF | Laser Cut File – Cricut Glowforge xTool | Wood Stencil",
    )

    description_fr = (
        f"🎨 Découvrez ce clipart {label} unique, pensé pour vos créations en découpe laser !\n\n"
        f"Ce pack comprend un lot de {bundle_size} designs de {label}, parfait pour vos créations sur le thème de "
        f"{label}, de la décoration murale et des cadeaux personnalisés.\n\n"
        "Ces fichiers numériques sont idéaux pour la gravure ou découpe laser, le vinyle, le papier, "
        "le flocage textile et de nombreux projets DIY.\n\n"
        "👉 Tous les cliparts sont fournis en silhouette noire ou trait noir épais, avec un style "
        "moderne, épuré et easy à découper. Ils sont spécialement conçus pour offrir un résultat "
        "propre et professionnel avec les machines Cricut, Silhouette, ScanNCut, ainsi qu'avec les "
        "logiciels de découpe et gravure laser tels que LightBurn.\n\n"
        f"Parfait pour les projets de décoration, cadeaux et gravure laser autour de {label}. 🚀\n\n"
        "📁 FORMATS DE FICHIERS INCLUS\n"
        "Vous recevrez les fichiers en haute qualité :\n"
        "- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser\n"
        "- PNG – fond transparent, haute résolution (Amélioré x3)\n"
        "- DXF – Silhouette Studio, machines laser\n"
        "- AI – fichiers vectoriels éditables Adobe Illustrator\n"
        "- EPS – fichiers vectoriels éditables\n"
        "- PDF - Impression haute définition (Amélioré x3)\n\n"
        "✔ Compatibles avec :\n"
        "Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, laser CO₂, laser diode, CNC\n\n"
        "📥 TÉLÉCHARGEMENT NUMÉRIQUE\n"
        "📌 Produit numérique – aucun article physique envoyé\n"
        "Téléchargement immédiat après achat sur Etsy.\n\n"
        "📜 Conditions d'utilisation\n"
        "✔ Utilisation personnelle\n"
        "✔ Utilisation commerciale autorisée sur produits finis : Licence commerciale requise. "
        "Pour utiliser ce fichier à des fins commerciales, une licence est obligatoire. Vous pouvez "
        "choisir la licence adaptée à votre besoin.\n\n"
        "👉 Les licences sont disponibles ici :\n"
        "Licence pour 1 fichier : https://digitalfilesbymop.etsy.com/listing/4499076966\n"
        "Licence pour tous les fichiers de la boutique : https://digitalfilesbymop.etsy.com/listing/4499075567\n\n"
        "❌ Revente, partage ou redistribution des fichiers interdits"
    )

    description_en = (
        f"🎨 Discover this one-of-a-kind {label} clipart, designed for your laser cutting projects!\n\n"
        f"This pack includes a bundle of {bundle_size} {label} designs, perfect for your creations themed around "
        f"{label}, wall decor and personalized gifts.\n\n"
        "These digital files are ideal for laser engraving or cutting, vinyl, paper, textile flocking "
        "and many other DIY projects.\n\n"
        "👉 All cliparts are provided as black silhouettes or thick black outlines, in a modern, "
        "clean and easy-to-cut style. They're specially designed for clean, professional results "
        "with Cricut, Silhouette, ScanNCut machines, as well as laser cutting and engraving software "
        "such as LightBurn.\n\n"
        f"Perfect for decoration, gift and laser engraving projects around {label}. 🚀\n\n"
        "📁 INCLUDED FILE FORMATS\n"
        "You will receive high quality files:\n"
        "- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser\n"
        "- PNG – transparent background, high resolution (Upscaled x3)\n"
        "- DXF – Silhouette Studio, laser machines\n"
        "- AI – editable Adobe Illustrator vector files\n"
        "- EPS – editable vector files\n"
        "- PDF - High definition print (Upscaled x3)\n\n"
        "✔ Compatible with:\n"
        "Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, CO₂ laser, diode laser, CNC\n\n"
        "📥 DIGITAL DOWNLOAD\n"
        "📌 Digital product – no physical item will be shipped\n"
        "Instant download after purchase on Etsy.\n\n"
        "📜 Terms of Use\n"
        "✔ Personal use\n"
        "✔ Commercial use allowed on finished products: Commercial license required. To use this "
        "file for commercial purposes, a license is mandatory. You can choose the license that fits "
        "your needs.\n\n"
        "👉 Licenses available here:\n"
        "License for 1 file: https://digitalfilesbymop.etsy.com/listing/4499076966\n"
        "License for all shop files: https://digitalfilesbymop.etsy.com/listing/4499075567\n\n"
        "❌ Resale, sharing or redistribution of files is prohibited"
    )

    fallback_fr = [
        "fichier svg", "decoupe laser", "fichier dxf", "stencil laser", "fichier eps",
        "fichier ai", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
        "bois laser", "gravure laser", label_lower,
    ]
    fallback_en = [
        "svg file", "laser cut file", "dxf file", "laser stencil", "eps file",
        "ai file", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
        "wood laser", "laser engrave", label_lower,
    ]

    return {
        "title_fr": title_fr,
        "title_en": title_en,
        "description": description_fr,
        "description_fr": description_fr,
        "description_en": description_en,
        "tags_fr": _normalize_tags_exact13([], fallback_fr),
        "tags_en": _normalize_tags_exact13([], fallback_en),
    }


# ─────────────────────────────────────────────────────────────────────────────
# TIER 2 — MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def generate_seo_metadata(settings, theme: str) -> dict:
    """
    Direct Gemini SEO generation via the google-genai SDK in strict JSON
    mode. Produces a bilingual, high-converting Etsy SEO package for
    `theme`. Falls back to `get_fallback_seo(theme)` if no key is
    configured, the client fails to initialize, or every retry fails
    parsing/validation.
    """
    try:
        if isinstance(settings, dict):
            provider = settings.get("text_ai_provider")
            gemini_key = settings.get("gemini_key")
            mistral_key = settings.get("mistral_key")
            bundle_size = settings.get("bundle_size", 4)
        else:
            provider = getattr(settings, "text_ai_provider", None)
            gemini_key = getattr(settings, "gemini_key", None)
            mistral_key = getattr(settings, "mistral_key", None)
            bundle_size = getattr(settings, "bundle_size", 4)

        gemini_key = (gemini_key or "").strip()
        mistral_key = (mistral_key or "").strip()

        if not provider or provider not in ["gemini-2.0-flash-lite", "gemini-1.5-pro", "mistral-large-latest", "gemini", "mistral"]:
            if gemini_key:
                provider = "gemini-2.0-flash-lite"
            elif mistral_key:
                provider = "mistral-large-latest"
            else:
                provider = "gemini-2.0-flash-lite"

        if provider == "gemini":
            provider = "gemini-2.0-flash-lite"
        elif provider == "mistral":
            provider = "mistral-large-latest"
    except Exception as e:
        print(f"[generator] Error resolving text provider, falling back to gemini: {e}")
        provider = "gemini-2.0-flash-lite"
        gemini_key = ""
        mistral_key = ""
        bundle_size = 4

    try:
        if provider.startswith("mistral"):
            from .seo_engine import generate_etsy_seo
            res = generate_etsy_seo(
                theme=theme,
                provider=provider,
                gemini_key="",
                mistral_key=mistral_key,
                openai_key="",
                bundle_size=bundle_size
            )
            return res if res else get_fallback_seo(theme, bundle_size=bundle_size)
    except Exception as e:
        print(f"[generator] Mistral routing failed: {e}. Falling back to Gemini.")
        provider = "gemini-2.0-flash-lite"

    if not gemini_key or not provider.startswith("gemini"):
        print("[generator] No Gemini API key configured or unknown provider — using local fallback SEO.")
        return get_fallback_seo(theme, bundle_size=bundle_size)

    try:
        client = genai.Client(api_key=gemini_key)
    except Exception as e:
        print(f"[generator] Failed to init Gemini client: {e} — using local fallback SEO.")
        return get_fallback_seo(theme, bundle_size=bundle_size)

    label = _theme_label(theme)
    user_message = (
        "Generate the complete bilingual Etsy SEO JSON package for this laser-cutting digital product.\n"
        f"THEME: \"{theme}\"\n"
        f"BUNDLE SIZE (QUANTITY OF DESIGNS): {bundle_size}\n\n"
        "Follow every rule in the system instructions exactly — adapt the titles and descriptions to clearly state that this is a pack/collection containing exactly this number of designs. Ensure the two required license links remain intact. Return ONLY the JSON object, no other text."
    )

    fallback_fr = [
        "fichier svg", "decoupe laser", "fichier dxf", "stencil laser", "fichier eps",
        "fichier ai", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
        "bois laser", "gravure laser", label.lower()[:19],
    ]
    fallback_en = [
        "svg file", "laser cut file", "dxf file", "laser stencil", "eps file",
        "ai file", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
        "wood laser", "laser engrave", label.lower()[:19],
    ]

    seo_instruction = (settings.prompt_seo.strip() if (settings and settings.prompt_seo and settings.prompt_seo.strip()) else SEO_SYSTEM_PROMPT).strip()

    last_error = None
    for attempt in range(1, 3):
        try:
            response = client.models.generate_content(
                model=provider,
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=seo_instruction,
                    response_mime_type="application/json",
                    temperature=0.7,
                    max_output_tokens=8192,
                )
            )

            try:
                finish_reason = response.candidates[0].finish_reason
                if str(finish_reason) in ("MAX_TOKENS", "2"):
                    print(f"[generator] Attempt {attempt}: truncated (MAX_TOKENS). Retrying...")
                    last_error = "MAX_TOKENS"
                    time.sleep(1)
                    continue
            except (IndexError, AttributeError):
                pass

            data = clean_json_response(response.text)
            errors = _validate_seo_payload(data)
            if errors:
                print(f"[generator] Attempt {attempt}: validation errors: {errors}")
                last_error = errors
                time.sleep(1)
                continue

            description_fr = data.get("description_fr", "")
            description_en = data.get("description_en", "")

            normalized = {
                "title_fr": _safe_title(
                    data.get("title_fr", ""),
                    f"🎨 {label} SVG DXF | Fichier Découpe Laser – Cricut Glowforge xTool",
                ),
                "title_en": _safe_title(
                    data.get("title_en", ""),
                    f"🎨 {label} SVG DXF | Laser Cut File – Cricut Glowforge xTool",
                ),
                "description": description_fr,
                "description_fr": description_fr,
                "description_en": description_en,
                "tags_fr": _normalize_tags_exact13(data.get("tags_fr", []), fallback_fr),
                "tags_en": _normalize_tags_exact13(data.get("tags_en", []), fallback_en),
            }
            print(f"[generator] SEO generated successfully on attempt {attempt}.")
            return normalized

        except json.JSONDecodeError as e:
            print(f"[generator] Attempt {attempt}: JSON parse error: {e}")
            last_error = str(e)
            time.sleep(1.5)
        except Exception as e:
            print(f"[generator] Attempt {attempt}: Gemini API error: {e}")
            last_error = str(e)
            time.sleep(2)

    print(f"[generator] All Gemini attempts failed ({last_error}). Using local fallback SEO.")
    return get_fallback_seo(theme, bundle_size=bundle_size)
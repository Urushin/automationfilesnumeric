"""
Image Engine — v5.0
Handles image generation with a dynamic fallback loop: [Together AI, Fal.ai, Pollinations, gpt-image-2, Banana/SDXL, Imagen 3].
No silent fallbacks: fails loudly with exceptions if all providers are exhausted.
"""

import base64
import os
import io
import time
import requests
import urllib.parse
from typing import Optional
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from fastapi import HTTPException
from ..core.config import settings
from openai import OpenAI


class _HTMLResponseError(ValueError):
    """Raised when an API returns an HTML page instead of expected JSON."""
    pass


def _safe_json(resp: requests.Response, provider: str) -> dict:
    """
    Safely parse a JSON response. Raises _HTMLResponseError if the body
    is HTML (e.g. a CDN 404 page) so the outer failover loop can skip
    gracefully to the next provider.
    """
    content_type = resp.headers.get("Content-Type", "")
    raw = resp.text or ""
    snippet = (raw[:150] + "...") if len(raw) > 150 else raw

    if raw.lstrip().startswith(("<!DOCTYPE", "<html", "<HTML")):
        raise _HTMLResponseError(
            f"{provider}: Received HTML instead of JSON (status={resp.status_code}). "
            f"Preview: {snippet!r}"
        )

    if "application/json" not in content_type and "text/json" not in content_type:
        try:
            return resp.json()
        except Exception:
            raise _HTMLResponseError(
                f"{provider}: Response is not JSON (Content-Type={content_type!r}). "
                f"Preview: {snippet!r}"
            )

    try:
        return resp.json()
    except ValueError as exc:
        raise _HTMLResponseError(
            f"{provider}: JSON decode error — {exc}. Preview: {snippet!r}"
        )


def _describe_image_with_vision(openai_key: str, image_path: str) -> str:
    if not os.path.exists(image_path):
        return ""
    try:
        ext = os.path.splitext(image_path)[1].lower().strip(".")
        mime_type = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/png")
        
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {openai_key.strip()}",
            "Content-Type": "application/json"
        }

        vision_prompt = "Describe the core subject, exact posture, layout, and shapes of this image in English for a silhouette stencil maker. Output ONLY the raw description, no prose."
        try:
            from ..database import SessionLocal
            from ..models import Setting
            db_s = SessionLocal()
            s = db_s.query(Setting).first()
            if s and s.prompt_vision_description and s.prompt_vision_description.strip():
                vision_prompt = s.prompt_vision_description.strip()
            db_s.close()
        except Exception:
            pass

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": vision_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
            proxies={"http": None, "https": None}
        )

        if response.status_code != 200:
            try:
                error_msg = response.json().get('error', {}).get('message', response.text)
            except Exception:
                error_msg = response.text
            raise RuntimeError(f"OpenAI Chat API HTTP Error ({response.status_code}): {error_msg}")

        description = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[VISION SUCCESS] Generated image description: {description}")
        return description
    except Exception as e:
        print(f"[VISION ERROR] Vision description failed: {e}")
        raise ValueError(f"Vision description failed: {e}") from e


def execute_inpainting(image_path: str, mask_path: str, prompt: str, output_path: str, openai_key: str = None, model: str = None):
    for var_name in ["image_path", "mask_path", "output_path"]:
        val = locals()[var_name]
        if val.startswith("http://") or val.startswith("https://"):
            parsed_url = urllib.parse.urlparse(val)
            if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                val = parsed_url.path
        if val.startswith("/static/"):
            storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage"))
            val = val.replace("/static/", storage_dir + "/")
        if var_name == "image_path":
            image_path = val
        elif var_name == "mask_path":
            mask_path = val
        elif var_name == "output_path":
            output_path = val

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    try:
        api_key = openai_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Clé API OpenAI manquante pour l'inpainting.")
        client = OpenAI(api_key=api_key.strip(), base_url="https://api.openai.com/v1")
        
        style_suffix = ", pure black and white stencil silhouette, flat 2D graphic, solid black lines on pure white background, no shading, no colors, no gradients, no gray pixels"
        final_prompt = prompt + style_suffix
        
        img = Image.open(image_path).convert("RGBA")
        if img.mode == "RGBA":
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(background, img)
        img = img.convert("RGBA")
        mask = Image.open(mask_path).convert("RGBA")
        
        target_size = (1024, 1024)
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        if mask.size != target_size:
            mask = mask.resize(target_size, Image.Resampling.LANCZOS)

        image_buffer = io.BytesIO()
        mask_buffer = io.BytesIO()
        img.save(image_buffer, format="PNG")
        mask.save(mask_buffer, format="PNG")
        image_buffer.seek(0)
        mask_buffer.seek(0)

        # Fallback list of models to try in sequence (cheapest first)
        selected_model = model or "gpt-image-1-mini"
        candidates = [selected_model]
        for fallback in ["gpt-image-1-mini", "gpt-image-1", "gpt-image-1.5", "gpt-image-2", "dall-e-2", "dall-e-3"]:
            if fallback not in candidates:
                candidates.append(fallback)

        response = None
        last_err = None
        successful_model = None

        for candidate in candidates:
            try:
                print(f"[inpainting] Trying client.images.edit with model {candidate}")
                response = client.images.edit(
                    model=candidate,
                    image=("image.png", image_buffer, "image/png"),
                    mask=("mask.png", mask_buffer, "image/png"),
                    prompt=final_prompt,
                    n=1,
                    size="1024x1024",
                    quality="low"
                )
                successful_model = candidate
                break
            except Exception as oe:
                print(f"[inpainting] Failed with model {candidate}: {oe}")
                last_err = oe
                continue

        if not response:
            raise ValueError(f"Inpainting failed (all models exhausted, last error: {last_err})")

        img_item = response.data[0]
        if img_item.b64_json:
            img_data = base64.b64decode(img_item.b64_json)
        elif img_item.url:
            image_url = img_item.url
            resp = requests.get(image_url, timeout=15, proxies={"http": None, "https": None})
            resp.raise_for_status()
            img_data = resp.content
        else:
            raise ValueError("No image URL or b64_json found in response data")

        with open(output_path, 'wb') as handler:
            handler.write(img_data)
        print(f"[{successful_model} SUCCESS] Inpainting applied and written to {output_path}")
        
        try:
            print(f"[execute_inpainting] Unconditionally applying binarize/threshold filter to: {output_path}")
            local_binarize_image(output_path, output_path)
        except Exception as be:
            print(f"[execute_inpainting] Warning: Binarization/threshold filter failed: {be}")
    finally:
        if mask_path and os.path.exists(mask_path):
            try:
                os.remove(mask_path)
            except Exception:
                pass


def local_binarize_image(input_path: str, output_path: str, apply_binarization: bool = True):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
    if not apply_binarization:
        if input_path != output_path:
            import shutil
            shutil.copy(input_path, output_path)
        print(f"[local_binarize_image] Bypassed/deactivated binarization for {input_path}")
        return
    try:
        import cv2
        import numpy as np
        import io
        from PIL import Image
        
        # Load image (supporting SVG to PNG conversion via cairosvg if needed)
        if input_path.lower().endswith('.svg'):
            import cairosvg
            png_output = cairosvg.svg2png(url=input_path)
            img = Image.open(io.BytesIO(png_output)).convert("RGBA")
        else:
            img = Image.open(input_path).convert("RGBA")
            
        # Composite onto white background to handle transparency
        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        white_bg.alpha_composite(img)
        
        # Convert to numpy array for OpenCV
        np_img = np.array(white_bg)
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGBA2GRAY)
        
        # High-quality edge-preserving smoothing filter to avoid pixelation
        smoothed = cv2.bilateralFilter(gray, 5, 50, 50)
        
        # Clean global binary thresholding instead of noisy adaptive thresholding
        _, thresh = cv2.threshold(smoothed, 220, 255, cv2.THRESH_BINARY)
        
        # Get transparency mask from original image
        alpha = np.array(img)[:, :, 3]
        
        # Construct output: transparent where white, black where black
        h, w = thresh.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, 0] = 0
        rgba[:, :, 1] = 0
        rgba[:, :, 2] = 0
        
        # Keep alpha only where it was thresholded to black (value 0 in binary threshold) and original alpha > 0
        rgba[:, :, 3] = np.where((thresh == 0) & (alpha > 0), alpha, 0)
        
        out_img = Image.fromarray(rgba, "RGBA")
        out_img.save(output_path, "PNG")
        print(f"[local_binarize_image] Saved smooth transparent PNG via cv2.threshold: {output_path}")
    except Exception as e:
        print(f"[local_binarize_image] cv2 threshold failed, falling back to PIL: {e}")
        try:
            if input_path.lower().endswith('.svg'):
                import cairosvg
                png_output = cairosvg.svg2png(url=input_path)
                img = Image.open(io.BytesIO(png_output)).convert("RGBA")
            else:
                img = Image.open(input_path).convert("RGBA")
                
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.alpha_composite(img)
            gray = white_bg.convert("L")
            
            gray_data = list(gray.getdata())
            original_data = list(img.getdata())
            
            new_data = []
            for i, item in enumerate(original_data):
                gray_val = gray_data[i]
                alpha_val = item[3]
                if gray_val < 220 and alpha_val > 0:
                    new_data.append((0, 0, 0, alpha_val))
                else:
                    new_data.append((255, 255, 255, 0))
                    
            img.putdata(new_data)
            img.save(output_path, "PNG")
            print(f"[local_binarize_image] Saved transparent PNG via PIL fallback: {output_path}")
        except Exception as fallback_err:
            raise RuntimeError(f"Binarization completely failed: {fallback_err}")


def local_binarize_opaque(input_path: str, output_path: str, apply_binarization: bool = True):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
    if not apply_binarization:
        if input_path != output_path:
            import shutil
            shutil.copy(input_path, output_path)
        print(f"[local_binarize_opaque] Bypassed/deactivated binarization for {input_path}")
        return
    try:
        import cv2
        import numpy as np
        import io
        from PIL import Image

        if input_path.lower().endswith('.svg'):
            import cairosvg
            png_output = cairosvg.svg2png(url=input_path)
            img = Image.open(io.BytesIO(png_output)).convert("RGBA")
        else:
            img = Image.open(input_path).convert("RGBA")
            
        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        white_bg.alpha_composite(img)
        
        np_img = np.array(white_bg)
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGBA2GRAY)
        
        # High-quality edge-preserving smoothing filter
        smoothed = cv2.bilateralFilter(gray, 5, 50, 50)
        
        # Clean global binary thresholding
        _, thresh = cv2.threshold(smoothed, 220, 255, cv2.THRESH_BINARY)
        
        h, w = thresh.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, 0] = np.where(thresh == 0, 0, 255)
        rgba[:, :, 1] = np.where(thresh == 0, 0, 255)
        rgba[:, :, 2] = np.where(thresh == 0, 0, 255)
        rgba[:, :, 3] = 255
        
        out_img = Image.fromarray(rgba, "RGBA")
        out_img.save(output_path, "PNG")
        print(f"[local_binarize_opaque] Saved smooth opaque PNG via cv2.threshold: {output_path}")
    except Exception as e:
        print(f"[local_binarize_opaque] cv2 threshold failed, falling back to PIL: {e}")
        try:
            if input_path.lower().endswith('.svg'):
                import cairosvg
                png_output = cairosvg.svg2png(url=input_path)
                img = Image.open(io.BytesIO(png_output)).convert("RGBA")
            else:
                img = Image.open(input_path).convert("RGBA")
                
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg.alpha_composite(img)
            gray = white_bg.convert("L")
            
            gray_data = list(gray.getdata())
            new_data = []
            for g_val in gray_data:
                if g_val < 220:
                    new_data.append((0, 0, 0, 255))
                else:
                    new_data.append((255, 255, 255, 255))
                    
            out_img = Image.new("RGBA", img.size)
            out_img.putdata(new_data)
            out_img.save(output_path, "PNG")
            print(f"[local_binarize_opaque] Saved opaque PNG via PIL fallback: {output_path}")
        except Exception as fallback_err:
            raise RuntimeError(f"Failed to binarize opaque image: {fallback_err}")


# ==============================================================================
# NEW FREE IMAGE-TO-IMAGE STRATEGIES
# ==============================================================================

def _try_together_ai_img2img(prompt: str, init_image_path: str, output_path: str):
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise ValueError("TOGETHER_API_KEY missing")
    if not init_image_path or not os.path.exists(init_image_path):
        raise FileNotFoundError(f"init_image_path missing: {init_image_path}")
    try:
        print("[image_engine] Attempting Tier 1: Together AI Img2Img...")
        with open(init_image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        
        url = "https://api.together.xyz/v1/images/generations"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "stabilityai/stable-diffusion-xl-base-1.0",
            "prompt": prompt,
            "image_url": f"data:image/png;base64,{b64_data}",
            "steps": 25,
            "strength": 0.35,
            "width": 1024,
            "height": 1024
        }
        r = requests.post(url, json=payload, headers=headers, timeout=40)
        if r.status_code != 200: raise ValueError(r.text)
        img_url = r.json()["data"][0]["url"]
        with open(output_path, "wb") as out:
            out.write(requests.get(img_url, timeout=20).content)
        return [output_path]
    except Exception as e:
        print(f"[image_engine] Together AI failed: {e}")
        raise e


def _try_fal_ai_img2img(prompt: str, init_image_path: str, output_path: str):
    api_key = os.getenv("FAL_KEY")
    if not api_key:
        raise ValueError("FAL_KEY missing")
    if not init_image_path or not os.path.exists(init_image_path):
        raise FileNotFoundError(f"init_image_path missing: {init_image_path}")
    try:
        print("[image_engine] Attempting Tier 2: Fal.ai Flux Img2Img...")
        with open(init_image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
            
        url = "https://queue.fal.run/fal-ai/flux/schnell/image-to-image"
        headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "image_url": f"data:image/png;base64,{b64_data}",
            "strength": 0.40,
            "sync_mode": True
        }
        r = requests.post(url, json=payload, headers=headers, timeout=40)
        if r.status_code != 200: raise ValueError(r.text)
        img_url = r.json()["image"]["url"]
        with open(output_path, "wb") as out:
            out.write(requests.get(img_url, timeout=20).content)
        return [output_path]
    except Exception as e:
        print(f"[image_engine] Fal.ai failed: {e}")
        raise e


def _try_pollinations_fallback(prompt: str, output_path: str):
    try:
        print("[image_engine] Attempting Tier 3 Safety Net: Pollinations...")
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/p/{encoded}?model=flux&width=1024&height=1024"
        r = requests.get(url, timeout=40)
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return [output_path]
        raise ValueError(f"HTTP {r.status_code}")
    except Exception as e:
        print(f"[image_engine] Pollinations failed: {e}")
        raise e

# ==============================================================================


def _try_dalle(openai_key: str, model: str, prompt: str, output_path: str, init_image_path: str = None, n: int = 1, vectorize: bool = False, quality: str = "low") -> list[str]:
    if not openai_key or not openai_key.strip():
        raise ValueError(f"Clé API OpenAI manquante pour {model}.")
    client = OpenAI(api_key=openai_key.strip(), base_url="https://api.openai.com/v1")
    
    # Force quality to 'low' to minimize costs
    resolved_quality = quality if quality in ("low", "medium", "high") else "low"
    
    candidates = [model]
    # Cheapest models first in fallback chain
    for fallback in ["gpt-image-1-mini", "gpt-image-1", "gpt-image-1.5", "gpt-image-2", "dall-e-2", "dall-e-3"]:
        if fallback not in candidates:
            candidates.append(fallback)

    response = None
    last_err = None
    successful_model = None

    for candidate in candidates:
        try:
            if init_image_path and os.path.exists(init_image_path):
                print(f"[{candidate}] Structural layout guidance detected via client.images.edit.")
                with Image.open(init_image_path) as img:
                    img_rgba = img.convert("RGBA")
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_f:
                        temp_png_path = tmp_f.name
                    img_rgba.save(temp_png_path, "PNG")
                    
                try:
                    with open(temp_png_path, "rb") as image_file:
                        response = client.images.edit(
                            model=candidate,
                            image=image_file,
                            prompt=prompt,
                            n=n,
                            size="1024x1024",
                            quality=resolved_quality
                        )
                    successful_model = candidate
                finally:
                    if os.path.exists(temp_png_path):
                        try:
                            os.remove(temp_png_path)
                        except Exception:
                            pass
            else:
                print(f"[{candidate}] Generating image via client.images.generate with quality {resolved_quality}.")
                response = client.images.generate(
                    model=candidate,
                    prompt=prompt,
                    n=n,
                    size="1024x1024",
                    quality=resolved_quality
                )
                successful_model = candidate
            
            if response:
                break
        except Exception as oe:
            print(f"[gpt-image] Failed with model {candidate}: {oe}")
            last_err = oe
            error_msg = str(oe)
            if "billing_hard_limit_reached" in error_msg or "Billing hard limit" in error_msg:
                print("[CRITICAL] OpenAI Billing ceiling caught.")
                raise ValueError("OPENAI_BILLING_LIMIT_REACHED") from oe
            continue
    else:
        raise ValueError(f"OpenAI error (all models failed, last: {last_err})")

    saved_paths = []
    for idx, img_item in enumerate(response.data):
        if idx == 0:
            target_out = output_path
        else:
            base, ext = os.path.splitext(output_path)
            if base.endswith("_source"):
                target_out = base[:-7] + f"_variant_{idx+1}" + ext
            else:
                target_out = f"{base}_variant_{idx+1}{ext}"
        if img_item.b64_json:
            img_data = base64.b64decode(img_item.b64_json)
        elif img_item.url:
            try:
                resp = requests.get(img_item.url, timeout=15, proxies={"http": None, "https": None})
                resp.raise_for_status()
                img_data = resp.content
            except Exception:
                continue
        else:
            continue

        with open(target_out, 'wb') as handler:
            handler.write(img_data)
        if vectorize:
            local_binarize_image(target_out, target_out)
        saved_paths.append(target_out)
    return saved_paths


def stream_dalle_image_progressive(openai_key: str, prompt: str, init_image_path: str = None, model: str = None):
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {openai_key.strip()}", "Content-Type": "application/json"}
    
    selected_model = model or "gpt-image-1-mini"
    payload = {"model": selected_model, "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "low", "stream": True}
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk: yield chunk
    except Exception as e:
        print(f"[image_engine] progressive stream failed: {e}")
        yield b""


def _try_imagen3(banana_key: str, prompt: str, output_path: str, n: int = 1, vectorize: bool = False) -> list[str]:
    if not banana_key or not banana_key.strip():
        raise ValueError("Clé API Gemini/Imagen manquante.")
    from google import genai
    from google.genai import types
    
    neg_suffix = "\nABSOLUTELY NO: color, photo, 3d, rendering, drop shadow, inner shadow, gradient, shading, gray tones, realistic texture, sketch, blurry, floating parts, text, watermark, signature. Pure flat 2D graphic only."
    try:
        from ..database import SessionLocal
        from ..models import Setting
        db_s = SessionLocal()
        s = db_s.query(Setting).first()
        if s and s.prompt_imagen3_negative_suffix and s.prompt_imagen3_negative_suffix.strip():
            neg_suffix = s.prompt_imagen3_negative_suffix
        db_s.close()
    except Exception:
        pass
    
    imagen_prompt = prompt + neg_suffix
    client = genai.Client(api_key=banana_key.strip())
    try:
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=imagen_prompt,
            config=types.GenerateImagesConfig(number_of_images=n, output_mime_type='image/jpeg')
        )
    except Exception as ge:
        error_msg = str(ge)
        if "RESOURCE_EXHAUSTED" in error_msg or "credits are depleted" in error_msg:
            raise ValueError("GEMINI_BILLING_LIMIT_REACHED") from ge
        raise ValueError(f"Gemini error: {error_msg}") from ge

    if not response.generated_images:
        raise ValueError("Aucune image générée par Google Imagen 3.")

    saved_paths = []
    for idx, gen_img in enumerate(response.generated_images):
        if idx == 0:
            target_out = output_path
        else:
            base, ext = os.path.splitext(output_path)
            if base.endswith("_source"):
                target_out = base[:-7] + f"_variant_{idx+1}" + ext
            else:
                target_out = f"{base}_variant_{idx+1}{ext}"
        image_bytes = gen_img.image.image_bytes
        with open(target_out, 'wb') as handler:
            handler.write(image_bytes)
        if vectorize:
            local_binarize_image(target_out, target_out)
        saved_paths.append(target_out)
    return saved_paths


def _try_replicate(replicate_key: str, model_id: str, prompt: str, output_path: str, init_image_path: str = None):
    if not replicate_key or not replicate_key.strip():
        raise ValueError(f"Clé API Replicate manquante pour {model_id}.")
    url = f"https://api.replicate.com/v1/models/{model_id}/predictions"
    headers = {"Authorization": f"Token {replicate_key.strip()}", "Content-Type": "application/json"}
    input_data = {"prompt": prompt, "width": 1024, "height": 1024}
    
    if init_image_path and os.path.exists(init_image_path):
        with open(init_image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
        input_data["image"] = f"data:image/png;base64,{b64_img}"
            
    resp = requests.post(url, json={"input": input_data}, headers=headers, timeout=30, proxies={"http": None, "https": None})
    resp.raise_for_status()
    pred = _safe_json(resp, f"replicate/{model_id}")
    
    poll_url = f"https://api.replicate.com/v1/predictions/{pred['id']}"
    for _ in range(60):
        poll_resp = requests.get(poll_url, headers=headers, timeout=10, proxies={"http": None, "https": None})
        poll_resp.raise_for_status()
        status_data = _safe_json(poll_resp, f"replicate-poll/{model_id}")
        if status_data["status"] == "succeeded":
            output_url = status_data["output"]
            if isinstance(output_url, list): output_url = output_url[0]
            img_resp = requests.get(output_url, timeout=30, proxies={"http": None, "https": None})
            with open(output_path, "wb") as f: f.write(img_resp.content)
            return
        elif status_data["status"] == "failed":
            raise ValueError(f"Replicate prediction failed: {status_data.get('error')}")
        time.sleep(2)
    raise TimeoutError("Replicate prediction timed out.")


def _generate_with_huggingface(prompt: str, output_path: str):
    if not settings.HUGGINGFACE_API_KEY:
        raise ValueError("Missing Hugging Face API key.")
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    resp = requests.post(url, json={"inputs": prompt}, headers=headers, timeout=90)
    if resp.status_code != 200:
        raise ValueError(f"Hugging Face API failed: {resp.text}")
    with open(output_path, "wb") as f:
        f.write(resp.content)


def _try_huggingface_image(hf_key: str, model_id: str, prompt: str, output_path: str):
    url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {"Authorization": f"Bearer {hf_key.strip()}"}
    resp = requests.post(url, json={"inputs": prompt}, headers=headers, timeout=60)
    if resp.status_code != 200: raise ValueError(resp.text)
    with open(output_path, "wb") as f: f.write(resp.content)


def _generate_with_stability(prompt: str, output_path: str, api_key: str = None):
    api_key = api_key or settings.STABILITY_API_KEY
    if not api_key: raise ValueError("Missing Stability AI API key.")
    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "image/*"}
    data = {"prompt": prompt, "output_format": "png", "width": 1024, "height": 1024}
    resp = requests.post(url, headers=headers, files={"none": ""}, data=data, timeout=120, proxies={"http": None, "https": None})
    if resp.status_code == 200:
        with open(output_path, "wb") as f: f.write(resp.content)
    else:
        raise ValueError(f"Stability error {resp.status_code}: {resp.text}")


class ImageFactory:
    def __init__(self, openai_key=None, gemini_key=None, banana_key=None, replicate_key=None, openrouter_key=None, huggingface_key=None, stability_key=None):
        self.openai_key = openai_key
        self.gemini_key = gemini_key or banana_key
        self.replicate_key = replicate_key
        self.openrouter_key = openrouter_key
        self.huggingface_key = huggingface_key
        self.stability_key = stability_key

    def generate(self, provider: str, prompt: str, output_path: str, init_image_path: str = None, n: int = 1, vectorize: bool = False, quality: str = "low") -> list[str]:
        p = provider.lower().strip()
        res_paths = []
        if p.startswith("gpt-image") or p in ("openai", "dall-e-3", "dall-e-2"):
            model_name = p if p.startswith("gpt-image") else "gpt-image-1-mini"
            res_paths = _try_dalle(self.openai_key, model_name, prompt, output_path, init_image_path, n=n, vectorize=vectorize, quality=quality)
        elif p in ("imagen-3", "imagen-3-generate", "imagen-3-edit", "gemini", "google"):
            res_paths = _try_imagen3(self.gemini_key, prompt, output_path, n=n, vectorize=vectorize)
        elif p == "stable-diffusion-xl-core":
            _try_replicate(self.replicate_key, "stability-ai/sdxl", prompt, output_path, init_image_path)
            res_paths = [output_path]
        elif p == "stable-diffusion-3-pro":
            _try_replicate(self.replicate_key, "stability-ai/stable-diffusion-3", prompt, output_path, init_image_path)
            res_paths = [output_path]
        elif p == "black-forest-labs-flux-pro":
            _try_replicate(self.replicate_key, "black-forest-labs/flux-pro", prompt, output_path, init_image_path)
            res_paths = [output_path]
        elif p == "bria-2.3":
            _try_replicate(self.replicate_key, "briaai/bria-2.3", prompt, output_path, init_image_path)
            res_paths = [output_path]
        elif p == "huggingface-flux-free":
            _generate_with_huggingface(prompt, output_path)
            res_paths = [output_path]
        elif p == "pollinations":
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/p/{encoded}?model=flux&width=1024&height=1024"
            with open(output_path, "wb") as f: f.write(requests.get(url, timeout=40).content)
            res_paths = [output_path]
        elif p in ("stability", "stability-ai", "sd3"):
            _generate_with_stability(prompt, output_path, api_key=self.stability_key)
            res_paths = [output_path]
        else:
            if "/" in p:
                if self.replicate_key:
                    _try_replicate(self.replicate_key, p, prompt, output_path, init_image_path)
                    res_paths = [output_path]
                elif self.huggingface_key:
                    _try_huggingface_image(self.huggingface_key, p, prompt, output_path)
                    res_paths = [output_path]
                else:
                    raise ValueError(f"Provider non supporté: {p}")
            else:
                raise ValueError(f"Provider non supporté: {p}")

        # Unconditionally apply local_binarize_image (thresholding) to all output stencil paths
        for path in res_paths:
            if path and os.path.exists(path):
                try:
                    print(f"[ImageFactory] Applying binarize/threshold filter to: {path} (apply={apply_binarization})")
                    local_binarize_image(path, path, apply_binarization=apply_binarization)
                except Exception as be:
                    print(f"[ImageFactory] Warning: Binarization/threshold filter failed for {path}: {be}")
        return res_paths


def _generate_stencil_image_core(provider: str, banana_key: str, openai_key: str, theme: str, output_path: str, init_image_path: str = None, custom_prompt: str = None, bundle_size: int = 4, design_style: str = "classic", gemini_key: str = None, replicate_key: str = None, openrouter_key: str = None, huggingface_key: str = None, stability_key: str = None, profile_tier: str = "free", strict_fidelity: bool = True, vectorize: bool = False, n_images: int = 1, quality: str = "low", apply_binarization: bool = True):
    theme = theme.strip() if (theme and theme.strip()) else "vector design"
    
    stencil_single = "A professional 2D flat vector silhouette stencil of {theme}. Pure solid black #000000 shapes on pristine solid white background #FFFFFF, clean lines."
    stencil_multiple = "An organized flash-sheet collection grid containing exactly {bundle_size} distinct variations of: {theme}. Grid layout, disconnected by wide white spaces. Pure black #000000 shapes on pristine white #FFFFFF background."
    stencil_framed_filigree = "Generate a strictly square image. Intricate stencil silhouette art based on: {final_prompt}."
    try:
        from ..database import SessionLocal
        from ..models import Setting
        db_s = SessionLocal()
        s = db_s.query(Setting).first()
        if s:
            if s.prompt_stencil_single and s.prompt_stencil_single.strip():
                stencil_single = s.prompt_stencil_single
            if s.prompt_stencil_multiple and s.prompt_stencil_multiple.strip():
                stencil_multiple = s.prompt_stencil_multiple
            if s.prompt_stencil_framed_filigree and s.prompt_stencil_framed_filigree.strip():
                stencil_framed_filigree = s.prompt_stencil_framed_filigree
        db_s.close()
    except Exception:
        pass

    if bundle_size > 1:
        final_prompt = stencil_multiple.replace("{bundle_size}", str(bundle_size)).replace("{theme}", theme)
    else:
        final_prompt = stencil_single.replace("{theme}", theme)

    strict_prompt = stencil_framed_filigree.replace("{final_prompt}", final_prompt) if design_style == "framed_filigree" else final_prompt
    current_prompt = custom_prompt if custom_prompt else strict_prompt

    # 1. NEW STRATEGY: INJECT FREE HIGH-QUALITY IMG2IMG AT THE TOP OF THE PYRAMID ONLY IF NO SPECIFIC PROVIDER OR IF PREFERRED IS POLLINATIONS / NONE
    if init_image_path and os.path.exists(init_image_path):
        pref = provider.lower().strip() if provider else "pollinations"
        if pref in ("pollinations", ""):
            if os.getenv("TOGETHER_API_KEY"):
                try: return _try_together_ai_img2img(current_prompt, init_image_path, output_path), "together/sdxl"
                except Exception: pass
            if os.getenv("FAL_KEY"):
                try: return _try_fal_ai_img2img(current_prompt, init_image_path, output_path), "fal/flux-schnell"
                except Exception: pass
            try: return _try_pollinations_fallback(current_prompt, output_path), "pollinations"
            except Exception: pass

    # 2. LEGACY RESTORED PATHS (Recraft PRO TIER layout execution mapping)
    if profile_tier == "pro" or provider.lower().strip() == "recraft":
        if replicate_key:
            try:
                print("[image_engine] Invoking Recraft V4 vector line art API...")
                url = "https://api.replicate.com/v1/models/recraft-ai/recraft-v4/predictions"
                headers = {"Authorization": f"Token {replicate_key.strip()}", "Content-Type": "application/json"}
                resp = requests.post(url, json={"input": {"prompt": current_prompt, "style": "vector/line_art", "size": "1024x1024"}}, headers=headers, timeout=30, proxies={"http": None, "https": None})
                resp.raise_for_status()
                pred_id = resp.json()["id"]
                
                for _ in range(60):
                    p_resp = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}", headers=headers, timeout=10, proxies={"http": None, "https": None})
                    st = p_resp.json()
                    if st["status"] == "succeeded":
                        img_url = st["output"][0] if isinstance(st["output"], list) else st["output"]
                        with open(output_path, "wb") as f: f.write(requests.get(img_url, timeout=30, proxies={"http": None, "https": None}).content)
                        return [output_path], "recraft-v4"
                    time.sleep(2)
            except Exception as e:
                print(f"[image_engine] Recraft failed: {e}. Falling back...")

    # 3. DYNAMIC FALLBACK PRIORITY QUEUE MATRIX
    all_providers = ["pollinations", "huggingface-flux-free", "gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "imagen-3-generate", "imagen-3-edit", "stable-diffusion-xl-core", "stable-diffusion-3-pro", "bria-2.3", "black-forest-labs-flux-pro", "stability"]
    active_providers = ["pollinations"]
    
    if openai_key or os.getenv("OPENAI_API_KEY"):
        active_providers.extend(["gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"])
    if gemini_key or banana_key: active_providers.extend(["imagen-3-generate", "imagen-3-edit"])
    if replicate_key and replicate_key.strip(): active_providers.extend(["stable-diffusion-xl-core", "stable-diffusion-3-pro", "bria-2.3", "black-forest-labs-flux-pro"])
    if stability_key and stability_key.strip(): active_providers.append("stability")
    if huggingface_key: active_providers.append("huggingface-flux-free")

    pref = provider.lower().strip() if provider else "pollinations"
    priority_list = [pref] + [p for p in active_providers if p != pref] if pref in active_providers else active_providers

    factory = ImageFactory(openai_key=openai_key, gemini_key=gemini_key or banana_key, replicate_key=replicate_key, huggingface_key=huggingface_key, stability_key=stability_key)
    errors = []

    for p in priority_list:
        try:
            print(f"[image_engine] Attempting stencil generation via {p}...")
            saved_paths = factory.generate(p, current_prompt, output_path, init_image_path, n=n_images, vectorize=vectorize, quality=quality)
            return saved_paths, p
        except Exception as e:
            errors.append(f"{p}: {e}")

    raise RuntimeError(f"All image providers failed stencil generation: {'; '.join(errors)}")


def generate_stencil_image(provider: str, banana_key: str, openai_key: str, theme: str, output_path: str, init_image_path: str = None, custom_prompt: str = None, bundle_size: int = 4, design_style: str = "classic", gemini_key: str = None, replicate_key: str = None, openrouter_key: str = None, huggingface_key: str = None, stability_key: str = None, profile_tier: str = "free", strict_fidelity: bool = True, vectorize: bool = False, generate_real_mockup: bool = False, mockup_configs: Optional[list] = None, n_images: int = 1, quality: str = "low", mockup_provider: str = None, mockup_quality: str = "low", apply_binarization: bool = True):
    saved_paths, final_p = _generate_stencil_image_core(provider, banana_key, openai_key, theme, output_path, init_image_path, custom_prompt, bundle_size, design_style, gemini_key, replicate_key, openrouter_key, huggingface_key, stability_key, profile_tier, strict_fidelity, vectorize, n_images, quality=quality, apply_binarization=apply_binarization)
    
    result = {"provider": final_p, "prompt": theme, "status": "success", "error": None, "saved_paths": saved_paths}

    if generate_real_mockup:
        try:
            import time
            ts = int(time.time())
            creation_dir = os.path.dirname(output_path)
            configs = mockup_configs if (mockup_configs and len(mockup_configs) > 0) else [{"index": 0, "style": "default_wood"}]
            for config in configs:
                idx = config.get("index") if isinstance(config, dict) else config.index
                theme_style = config.get("style") if isinstance(config, dict) else config.style
                
                temp_bg = None
                try:
                    backdrop_bytes = generate_mockup_backdrop(theme_style, openai_key, model=mockup_provider, quality=mockup_quality)
                    temp_bg = os.path.join(creation_dir, f"temp_bg_{theme_style}_{idx}.jpg")
                    with open(temp_bg, 'wb') as f: f.write(backdrop_bytes)
                except Exception as bg_err:
                    print(f"[image_engine] AI backdrop generation failed: {bg_err}. Trying static backgrounds.")

                if not temp_bg:
                    bg_candidates = [
                        os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../assets/backgrounds/{theme_style}.jpg")),
                        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../assets/backgrounds/classic_living_room.jpg")),
                    ]
                    temp_bg = next((p for p in bg_candidates if os.path.exists(p)), None)
                    
                from .mockup_engine import composite_stencil_on_bg
                mockup_raw = os.path.join(creation_dir, f"Fichier_Import_mockup_raw_{idx+1}_{ts}.jpg")
                
                composite_stencil_on_bg(output_path, temp_bg, mockup_raw, "matte_black_metal", False)
                
                if idx == 0:
                    result["mockup_raw_path"] = mockup_raw
                    result["mockup_commercial_path"] = None

                if temp_bg and os.path.exists(temp_bg) and "temp_bg" in os.path.basename(temp_bg):
                    try: os.remove(temp_bg)
                    except Exception: pass
        except Exception as mockup_err:
            print(f"[image_engine] Premium Mockup processing failed: {mockup_err}")
            
    return result


def regenerate_stencil_image_guided(provider: str, banana_key: str, openai_key: str, theme: str, current_image_path: str, init_image_path: str, instructions: str, output_path: str, bundle_size: int = 4, gemini_key: str = None, replicate_key: str = None, openrouter_key: str = None, huggingface_key: str = None, stability_key: str = None, vectorize: bool = False, quality: str = "low", mockup_provider: str = None, mockup_quality: str = "low"):
    api_key = gemini_key or banana_key
    if not api_key: raise ValueError("Clé API Gemini manquante.")
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key.strip())
    contents = []

    def _encode_image(path: str) -> str:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode("utf-8")

    if init_image_path and os.path.exists(init_image_path):
        contents.append(types.Part.from_bytes(data=base64.b64decode(_encode_image(init_image_path)), mime_type="image/png"))
    contents.append(types.Part.from_bytes(data=base64.b64decode(_encode_image(current_image_path)), mime_type="image/png"))

    system_prompt = "You are an expert prompt engineer. Write a revised prompt in English based on the current image and modifications: " + instructions
    contents.extend([f"Original Theme: {theme}", f"Request: {instructions}"])

    response = client.models.generate_content(model="gemini-2.0-flash", contents=contents, config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.4))
    
    return generate_stencil_image(provider, banana_key, openai_key, theme, output_path, None, response.text.strip(), bundle_size, "classic", gemini_key, replicate_key, openrouter_key, huggingface_key, stability_key, "free", True, vectorize, quality=quality, mockup_provider=mockup_provider, mockup_quality=mockup_quality)


def split_multielement_image(image_path: str, output_dir: str, bundle_size: int) -> list[str]:
    """
    Precisely segments and extracts individual elements from a multi-design bundle image.
    Uses contour detection with spatial 2D grid sorting, dynamic margins, and 1024x1024 centering.
    """
    if not os.path.exists(image_path):
        return []
    try:
        import cv2
        import numpy as np
        from PIL import Image

        pil_img = Image.open(image_path).convert("RGBA")
        white_bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
        white_bg.alpha_composite(pil_img)
        gray = np.array(white_bg.convert("L"))

        # Adaptive thresholding to isolate all stencil elements
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7)
        inverted = cv2.bitwise_not(thresh)

        # Morphological closing to ensure multi-part connected elements stay grouped
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_boxes = []
        total_area = gray.shape[1] * gray.shape[0]
        min_area = int(total_area * 0.003)  # Ignore tiny noise specks < 0.3%

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                # Ignore full-image border rectangles
                if w > gray.shape[1] * 0.96 and h > gray.shape[0] * 0.96:
                    continue
                valid_boxes.append((x, y, w, h))

        if not valid_boxes:
            return [image_path]

        # 2D Spatial sorting: top-to-bottom rows, then left-to-right
        avg_h = sum(b[3] for b in valid_boxes) / len(valid_boxes)
        row_band = max(30, int(avg_h * 0.75))
        valid_boxes.sort(key=lambda b: (((b[1] + b[3] // 2) // row_band) * 10000) + b[0])

        cropped_paths = []
        os.makedirs(output_dir, exist_ok=True)

        for idx, (x, y, w, h) in enumerate(valid_boxes):
            # Dynamic generous padding (8% of dimension + 20px) to prevent clipped edges
            pad_x = max(20, int(w * 0.08))
            pad_y = max(20, int(h * 0.08))

            y1 = max(0, y - pad_y)
            y2 = min(gray.shape[0], y + h + pad_y)
            x1 = max(0, x - pad_x)
            x2 = min(gray.shape[1], x + w + pad_x)

            cropped_roi = thresh[y1:y2, x1:x2]

            # Place onto clean 1024x1024 white canvas with aspect-ratio preservation
            canvas = np.ones((1024, 1024), dtype=np.uint8) * 255
            h_r, w_r = cropped_roi.shape

            # Target inner box is 920x920 (leaving a clean 52px outer safety margin)
            target_max = 920
            scale = min(target_max / w_r, target_max / h_r)
            new_w = max(1, int(w_r * scale))
            new_h = max(1, int(h_r * scale))

            resized_roi = cv2.resize(cropped_roi, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)

            offset_y = (1024 - new_h) // 2
            offset_x = (1024 - new_w) // 2
            canvas[offset_y:offset_y + new_h, offset_x:offset_x + new_w] = resized_roi

            out_path = os.path.join(output_dir, f"element_{idx + 1}.png")
            cv2.imwrite(out_path, canvas)
            cropped_paths.append(out_path)

        print(f"[split_multielement_image] Successfully split bundle into {len(cropped_paths)} clean elements.")
        return cropped_paths
    except Exception as e:
        print(f"[split_multielement_image] Segmentation failed ({e}), returning original image.")
        return [image_path]



def generate_mockup_backdrop(theme: str, openai_key: str, custom_prompt: str = None, model: str = None, quality: str = "low") -> bytes:
    backdrop_prompt = custom_prompt.replace("{theme}", theme) if custom_prompt else f"A professional product photography of an empty interior wall mockup for theme: '{theme}'. Square frame, zero furniture elements obstructing center."
    resolved_key = (openai_key or os.getenv("OPENAI_API_KEY") or "").strip()
    
    selected_model = model or "gpt-image-1-mini"
    # Force quality to 'low' to minimize costs
    selected_quality = quality if quality in ("low", "medium", "high") else "low"
    
    candidates = [selected_model]
    # Cheapest models first in fallback chain
    for fallback in ["gpt-image-1-mini", "gpt-image-1", "gpt-image-1.5", "gpt-image-2", "dall-e-2", "dall-e-3"]:
        if fallback not in candidates:
            candidates.append(fallback)
            
    headers = {"Authorization": f"Bearer {resolved_key}", "Content-Type": "application/json"}
    
    response = None
    last_err = None
    
    for candidate in candidates:
        try:
            print(f"[mockup] generate_mockup_backdrop trying model {candidate} with quality {selected_quality}")
            res = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json={
                    "model": candidate,
                    "prompt": backdrop_prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": selected_quality
                },
                timeout=60,
                proxies={"http": None, "https": None}
            )
            if res.status_code == 200:
                response = res
                break
            else:
                try:
                    err_msg = res.json().get('error', {}).get('message', res.text)
                except Exception:
                    err_msg = res.text
                last_err = RuntimeError(f"HTTP Error {res.status_code}: {err_msg}")
        except Exception as e:
            print(f"[mockup] Backdrop generation failed with model {candidate}: {e}")
            last_err = e
            continue
            
    if not response:
        raise RuntimeError(f"Mockup backdrop generation failed (all models exhausted, last error: {last_err})")
        
    img_item = response.json().get("data", [{}])[0]
    return base64.b64decode(img_item["b64_json"]) if "b64_json" in img_item else requests.get(img_item["url"], timeout=30, proxies={"http": None, "https": None}).content

def create_real_metal_mockup(stencil_path: str, backdrop_bytes: bytes, output_mockup_path: str, style: str = "classic_living_room"):
    """
    Composites the black stencil onto the room backdrop using PIL.
    Transforms the pure black stencil into an engraved matte-black metallic piece
    with an elegant drop shadow and perspective translation for realism.
    """
    from PIL import Image, ImageOps, ImageFilter
    import io

    # 1. Load the backdrop and the stencil
    backdrop = Image.open(io.BytesIO(backdrop_bytes)).convert("RGBA")
    stencil = Image.open(stencil_path).convert("RGBA")
    
    # Configure sizing based on mockup style
    if style == "tshirt_apparel":
        target_size = (350, 350)
    elif style == "frame_poster":
        target_size = (450, 450)
    else:
        target_size = (650, 650)
        
    stencil = stencil.resize(target_size, Image.Resampling.LANCZOS)
    
    # 2. Apply 3D perspective transformation if the interior style is angled
    if style in ("angled_interior", "frame_poster"):
        import numpy as np
        
        # Map original square corners to a realistic 3D perspective slanted to the left
        w, h = target_size
        pa = [(0, 0), (w, 0), (w, h), (0, h)]
        # Slightly slanted target points
        pb = [
            (int(w * 0.15), int(h * 0.08)),  # Top-left
            (int(w * 0.86), int(h * 0.15)),  # Top-right
            (int(w * 0.83), int(h * 0.84)),  # Bottom-right
            (int(w * 0.09), int(h * 0.77))   # Bottom-left
        ]
        
        def find_coeffs(pa, pb):
            matrix = []
            for p1, p2 in zip(pa, pb):
                matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
                matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
            A = np.array(matrix)
            B = np.array(pb).reshape(8)
            res = np.linalg.solve(A, B)
            return res
            
        coeffs = find_coeffs(pb, pa)  # Maps target to source
        stencil = stencil.transform(target_size, Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    
    # 3. Isolate the black artwork mask (supporting both transparent and white background stencils)
    import numpy as np
    white_bg = Image.new("RGBA", stencil.size, (255, 255, 255, 255))
    white_bg.alpha_composite(stencil)
    gray = white_bg.convert("L")
    alpha = stencil.split()[3]
    
    gray_np = np.array(gray)
    alpha_np = np.array(alpha)
    
    # Mask is 255 (opaque/keep) where the image is dark (gray value < 200) and not transparent (alpha > 50)
    mask_np = np.where((gray_np < 200) & (alpha_np > 50), 255, 0).astype(np.uint8)
    artwork_mask = Image.fromarray(mask_np, "L")
    
    # 4. Create the Matte-Black Metal Layer texture composition
    metal_color = Image.new("RGBA", target_size, (22, 22, 22, 255))
    
    # 5. Generate a Realistic Bevel/Emboss Drop Shadow
    shadow_mask = artwork_mask.filter(ImageFilter.GaussianBlur(radius=12))
    shadow = Image.new("RGBA", target_size, (0, 0, 0, 160))
    
    # Center position calculations on the master interior backdrop wall canvas
    offset_x = (backdrop.width - target_size[0]) // 2
    offset_y = (backdrop.height - target_size[1]) // 2
    
    if style == "tshirt_apparel":
        offset_y -= 40  # Place slightly higher on chest area
        
    # Paste shadow mask matrix onto backdrop first (offsetting slightly down and right for deep visual parallax)
    shadow_layer = Image.new("RGBA", backdrop.size, (0, 0, 0, 0))
    shadow_layer.paste(shadow, (offset_x + 4, offset_y + 8), mask=shadow_mask)
    backdrop.alpha_composite(shadow_layer)
    
    # 6. Composite the metal layer surface pattern onto the canvas layout
    artwork_final = Image.new("RGBA", target_size)
    artwork_final.paste(metal_color, (0, 0), mask=artwork_mask)
    
    backdrop.alpha_composite(artwork_final, dest=(offset_x, offset_y))
    
    # Save the compressed high-end artifact back to the filesystem directory
    backdrop.convert("RGB").save(output_mockup_path, "JPEG", quality=95)
    print(f"[MOCKUP SUCCESS] Premium metallic artwork mockup saved successfully to {output_mockup_path}")



def _describe_image_with_vision(openai_key: str, image_path: str) -> str:
    """
    Uses OpenAI Vision parameters to output the descriptive subject string 
    extracted from the initial user reference upload template layout.
    """
    if not os.path.exists(image_path):
        return ""
    try:
        ext = os.path.splitext(image_path)[1].lower().strip(".")
        mime_type = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/png")
        
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {openai_key.strip()}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Describe the core subject, exact posture, layout, and shapes of this image in English for a silhouette stencil maker. Output ONLY the raw description, no prose."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
            proxies={"http": None, "https": None}
        )

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI Chat API HTTP Error ({response.status_code})")

        description = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[VISION SUCCESS] Generated image description: {description}")
        return description
    except Exception as e:
        print(f"[VISION ERROR] Vision description failed: {e}")
        return ""
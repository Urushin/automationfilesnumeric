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


def execute_inpainting(image_path: str, mask_path: str, prompt: str, output_path: str, openai_key: str = None):
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

        response = client.images.edit(
            model="gpt-image-2",
            image=("image.png", image_buffer, "image/png"),
            mask=("mask.png", mask_buffer, "image/png"),
            prompt=final_prompt,
            n=1,
            size="1024x1024"
        )
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
        print(f"[gpt-image-2 SUCCESS] Inpainting applied and written to {output_path}")
    finally:
        if mask_path and os.path.exists(mask_path):
            try:
                os.remove(mask_path)
            except Exception:
                pass


def local_binarize_image(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
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
            if gray_val < 240 and alpha_val > 0:
                new_data.append((0, 0, 0, alpha_val))
            else:
                new_data.append((255, 255, 255, 0))
                
        img.putdata(new_data)
        img.save(output_path, "PNG")
        print(f"[local_binarize_image] Saved transparent PNG via PIL: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to binarize image via Pillow: {e}")


def local_binarize_opaque(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
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
            if g_val < 240:
                new_data.append((0, 0, 0, 255))
            else:
                new_data.append((255, 255, 255, 255))
                
        out_img = Image.new("RGBA", img.size)
        out_img.putdata(new_data)
        out_img.save(output_path, "PNG")
        print(f"[local_binarize_opaque] Saved opaque PNG: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to binarize opaque image: {e}")


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


def _try_dalle(openai_key: str, model: str, prompt: str, output_path: str, init_image_path: str = None, n: int = 1, vectorize: bool = False) -> list[str]:
    if not openai_key or not openai_key.strip():
        raise ValueError(f"Clé API OpenAI manquante pour {model}.")
    client = OpenAI(api_key=openai_key.strip(), base_url="https://api.openai.com/v1")
    try:
        if init_image_path and os.path.exists(init_image_path):
            print(f"[gpt-image-2] Structural layout guidance detected via client.images.edit.")
            with Image.open(init_image_path) as img:
                img_rgba = img.convert("RGBA")
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_f:
                    temp_png_path = tmp_f.name
                img_rgba.save(temp_png_path, "PNG")
                
            try:
                with open(temp_png_path, "rb") as image_file:
                    response = client.images.edit(
                        model="gpt-image-2",
                        image=image_file,
                        prompt=prompt,
                        n=n,
                        size="1024x1024"
                    )
            finally:
                if os.path.exists(temp_png_path):
                    try:
                        os.remove(temp_png_path)
                    except Exception:
                        pass
        else:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=n,
                size="1024x1024",
                quality="auto"
            )
    except Exception as oe:
        error_msg = str(oe)
        if "billing_hard_limit_reached" in error_msg or "Billing hard limit" in error_msg:
            print("[CRITICAL] OpenAI Billing ceiling caught.")
            raise ValueError("OPENAI_BILLING_LIMIT_REACHED") from oe
        raise ValueError(f"OpenAI error: {error_msg}") from oe

    saved_paths = []
    for idx, img_item in enumerate(response.data):
        target_out = output_path if idx == 0 else output_path.replace("_source.png", f"_variant_{idx+1}.png").replace(".png", f"_variant_{idx+1}.png")
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


def stream_dalle_image_progressive(openai_key: str, prompt: str, init_image_path: str = None):
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {openai_key.strip()}", "Content-Type": "application/json"}
    payload = {"model": "gpt-image-2", "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "auto", "stream": True}
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
    
    imagen_prompt = prompt + "\nABSOLUTELY NO: color, photo, 3d, rendering, drop shadow, inner shadow, gradient, shading, gray tones, realistic texture, sketch, blurry, floating parts, text, watermark, signature. Pure flat 2D graphic only."
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
        target_out = output_path if idx == 0 else output_path.replace("_source.png", f"_variant_{idx+1}.png").replace(".png", f"_variant_{idx+1}.png")
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

    def generate(self, provider: str, prompt: str, output_path: str, init_image_path: str = None, n: int = 1, vectorize: bool = False) -> list[str]:
        p = provider.lower().strip()
        if p in ("gpt-image-2", "openai"):
            return _try_dalle(self.openai_key, "gpt-image-2", prompt, output_path, init_image_path, n=n, vectorize=vectorize)
        elif p in ("imagen-3", "imagen-3-generate", "imagen-3-edit", "gemini", "google"):
            return _try_imagen3(self.gemini_key, prompt, output_path, n=n, vectorize=vectorize)
        elif p == "stable-diffusion-xl-core":
            _try_replicate(self.replicate_key, "stability-ai/sdxl", prompt, output_path, init_image_path)
            return [output_path]
        elif p == "stable-diffusion-3-pro":
            _try_replicate(self.replicate_key, "stability-ai/stable-diffusion-3", prompt, output_path, init_image_path)
            return [output_path]
        elif p == "black-forest-labs-flux-pro":
            _try_replicate(self.replicate_key, "black-forest-labs/flux-pro", prompt, output_path, init_image_path)
            return [output_path]
        elif p == "bria-2.3":
            _try_replicate(self.replicate_key, "briaai/bria-2.3", prompt, output_path, init_image_path)
            return [output_path]
        elif p == "huggingface-flux-free":
            _generate_with_huggingface(prompt, output_path)
            return [output_path]
        elif p == "pollinations":
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/p/{encoded}?model=flux&width=1024&height=1024"
            with open(output_path, "wb") as f: f.write(requests.get(url, timeout=40).content)
            return [output_path]
        elif p in ("stability", "stability-ai", "sd3"):
            _generate_with_stability(prompt, output_path, api_key=self.stability_key)
            return [output_path]
        else:
            if "/" in p:
                if self.replicate_key:
                    _try_replicate(self.replicate_key, p, prompt, output_path, init_image_path)
                    return [output_path]
                elif self.huggingface_key:
                    _try_huggingface_image(self.huggingface_key, p, prompt, output_path)
                    return [output_path]
            raise ValueError(f"Provider non supporté: {p}")


def _generate_stencil_image_core(provider: str, banana_key: str, openai_key: str, theme: str, output_path: str, init_image_path: str = None, custom_prompt: str = None, bundle_size: int = 4, design_style: str = "classic", gemini_key: str = None, replicate_key: str = None, openrouter_key: str = None, huggingface_key: str = None, stability_key: str = None, profile_tier: str = "free", strict_fidelity: bool = True, vectorize: bool = False, n_images: int = 1):
    theme = theme.strip() if (theme and theme.strip()) else "vector design"
    
    if bundle_size > 1:
        final_prompt = f"An organized flash-sheet collection grid containing exactly {bundle_size} distinct variations of: {theme}. Grid layout, disconnected by wide white spaces. Pure black #000000 shapes on pristine white #FFFFFF background."
    else:
        final_prompt = f"A professional 2D flat vector silhouette stencil of {theme}. Pure solid black #000000 shapes on pristine solid white background #FFFFFF, clean lines."

    strict_prompt = f"Generate a strictly square image. Intricate stencil silhouette art based on: {final_prompt}." if design_style == "framed_filigree" else final_prompt
    current_prompt = custom_prompt if custom_prompt else strict_prompt

    # 1. NEW STRATEGY: INJECT FREE HIGH-QUALITY IMG2IMG AT THE TOP OF THE PYRAMID
    if init_image_path and os.path.exists(init_image_path):
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
    all_providers = ["pollinations", "huggingface-flux-free", "gpt-image-2", "imagen-3-generate", "imagen-3-edit", "stable-diffusion-xl-core", "stable-diffusion-3-pro", "bria-2.3", "black-forest-labs-flux-pro", "stability"]
    active_providers = ["pollinations"]
    
    if openai_key or os.getenv("OPENAI_API_KEY"): active_providers.append("gpt-image-2")
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
            saved_paths = factory.generate(p, current_prompt, output_path, init_image_path, n=n_images, vectorize=vectorize)
            return saved_paths, p
        except Exception as e:
            errors.append(f"{p}: {e}")

    raise RuntimeError(f"All image providers failed stencil generation: {'; '.join(errors)}")


def generate_stencil_image(provider: str, banana_key: str, openai_key: str, theme: str, output_path: str, init_image_path: str = None, custom_prompt: str = None, bundle_size: int = 4, design_style: str = "classic", gemini_key: str = None, replicate_key: str = None, openrouter_key: str = None, huggingface_key: str = None, stability_key: str = None, profile_tier: str = "free", strict_fidelity: bool = True, vectorize: bool = False, generate_real_mockup: bool = False, mockup_configs: Optional[list] = None, n_images: int = 1):
    saved_paths, final_p = _generate_stencil_image_core(provider, banana_key, openai_key, theme, output_path, init_image_path, custom_prompt, bundle_size, design_style, gemini_key, replicate_key, openrouter_key, huggingface_key, stability_key, profile_tier, strict_fidelity, vectorize, n_images)
    
    result = {"provider": final_p, "prompt": theme, "status": "success", "error": None, "saved_paths": saved_paths}

    if generate_real_mockup:
        try:
            configs = mockup_configs if (mockup_configs and len(mockup_configs) > 0) else [{"index": 0, "style": "default_wood"}]
            for config in configs:
                idx = config.get("index") if isinstance(config, dict) else config.index
                theme_style = config.get("style") if isinstance(config, dict) else config.style
                
                backdrop_bytes = generate_mockup_backdrop(theme_style, openai_key)
                temp_bg = output_path.replace("_source.png", f"_temp_bg_{idx}.jpg")
                with open(temp_bg, 'wb') as f: f.write(backdrop_bytes)
                    
                from .mockup_engine import composite_stencil_on_bg
                mockup_raw = output_path.replace("_source.png", f"_mockup_raw_{idx}.jpg")
                mockup_comm = output_path.replace("_source.png", f"_mockup_commercial_{idx}.jpg")
                
                composite_stencil_on_bg(output_path, temp_bg, mockup_raw, "matte_black_metal", False)
                composite_stencil_on_bg(output_path, temp_bg, mockup_comm, "matte_black_metal", True)
                
                if idx == 0:
                    result["mockup_raw_path"] = mockup_raw
                    result["mockup_commercial_path"] = mockup_comm
                if os.path.exists(temp_bg): os.remove(temp_bg)
        except Exception as mockup_err:
            print(f"[image_engine] Premium Mockup processing failed: {mockup_err}")
            
    return result


def regenerate_stencil_image_guided(provider: str, banana_key: str, openai_key: str, theme: str, current_image_path: str, init_image_path: str, instructions: str, output_path: str, bundle_size: int = 4, gemini_key: str = None, replicate_key: str = None, openrouter_key: str = None, huggingface_key: str = None, stability_key: str = None, vectorize: bool = False):
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
    
    return generate_stencil_image(provider, banana_key, openai_key, theme, output_path, None, response.text.strip(), bundle_size, "classic", gemini_key, replicate_key, openrouter_key, huggingface_key, stability_key, "free", True, vectorize)


def split_multielement_image(image_path: str, output_dir: str, bundle_size: int) -> list[str]:
    if not os.path.exists(image_path): return []
    try:
        import cv2
        import numpy as np
        pil_img = Image.open(image_path).convert("RGBA")
        white_bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
        white_bg.alpha_composite(pil_img)
        gray = np.array(white_bg.convert("L"))
        
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(cv2.bitwise_not(thresh), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_boxes = []
        min_area = int(gray.shape[1] * gray.shape[0] * 0.005)
        for cnt in contours:
            if cv2.contourArea(cnt) > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > gray.shape[1] * 0.98 and h > gray.shape[0] * 0.98: continue
                valid_boxes.append((x, y, w, h))

        if not valid_boxes: return [image_path]
        valid_boxes.sort(key=lambda b: b[0])
        cropped_paths = []

        for idx, (x, y, w, h) in enumerate(valid_boxes):
            cropped_roi = thresh[max(0, y-20):min(gray.shape[0], y+h+20), max(0, x-20):min(gray.shape[1], x+w+20)]
            canvas = np.ones((1024, 1024), dtype=np.uint8) * 255
            h_r, w_r = cropped_roi.shape
            if h_r > 1024 or w_r > 1024:
                sc = min(1024/w_r, 1024/h_r)
                cropped_roi = cv2.resize(cropped_roi, (int(w_r*sc), int(h_r*sc)), interpolation=cv2.INTER_AREA)
                h_r, w_r = cropped_roi.shape
            canvas[(1024-h_r)//2:(1024-h_r)//2+h_r, (1024-w_r)//2:(1024-w_r)//2+w_r] = cropped_roi
            out_path = os.path.join(output_dir, f"element_{idx+1}.png")
            cv2.imwrite(out_path, canvas)
            cropped_paths.append(out_path)
        return cropped_paths
    except Exception:
        return [image_path]


def generate_mockup_backdrop(theme: str, openai_key: str, custom_prompt: str = None) -> bytes:
    backdrop_prompt = custom_prompt.replace("{theme}", theme) if custom_prompt else f"A professional product photography of an empty interior wall mockup for theme: '{theme}'. Square frame, zero furniture elements obstructing center."
    resolved_key = (openai_key or os.getenv("OPENAI_API_KEY") or "").strip()
    
    headers = {"Authorization": f"Bearer {resolved_key}", "Content-Type": "application/json"}
    response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json={"model": "gpt-image-2", "prompt": backdrop_prompt, "n": 1, "size": "1024x1024"}, timeout=60, proxies={"http": None, "https": None})
    response.raise_for_status()
    img_item = response.json().get("data", [{}])[0]
    return base64.b64decode(img_item["b64_json"]) if "b64_json" in img_item else requests.get(img_item["url"], timeout=30, proxies={"http": None, "https": None}).content

def create_real_metal_mockup(stencil_path: str, backdrop_bytes: bytes, output_mockup_path: str):
    """
    Composites the black stencil onto the room backdrop using PIL.
    Transforms the pure black stencil into an engraved matte-black metallic piece
    with an elegant drop shadow for realism.
    """
    from PIL import Image, ImageOps, ImageFilter
    import io

    # 1. Load the backdrop and the stencil
    backdrop = Image.open(io.BytesIO(backdrop_bytes)).convert("RGBA")
    stencil = Image.open(stencil_path).convert("RGBA")
    
    # Ensure stencil scales nicely to fit on the wall wall art space (650x650)
    target_size = (650, 650)
    stencil = stencil.resize(target_size, Image.Resampling.LANCZOS)
    
    # 2. Isolate the black artwork mask
    gray_stencil = stencil.convert("L")
    artwork_mask = ImageOps.invert(gray_stencil).point(lambda x: 255 if x > 50 else 0)
    
    # 3. Create the Matte-Black Metal Layer texture composition
    metal_color = Image.new("RGBA", target_size, (22, 22, 22, 255))
    
    # 4. Generate a Realistic Bevel/Emboss Drop Shadow
    shadow_mask = artwork_mask.filter(ImageFilter.GaussianBlur(radius=12))
    shadow = Image.new("RGBA", target_size, (0, 0, 0, 160))
    
    # Center position calculations on the master interior backdrop wall canvas
    offset_x = (backdrop.width - target_size[0]) // 2
    offset_y = (backdrop.height - target_size[1]) // 2
    
    # Paste shadow mask matrix onto backdrop first (offsetting slightly down and right for deep visual parallax)
    shadow_layer = Image.new("RGBA", backdrop.size, (0, 0, 0, 0))
    shadow_layer.paste(shadow, (offset_x + 4, offset_y + 8), mask=shadow_mask)
    backdrop.alpha_composite(shadow_layer)
    
    # 5. Composite the metal layer surface pattern onto the canvas layout
    artwork_final = Image.new("RGBA", target_size)
    artwork_final.paste(metal_color, (0, 0), mask=artwork_mask)
    
    backdrop.alpha_composite(artwork_final, dest=(offset_x, offset_y))
    
    # Save the compressed high-end artifact back to the filesystem directory
    backdrop.convert("RGB").save(output_mockup_path, "JPEG", quality=95)
    print(f"[MOCKUP SUCCESS] Premium metallic artwork mockup saved successfully to {output_mockup_path}")



def local_binarize_image(input_path: str, output_path: str):
    """
    Converts an uploaded user image (possibly RGBA with transparent background)
    into a crisp black-on-transparent PNG, preserving fine white separation lines.
    Using Pillow instead of OpenCV to avoid OS-level alpha channel inconsistencies.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")

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
            if gray_val < 240 and alpha_val > 0:
                new_data.append((0, 0, 0, alpha_val))
            else:
                new_data.append((255, 255, 255, 0))
                
        img.putdata(new_data)
        img.save(output_path, "PNG")
        print(f"[local_binarize_image] Binarized and saved transparent PNG via PIL: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to binarize image via Pillow: {e}")


def local_binarize_opaque(input_path: str, output_path: str):
    """
    Converts an image into a crisp black-on-white PNG (opaque, NO transparency).
    White background (#FFFFFF, alpha=255) and black shapes (#000000, alpha=255).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
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
            if g_val < 240:
                new_data.append((0, 0, 0, 255))
            else:
                new_data.append((255, 255, 255, 255))
                
        out_img = Image.new("RGBA", img.size)
        out_img.putdata(new_data)
        out_img.save(output_path, "PNG")
        print(f"[local_binarize_opaque] Binarized and saved opaque PNG: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to binarize opaque image: {e}")


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
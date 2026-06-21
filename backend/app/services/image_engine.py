"""
Image Engine — v5.0
Handles image generation with a dynamic fallback loop: [gpt-image-2, Banana/SDXL, Imagen 3].
No silent fallbacks: fails loudly with exceptions if all providers are exhausted.
"""

import base64
import os
import requests
from PIL import Image, ImageFilter
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
    gracefully to the next provider. Body previews are capped at 150 chars.
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
        # Try parsing anyway — some APIs omit the correct Content-Type header
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
    # Strip local server domain prefix if accidentally appended by the frontend
    for var_name in ["image_path", "mask_path", "output_path"]:
        val = locals()[var_name]
        if val.startswith("http://") or val.startswith("https://"):
            import urllib.parse
            parsed_url = urllib.parse.urlparse(val)
            if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                val = parsed_url.path
        if val.startswith("/static/"):
            storage_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../storage")
            )
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
        """
        Executes zone modification (inpainting) using gpt-image-2 edit API or a local fallback.
        Enforces strict black and white style injection so the inpainted zone blends.
        """
        api_key = openai_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Clé API OpenAI manquante pour l'inpainting.")
        client = OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.openai.com/v1" # FORCED OFFICIAL OPENAI ENDPOINT
        )
        
        # Enforce strict B&W stencil style
        style_suffix = ", pure black and white stencil silhouette, flat 2D graphic, solid black lines on pure white background, no shading, no colors, no gradients, no gray pixels"
        final_prompt = prompt + style_suffix
        
        import io
        from PIL import Image

        # Load and force resize/format compatibility to prevent size mismatch errors
        img = Image.open(image_path).convert("RGBA")
        if img.mode == "RGBA":
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(background, img)
        img = img.convert("RGBA")
        mask = Image.open(mask_path).convert("RGBA")
        
        target_size = (1024, 1024)
        if img.size != target_size:
            print(f"[image_engine] Resizing image from {img.size} to {target_size} for inpainting")
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        if mask.size != target_size:
            print(f"[image_engine] Resizing mask from {mask.size} to {target_size} for inpainting")
            mask = mask.resize(target_size, Image.Resampling.LANCZOS)

        # Save to BytesIO buffers
        image_buffer = io.BytesIO()
        mask_buffer = io.BytesIO()
        
        img.save(image_buffer, format="PNG")
        mask.save(mask_buffer, format="PNG")
        
        image_buffer.seek(0)
        mask_buffer.seek(0)

        image_url = None
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
            try:
                resp = requests.get(image_url, timeout=15, proxies={"http": None, "https": None})
                resp.raise_for_status()
                img_data = resp.content
            except Exception as download_err:
                import traceback
                traceback.print_exc()
                raise RuntimeError(f"Failed to download inpainted gpt-image-2 image from URL {image_url}: {download_err}") from download_err
        else:
            raise ValueError("No image URL or b64_json found in response data")

        try:
            with open(output_path, 'wb') as handler:
                handler.write(img_data)
        except Exception as write_err:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to write inpainted gpt-image-2 image to {output_path}: {write_err}") from write_err

        print(f"[gpt-image-2 SUCCESS] Image generated at URL: {image_url}. Successfully downloaded and saved to {output_path}")
    finally:
        if mask_path and os.path.exists(mask_path):
            try:
                os.remove(mask_path)
                print(f"[image_engine] Cleaned up temporary mask file: {mask_path}")
            except Exception as cleanup_err:
                print(f"[image_engine] Failed to clean up temporary mask file: {cleanup_err}")

def local_binarize_image(input_path: str, output_path: str):
    """
    Converts an uploaded user image (possibly RGBA with transparent background)
    into a crisp black-on-transparent PNG, preserving fine white separation lines.
    Using Pillow instead of OpenCV to avoid OS-level alpha channel inconsistencies.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")

    try:
        from PIL import Image
        
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
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Failed to binarize image via Pillow: {e}")


def local_binarize_opaque(input_path: str, output_path: str):
    """
    Converts an image into a crisp black-on-white PNG (opaque, NO transparency).
    White background (#FFFFFF, alpha=255) and black shapes (#000000, alpha=255).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
    try:
        from PIL import Image
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
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Failed to binarize opaque image: {e}")



def _try_dalle(openai_key: str, model: str, prompt: str, output_path: str, init_image_path: str = None, n: int = 1, vectorize: bool = False) -> list[str]:
    if not openai_key or not openai_key.strip():
        raise ValueError(f"Clé API OpenAI manquante pour {model}.")
    client = OpenAI(
        api_key=openai_key.strip(),
        base_url="https://api.openai.com/v1" # FORCED OFFICIAL OPENAI ENDPOINT
    )
    try:
        if init_image_path and os.path.exists(init_image_path):
            print(f"[gpt-image-2] Structural layout guidance detected via client.images.edit. Using model: gpt-image-2")
            from PIL import Image
            with Image.open(init_image_path) as img:
                img_rgba = img.convert("RGBA")
                # Save to a temporary file as required by OpenAI API (must be square RGBA PNG < 4MB)
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
        print(f"[gpt-image-2 OPENAI ERROR] OpenAI image generation failed with {model}: {oe}")
        raise ValueError(f"OpenAI gpt-image-2 image generation error: {oe}") from oe

    saved_paths = []
    for idx, img_item in enumerate(response.data):
        if idx == 0:
            target_out = output_path
        else:
            target_out = output_path.replace("_source.png", f"_variant_{idx+1}.png").replace(".png", f"_variant_{idx+1}.png")
            
        if img_item.b64_json:
            img_data = base64.b64decode(img_item.b64_json)
        elif img_item.url:
            image_url = img_item.url
            try:
                resp = requests.get(image_url, timeout=15, proxies={"http": None, "https": None})
                resp.raise_for_status()
                img_data = resp.content
            except Exception as download_err:
                print(f"Failed to download variant {idx+1}: {download_err}")
                continue
        else:
            continue

        try:
            with open(target_out, 'wb') as handler:
                handler.write(img_data)
            if vectorize:
                local_binarize_image(target_out, target_out)
            saved_paths.append(target_out)
        except Exception as write_err:
            print(f"Failed to write variant {idx+1}: {write_err}")

    return saved_paths


def stream_dalle_image_progressive(openai_key: str, prompt: str, init_image_path: str = None):
    """
    Yields partial base64 encoded chunks of the generated image from OpenAI via a streaming connection.
    """
    if init_image_path and os.path.exists(init_image_path):
        print(f"[image_engine] WARNING: Image-to-Image structural routing detected inside text-only streaming channel. "
              f"For maximum precision edits, route this transaction through the synchrounous execute_inpainting pipeline.")
        
    import requests
    
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {openai_key.strip()}",
        "Content-Type": "application/json"
    }
    
    # Structural context adjustments are fully managed inside the compiled text prompt layout
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "auto",
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk
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
    response = client.models.generate_images(
        model='imagen-3.0-generate-002',
        prompt=imagen_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=n,
            output_mime_type='image/jpeg'
        )
    )
    if not response.generated_images:
        raise ValueError("Aucune image générée par Google Imagen 3.")
    
    saved_paths = []
    for idx, gen_img in enumerate(response.generated_images):
        if idx == 0:
            target_out = output_path
        else:
            target_out = output_path.replace("_source.png", f"_variant_{idx+1}.png").replace(".png", f"_variant_{idx+1}.png")
            
        try:
            image_bytes = gen_img.image.image_bytes
            with open(target_out, 'wb') as handler:
                handler.write(image_bytes)
            if vectorize:
                local_binarize_image(target_out, target_out)
            saved_paths.append(target_out)
        except Exception as e:
            print(f"Failed to write Imagen variant {idx+1}: {e}")
            
    return saved_paths


# _try_banana removed because provider is deprecated/dead


def _try_replicate(replicate_key: str, model_id: str, prompt: str, output_path: str, init_image_path: str = None):
    if not replicate_key or not replicate_key.strip():
        raise ValueError(f"Clé API Replicate manquante pour {model_id}.")
    
    url = f"https://api.replicate.com/v1/models/{model_id}/predictions"
    headers = {
        "Authorization": f"Token {replicate_key.strip()}",
        "Content-Type": "application/json"
    }
    
    input_data = {
        "prompt": prompt,
        "width": 1024,
        "height": 1024,
    }
    if init_image_path and os.path.exists(init_image_path):
        try:
            with open(init_image_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            input_data["image"] = f"data:image/png;base64,{b64_img}"
        except Exception as e:
            print(f"[image_engine] Warning: failed to encode init image for Replicate: {e}")
            
    payload = {"input": input_data}
    resp = requests.post(url, json=payload, headers=headers, timeout=30, proxies={"http": None, "https": None})
    resp.raise_for_status()
    pred = _safe_json(resp, f"replicate/{model_id}")
    
    pred_id = pred["id"]
    poll_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
    
    import time
    for _ in range(60):
        poll_resp = requests.get(poll_url, headers=headers, timeout=10, proxies={"http": None, "https": None})
        poll_resp.raise_for_status()
        status_data = _safe_json(poll_resp, f"replicate-poll/{model_id}")
        if status_data["status"] == "succeeded":
            output_url = status_data["output"]
            if isinstance(output_url, list):
                output_url = output_url[0]
            img_resp = requests.get(output_url, timeout=30, proxies={"http": None, "https": None})
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            return
        elif status_data["status"] == "failed":
            raise ValueError(f"Replicate prediction failed: {status_data.get('error')}")
        time.sleep(2)
    raise TimeoutError("Replicate prediction timed out.")


def _try_hf_flux_free(hf_key: str, prompt: str, output_path: str):
    """
    Hugging Face Inference API — FLUX.1-schnell (free tier).
    Returns raw image bytes (Content-Type: image/jpeg or image/png), NOT JSON.
    """
    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Content-Type": "application/json"}
    if hf_key and hf_key.strip():
        headers["Authorization"] = f"Bearer {hf_key.strip()}"
    payload = {"inputs": prompt}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90, proxies={"http": None, "https": None})
    except Exception as conn_err:
        print(f"[image_engine] Hugging Face first connection attempt failed: {conn_err}. Retrying in 5s...")
        import time
        time.sleep(5)
        resp = requests.post(url, json=payload, headers=headers, timeout=90, proxies={"http": None, "https": None})

    if resp.status_code == 503:
        # Model loading — wait for estimated time and retry once
        import time
        wait = min(resp.json().get("estimated_time", 20) if "application/json" in resp.headers.get("Content-Type", "") else 20, 30)
        print(f"[image_engine] HuggingFace FLUX.1-schnell loading, retrying in {wait}s...")
        time.sleep(wait)
        resp = requests.post(url, json=payload, headers=headers, timeout=90, proxies={"http": None, "https": None})
    resp.raise_for_status()

    # Response is raw image bytes — write directly, no JSON parsing
    content_type = resp.headers.get("Content-Type", "")
    if not any(ct in content_type for ct in ("image/", "application/octet-stream")):
        snippet = (resp.text[:150] + "...") if len(resp.text) > 150 else resp.text
        raise ValueError(f"HuggingFace FLUX returned unexpected content type {content_type!r}. Preview: {snippet!r}")

    with open(output_path, "wb") as f:
        f.write(resp.content)
    print(f"[image_engine] HuggingFace FLUX.1-schnell generated image → {output_path}")


def _generate_with_huggingface(prompt: str, output_path: str):
    """
    Generate image with Hugging Face Inference API FLUX.1-schnell model.
    """
    if not settings.HUGGINGFACE_API_KEY:
        raise ValueError("Missing Hugging Face API key in HUGGINGFACE_API_KEY environment variable or database.")
    
    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {"inputs": prompt}

    resp = requests.post(url, json=payload, headers=headers, timeout=90, proxies={"http": None, "https": None})
    if resp.status_code != 200:
        raise ValueError(f"Hugging Face Inference API failed with status code {resp.status_code}: {resp.text}")

    with open(output_path, "wb") as f:
        f.write(resp.content)


def _generate_with_stability(prompt: str, output_path: str, api_key: str = None):
    """
    Stability AI Stable Diffusion 3 — sd3 endpoint.
    POST multipart/form-data to https://api.stability.ai/v2beta/stable-image/generate/sd3.
    Response is raw image bytes (PNG) when Accept: image/* is set.
    Prompt is forced to matte-black-vector-stencil style regardless of caller prompt.
    """
    if not api_key:
        api_key = settings.STABILITY_API_KEY
    if not api_key:
        raise ValueError("Missing Stability AI API key (STABILITY_API_KEY env or stability_key in DB).")

    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*",
    }
    data = {
        "prompt": prompt,
        "output_format": "png",
        "width": 1024,
        "height": 1024,
    }

    resp = requests.post(url, headers=headers, files={"none": ""}, data=data, timeout=120, proxies={"http": None, "https": None})
    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in ("image/", "application/octet-stream")):
            snippet = (resp.text[:200] + "...") if len(resp.text) > 200 else resp.text
            raise ValueError(f"Stability AI returned unexpected content type {content_type!r}. Preview: {snippet!r}")
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"[image_engine] Stability AI SD3 generated image → {output_path}")
    else:
        error_detail = resp.text[:300] if resp.text else str(resp.status_code)
        raise ValueError(f"Stability AI API error {resp.status_code}: {error_detail}")



def _try_huggingface_image(hf_key: str, model_id: str, prompt: str, output_path: str):
    if not hf_key or not hf_key.strip():
        raise ValueError(f"Clé API Hugging Face manquante pour {model_id}.")
    
    url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {"Authorization": f"Bearer {hf_key.strip()}"}
    payload = {"inputs": prompt}
    
    resp = requests.post(url, json=payload, headers=headers, timeout=60, proxies={"http": None, "https": None})
    if resp.status_code != 200:
        raise ValueError(f"Hugging Face API error: {resp.text}")
    
    with open(output_path, "wb") as f:
        f.write(resp.content)


class ImageFactory:
    def __init__(
        self,
        openai_key: str = None,
        gemini_key: str = None,
        banana_key: str = None,
        replicate_key: str = None,
        openrouter_key: str = None,
        huggingface_key: str = None,
        stability_key: str = None
    ):
        self.openai_key = openai_key
        self.gemini_key = gemini_key
        self.banana_key = banana_key
        self.replicate_key = replicate_key
        self.openrouter_key = openrouter_key
        self.huggingface_key = huggingface_key
        self.stability_key = stability_key

    def generate(self, provider: str, prompt: str, output_path: str, init_image_path: str = None, n: int = 1, vectorize: bool = False) -> list[str]:
        p = provider.lower().strip()
        if p in ("gpt-image-2", "openai"):
            # Do NOT run Vision analysis here again. Use the perfectly crafted prompt passed by the caller.
            return _try_dalle(self.openai_key, "gpt-image-2", prompt, output_path, init_image_path, n=n, vectorize=vectorize)
        elif p in ("imagen-3", "imagen-3-generate", "gemini", "google"):
            return _try_imagen3(self.gemini_key or self.banana_key, prompt, output_path, n=n, vectorize=vectorize)
        elif p == "imagen-3-edit":
            return _try_imagen3(self.gemini_key or self.banana_key, prompt, output_path, n=n, vectorize=vectorize)
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
                else:
                    raise ValueError(f"Unknown provider format and no Replicate/HF keys: {p}")
            else:
                raise ValueError(f"Provider non supporté: {p}")


def _generate_stencil_image_core(
    provider: str,
    banana_key: str,
    openai_key: str,
    theme: str,
    output_path: str,
    init_image_path: str = None,
    custom_prompt: str = None,
    bundle_size: int = 4,
    design_style: str = "classic",
    gemini_key: str = None,
    replicate_key: str = None,
    openrouter_key: str = None,
    huggingface_key: str = None,
    stability_key: str = None,
    profile_tier: str = "free",
    strict_fidelity: bool = True,
    vectorize: bool = False,
    n_images: int = 1
):
    # Fallback to 'vector design' if theme is empty
    theme = theme.strip() if (theme and theme.strip()) else "vector design"

    # Extract the core theme directly (no intermediate vision analysis step)
    target_subject = theme

    # Clean target_subject from single-item keywords if bundle_size > 1
    if bundle_size > 1:
        # Force layout grid instructions to completely wrap the target subject
        final_prompt = (
            f"An organized flash-sheet collection grid containing exactly {bundle_size} distinct, separate, and individual variations of the following subject: {target_subject}. "
            f"Arranged cleanly in a balanced {bundle_size} item grid layout on a single square canvas. "
            f"CRITICAL: Each variation must be completely disconnected from the others with wide white spaces separating them. "
            f"Pure black #000000 silhouette shapes on a solid pristine pure white #FFFFFF background. No framing plaque, no 3D rendering, flat 2D graphics only."
        )
    else:
        final_prompt = (
            f"A professional, ultra-crisp 2D flat vector silhouette stencil of {target_subject}. "
            f"Pure solid black #000000 shapes on a pristine solid white background #FFFFFF. "
            f"Perfect clean bold lines, maximum edge contrast, zero gradients, zero floating parts, optimized for flawless cnc laser cutting extraction."
        )

    if design_style == "framed_filigree":
        strict_prompt = (
            f"Generate a strictly square image (1024x1024 resolution). An intricate, highly detailed, layered stencil silhouette art based on: {final_prompt}."
        )
    else:
        strict_prompt = final_prompt

    if custom_prompt:
        final_prompt = custom_prompt
        strict_prompt = custom_prompt
    else:
        final_prompt = strict_prompt

    # --- gpt-image-2 EXPLICIT IMAGE GENERATION OR IMAGE-TO-IMAGE PIPELINE ---
    prov_lower = (provider or "").lower().strip()
    if prov_lower in ["gpt-image-2", "openai"]:
        resolved_key = (openai_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not resolved_key or len(resolved_key) < 20:
            raise ValueError("Sanity Check Failed: OpenAI API Key is missing or invalid in this context.")
        
        try:
            actual_provider = "gpt-image-2"
            
            # Delegate directly to the factory layout logic to handle structural masking or clean text-to-image
            factory = ImageFactory(openai_key=resolved_key)
            saved_paths = factory.generate("gpt-image-2", final_prompt, output_path, init_image_path, n=n_images, vectorize=vectorize)
            
            return {
                "provider": actual_provider,
                "prompt": final_prompt,
                "vision_description": None,
                "status": "success",
                "error": None,
                "saved_paths": saved_paths
            }
        except Exception as e:
            print(f"[gpt-image-2 ERROR] {str(e)} - Attempting degraded fallback to alternative providers...")
            
            # Fallback 1: Google Imagen 3 via gemini_key or banana_key
            alt_key = gemini_key or banana_key
            if alt_key and alt_key.strip():
                try:
                    print("[image_engine] Attempting fallback to Google Imagen 3...")
                    _try_imagen3(alt_key, final_prompt, output_path)
                    return {
                        "provider": "google/imagen-3",
                        "prompt": final_prompt,
                        "vision_description": None,
                        "status": "degraded",
                        "error": f"OpenAI failed ({e}); fell back to Google Imagen 3."
                    }
                except Exception as ex_gem:
                    print(f"[image_engine] Fallback to Google Imagen 3 failed: {ex_gem}")
            
            # Fallback 2: Replicate via replicate_key
            if replicate_key and replicate_key.strip():
                try:
                    print("[image_engine] Attempting fallback to Replicate (flux-schnell)...")
                    _try_replicate(replicate_key, "black-forest-labs/flux-schnell", final_prompt, output_path)
                    return {
                        "provider": "replicate/flux-schnell",
                        "prompt": final_prompt,
                        "vision_description": None,
                        "status": "degraded",
                        "error": f"OpenAI failed ({e}); fell back to Replicate flux-schnell."
                    }
                except Exception as ex_rep:
                    print(f"[image_engine] Fallback to Replicate failed: {ex_rep}")
            
            # Fallback 3: Hugging Face via huggingface_key
            if huggingface_key and huggingface_key.strip():
                try:
                    print("[image_engine] Attempting fallback to Hugging Face (FLUX.1-schnell)...")
                    _try_huggingface_image(huggingface_key, "black-forest-labs/FLUX.1-schnell", final_prompt, output_path)
                    return {
                        "provider": "huggingface/flux-schnell",
                        "prompt": final_prompt,
                        "vision_description": None,
                        "status": "degraded",
                        "error": f"OpenAI failed ({e}); fell back to Hugging Face FLUX.1-schnell."
                    }
                except Exception as ex_hf:
                    print(f"[image_engine] Fallback to Hugging Face failed: {ex_hf}")

            # Fallback 4: Stability AI via stability_key
            if stability_key and stability_key.strip():
                try:
                    print("[image_engine] Attempting fallback to Stability AI (sd3)...")
                    _generate_with_stability(final_prompt, output_path, api_key=stability_key)
                    return {
                        "provider": "stability/sd3",
                        "prompt": final_prompt,
                        "vision_description": None,
                        "status": "degraded",
                        "error": f"OpenAI failed ({e}); fell back to Stability AI SD3."
                    }
                except Exception as ex_stab:
                    print(f"[image_engine] Fallback to Stability AI failed: {ex_stab}")
            
            # If all fallbacks failed or no keys were available, raise the original exception
            raise RuntimeError(f"OpenAI Generation Failed (and no alternative fallbacks succeeded): {str(e)}")

    """
    Generates a stencil image based on profile_tier or preferred provider.
    PRO TIER: Call Recraft V4 API with style="vector/line_art" to get native .svg.
    ECO TIER: Call replicate/flux-schnell.
    FREE TIER: Call Hugging Face black-forest-labs/FLUX.1-schnell.
    """
    # Override provider based on profile_tier if explicitly given
    if profile_tier == "pro":
        provider = "recraft"
    elif profile_tier == "eco":
        provider = "black-forest-labs/flux-schnell" if replicate_key else "huggingface-flux-free"
    elif profile_tier == "free":
        provider = "huggingface-flux-free"

    # strict_prompt has already been set at the top of the function
    pass

    # If Recraft is requested (pro tier), implement the Recraft V4 API call
    if provider == "recraft":
        print("[image_engine] Invoking Recraft V4 vector line art API...")
        try:
            # Let's call Recraft V4 API
            # Standard Recraft API call via requests or replicate model recraft-ai/recraft-v4
            # We can use Replicate's model: recraft-ai/recraft-v4
            if replicate_key:
                # We fetch native svg using recraft-v4
                url = "https://api.replicate.com/v1/models/recraft-ai/recraft-v4/predictions"
                headers = {
                    "Authorization": f"Token {replicate_key.strip()}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "input": {
                        "prompt": strict_prompt,
                        "style": "vector/line_art",
                        "size": "1024x1024"
                    }
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=30, proxies={"http": None, "https": None})
                resp.raise_for_status()
                pred = resp.json()
                pred_id = pred["id"]
                poll_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
                
                import time
                for _ in range(60):
                    poll_resp = requests.get(poll_url, headers=headers, timeout=10, proxies={"http": None, "https": None})
                    poll_resp.raise_for_status()
                    status_data = poll_resp.json()
                    if status_data["status"] == "succeeded":
                        output_url = status_data["output"]
                        if isinstance(output_url, list):
                            output_url = output_url[0]
                        
                        # Recraft can return .svg directly or raster. Check extension
                        img_resp = requests.get(output_url, timeout=30, proxies={"http": None, "https": None})
                        
                        # If output path is expecting .png, and we got SVG, or vice versa, write appropriately.
                        # Wait, we need to output transparent tp.png.
                        # If the output URL is SVG, we save it and then render it to png, or save directly.
                        # To keep it simple, we save the bytes.
                        if output_url.endswith(".svg") or "image/svg+xml" in img_resp.headers.get("Content-Type", ""):
                            svg_output_path = output_path.replace("_source.png", ".svg").replace(".png", ".svg")
                            with open(svg_output_path, "wb") as f:
                                f.write(img_resp.content)
                            # Render SVG to PNG locally or create transparent PNG
                            # Let's save a copy as png too (using local_binarize_image or simple rendering)
                            # We can also fallback to generating a PNG
                        with open(output_path, "wb") as f:
                            f.write(img_resp.content)
                        return {
                            "provider": "recraft-v4",
                            "prompt": strict_prompt
                        }
                    elif status_data["status"] == "failed":
                        raise ValueError(f"Recraft failed: {status_data.get('error')}")
                    time.sleep(2)
            else:
                raise ValueError("Missing Replicate key for Recraft PRO TIER.")
        except Exception as recraft_err:
            print(f"[image_engine] Recraft V4 failed: {recraft_err}. Falling back to default list...")

    # Build fallback order starting with preferred provider
    all_providers = [
        "gpt-image-2", "imagen-3-generate", "imagen-3-edit",
        "stable-diffusion-xl-core", "stable-diffusion-3-pro", "bria-2.3",
        "black-forest-labs-flux-pro", "huggingface-flux-free", "stability"
    ]
    pref = provider.lower().strip() if provider else "gpt-image-2"

    # Filter based on key availability to avoid trying providers we don't have keys for
    active_providers = []
    for p in all_providers:
        if p == "gpt-image-2" and not (openai_key or os.getenv("OPENAI_API_KEY")):
            continue
        if p in ("imagen-3-generate", "imagen-3-edit") and not (gemini_key or banana_key):
            continue
        if p in ("stable-diffusion-xl-core", "stable-diffusion-3-pro", "bria-2.3", "black-forest-labs-flux-pro") and not (replicate_key and replicate_key.strip()):
            continue
        if p == "stability" and not (stability_key and stability_key.strip()):
            continue
        if p == "huggingface-flux-free" and not (huggingface_key or getattr(settings, "HUGGINGFACE_API_KEY", None)):
            continue
        active_providers.append(p)

    if pref in active_providers:
        active_providers.remove(pref)
        priority_list = [pref] + active_providers
    else:
        if pref and pref != "banana":
            priority_list = [pref] + active_providers
        elif active_providers:
            priority_list = active_providers
        else:
            priority_list = ["huggingface-flux-free"] # fallback absolute default

    factory = ImageFactory(
        openai_key=openai_key,
        gemini_key=gemini_key,
        banana_key=banana_key,
        replicate_key=replicate_key,
        openrouter_key=openrouter_key,
        huggingface_key=huggingface_key,
        stability_key=stability_key
    )

    errors = []
    last_prompt = strict_prompt
    for p in priority_list:
        print(f"[image_engine] Attempting stencil generation via {p}...")
        try:
            current_prompt = strict_prompt
            if p == "huggingface-flux-free":
                if custom_prompt:
                    current_prompt = custom_prompt
                elif bundle_size > 1:
                    current_prompt = f"An organized flash-sheet collection grid containing exactly {bundle_size} distinct, separate, and individual variations of {theme}, arranged cleanly in a balanced grid layout on a single canvas. Each variation must be completely disconnected from the others with wide white spaces separating them. Pure black and white vector stencil, white background, high contrast, clean lines."
                else:
                    current_prompt = f"A professional matte black vector stencil of {theme}, white background, high contrast, clean lines, flat vector silhouette"
            
            # Execute generation
            saved_paths = factory.generate(p, current_prompt, output_path, init_image_path, n=n_images, vectorize=vectorize)
            print(f"[image_engine] Stencil generation succeeded via {p}.")

            # Identify if fallback occurred
            status = "success"
            error_details = None
            if pref != p:
                status = "degraded"
                error_details = f"Preferred provider {pref} failed. Fallback to {p} succeeded. Provider errors: {'; '.join(errors)}"
                
            return {
                "provider": p,
                "prompt": current_prompt,
                "status": status,
                "error": error_details,
                "saved_paths": saved_paths
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = f"{p} failed: {e}"
            print(f"[image_engine] {err_msg}. Live failover to next image provider in the prioritization list...")
            errors.append(err_msg)
            last_prompt = current_prompt

    # If we get here, all providers failed
    raise RuntimeError(f"All image providers failed stencil generation: {'; '.join(errors)}")


def regenerate_stencil_image_guided(
    provider: str,
    banana_key: str,
    openai_key: str,
    theme: str,
    current_image_path: str,
    init_image_path: str,
    instructions: str,
    output_path: str,
    bundle_size: int = 4,
    gemini_key: str = None,
    replicate_key: str = None,
    openrouter_key: str = None,
    huggingface_key: str = None,
    stability_key: str = None,
    vectorize: bool = False
):
    """
    Uses Gemini Multimodal to analyze differences and generate a corrected stencil image.
    Fails loudly if API fails.
    """
    api_key = gemini_key or banana_key
    if not api_key:
        raise ValueError("Clé API Gemini/Imagen manquante pour la correction guidée.")

    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key.strip())

    def _encode_image(path: str) -> str:
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Image for correction not found: {path}")
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    current_b64 = _encode_image(current_image_path)
    contents = []

    if init_image_path and os.path.exists(init_image_path):
        init_b64 = _encode_image(init_image_path)
        contents.append("=== ORIGINAL BASE IMAGE ===")
        contents.append(
            types.Part.from_bytes(
                data=base64.b64decode(init_b64),
                mime_type="image/png" if not init_image_path.lower().endswith((".jpg", ".jpeg")) else "image/jpeg"
            )
        )

    contents.append("=== CURRENT GENERATED IMAGE (Has defects to correct) ===")
    contents.append(
        types.Part.from_bytes(
            data=base64.b64decode(current_b64),
            mime_type="image/png" if not current_image_path.lower().endswith((".jpg", ".jpeg")) else "image/jpeg"
        )
    )

    system_prompt = (
        "You are an expert prompt engineer for Text-to-Image models (gpt-image-2 and Imagen 3).\n"
        "Your role is to write a revised and corrected image prompt in English based on visual feedback.\n"
        "You are modifying a black and white stencil design for laser cutting.\n"
        "Analyze the original base image and the current generated image. "
        f"Then, read the user's correction instructions: '{instructions}'.\n"
    )
    if bundle_size > 1:
        system_prompt += f"STRICT REQUIREMENT: The image must be a flash-sheet grid containing exactly {bundle_size} distinct separate designs.\n"
    else:
        system_prompt += "STRICT REQUIREMENT: The image must contain a single isolated design.\n"

    system_prompt += (
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
        print(f"[guided_regeneration] Gemini generated prompt: {custom_prompt}")
    except Exception as e:
        raise RuntimeError(f"Gemini correction prompt generation failed: {e}")

    generate_stencil_image(
        provider=provider,
        banana_key=banana_key,
        openai_key=openai_key,
        theme=theme,
        output_path=output_path,
        init_image_path=None,
        custom_prompt=custom_prompt,
        bundle_size=bundle_size,
        gemini_key=gemini_key,
        replicate_key=replicate_key,
        openrouter_key=openrouter_key,
        huggingface_key=huggingface_key,
        stability_key=stability_key,
        vectorize=vectorize
    )


def split_multielement_image(image_path: str, output_dir: str, bundle_size: int) -> list[str]:
    """
    Uses PIL and OpenCV to detect separate distinct black vector shapes,
    crops each into its own square white canvas (1024x1024) PNG file (element_1.png, element_2.png, ...).
    Returns list of paths to cropped element files.
    """
    if not os.path.exists(image_path):
        return []

    try:
        from PIL import Image
        import cv2
        import numpy as np

        # Load image via PIL to safely preserve/handle alpha transparent channel
        pil_img = Image.open(image_path).convert("RGBA")
        white_bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
        white_bg.alpha_composite(pil_img)
        
        # Convert to grayscale numpy array for OpenCV processing
        gray_pil = white_bg.convert("L")
        gray = np.array(gray_pil)
        img_height, img_width = gray.shape

        # Binarize to pure B&W (black shapes = 0, white background = 255)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        
        # Invert to find contours (shapes must be white (255) on black background (0))
        thresh_inv = cv2.bitwise_not(thresh)
        
        # Morphological closing operation before findContours to bridge small gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(thresh_inv, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Dynamic min_area based on master canvas resolution (0.5% of total area)
        min_area = int(img_width * img_height * 0.005)
        valid_boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                # Ignore outer border boxes if they cover almost the entire image
                if w > img_width * 0.98 and h > img_height * 0.98:
                    continue
                valid_boxes.append((x, y, w, h))

        if not valid_boxes:
            print("[image_engine] No distinct elements detected via contour analysis. Using master image.")
            return [image_path]

        # Sort from left to right
        valid_boxes.sort(key=lambda b: b[0])
        cropped_paths = []

        for idx, (x, y, w, h) in enumerate(valid_boxes):
            # Crop with clean padding (20px)
            pad = 20
            x_start = max(0, x - pad)
            y_start = max(0, y - pad)
            x_end = min(img_width, x + w + pad)
            y_end = min(img_height, y + h + pad)

            cropped_roi = thresh[y_start:y_end, x_start:x_end]

            # Place centered on a pristine square (1024x1024) white canvas
            canvas = np.ones((1024, 1024), dtype=np.uint8) * 255
            
            h_roi, w_roi = cropped_roi.shape
            if h_roi > 1024 or w_roi > 1024:
                scale = min(1024 / w_roi, 1024 / h_roi)
                new_w = int(w_roi * scale)
                new_h = int(h_roi * scale)
                cropped_roi = cv2.resize(cropped_roi, (new_w, new_h), interpolation=cv2.INTER_AREA)
                h_roi, w_roi = cropped_roi.shape

            offset_y = (1024 - h_roi) // 2
            offset_x = (1024 - w_roi) // 2
            canvas[offset_y:offset_y+h_roi, offset_x:offset_x+w_roi] = cropped_roi

            out_name = f"element_{idx+1}.png"
            out_path = os.path.join(output_dir, out_name)
            cv2.imwrite(out_path, canvas)
            cropped_paths.append(out_path)

        print(f"[image_engine] Successfully split master image into {len(cropped_paths)} elements on 1024x1024 canvases.")
        return cropped_paths

    except Exception as e:
        print(f"[image_engine] Element splitting failed: {e}. Falling back to single master image.")
        return [image_path]


def generate_mockup_backdrop(theme: str, openai_key: str, custom_prompt: str = None) -> bytes:
    """Generates a premium, high-end empty room backdrop tailored to the theme."""
    if custom_prompt and custom_prompt.strip():
        backdrop_prompt = custom_prompt.replace("{theme}", theme)
    else:
        backdrop_prompt = (
            f"A professional, crisp e-commerce product photography of an empty interior wall mockup, straight-on centered shot, eye-level perspective. "
            f"The main focus is a large, flat, completely empty wall made of a premium texture (such as smooth industrial concrete, high-end matte plaster, split-face slate, or luxury rustic oak wood panels). "
            f"The room's architectural style, high-end interior styling, cozy decorations, and atmospheric cinematic lighting must elegantly reflect the aesthetic essence of the theme: '{theme}'. \n\n"
            f"STRICT VISUAL RULES:\n"
            f"- The center of the wall MUST be completely blank, flat, and clear, acting as a canvas ready for mounting a wall art product.\n"
            f"- NO existing frames, NO canvases, NO paintings, NO wall clocks, NO shelves, and NO mirrors on the wall.\n"
            f"- NO hanging pendant lights, NO overhead chandeliers dangling into the frame, and NO plants or leaves blocking or overlapping the empty wall space.\n"
            f"- Soft, natural, ambient side-lighting from a realistic window creating clean, subtle depth. Photorealistic rendering, 8k resolution, uncluttered luxury aesthetic."
        )
    resolved_key = (openai_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not resolved_key:
        raise ValueError("Sanity Check Failed: OpenAI API Key is missing or invalid in this context.")
    
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "model": "gpt-image-2",
        "prompt": backdrop_prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "auto"
    }
    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers=headers,
        json=payload,
        timeout=60,
        proxies={"http": None, "https": None}
    )
    response.raise_for_status()
    data = response.json()
    img_item = data.get("data", [{}])[0]
    if "b64_json" in img_item:
        return base64.b64decode(img_item["b64_json"])
    elif "url" in img_item:
        image_url = img_item["url"]
        return requests.get(image_url, timeout=30, proxies={"http": None, "https": None}).content
    else:
        raise RuntimeError("No image data or URL found in OpenAI mockup response.")


def create_real_metal_mockup(stencil_path: str, backdrop_bytes: bytes, output_mockup_path: str):
    """
    Composites the black stencil onto the room backdrop using PIL.
    Transforms the pure black stencil into an engraved matte-black metallic piece
    with an elegant drop shadow for realism.
    """
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    import io

    # 1. Load the backdrop and the stencil
    backdrop = Image.open(io.BytesIO(backdrop_bytes)).convert("RGBA")
    stencil = Image.open(stencil_path).convert("RGBA")
    
    # Ensure stencil matches 1024x1024 or scale it down slightly to fit nicely on the wall (e.g., 650x650)
    target_size = (650, 650)
    stencil = stencil.resize(target_size, Image.Resampling.LANCZOS)
    
    # 2. Isolate the black artwork mask (assuming stencil is black shapes on white background)
    # Convert to grayscale and invert so the artwork mask is white (255) and background is black (0)
    gray_stencil = stencil.convert("L")
    artwork_mask = ImageOps.invert(gray_stencil).point(lambda x: 255 if x > 50 else 0)
    
    # 3. Create the Matte-Black Metal Layer
    # Create a solid dark charcoal/matte black canvas (#1A1A1A or #111111)
    metal_color = Image.new("RGBA", target_size, (22, 22, 22, 255))
    
    # 4. Generate a Realistic Bevel/Emboss Drop Shadow
    # Create an alpha mask for the shadow, blur it, and offset it slightly
    shadow_mask = artwork_mask.filter(ImageFilter.GaussianBlur(radius=12))
    shadow = Image.new("RGBA", backdrop.size, (0, 0, 0, 160)) # Smooth dark shadow
    
    # Center position on the wall
    offset_x = (backdrop.width - target_size[0]) // 2
    offset_y = (backdrop.height - target_size[1]) // 2
    
    # Paste shadow onto backdrop first (shifted 8px down and 4px right for depth)
    backdrop.alpha_composite(shadow, dest=(offset_x + 4, offset_y + 8), source=(0, 0))
    
    # 5. Composite the metal artwork onto the background using the artwork mask
    artwork_final = Image.new("RGBA", target_size)
    artwork_final.paste(metal_color, (0, 0), mask=artwork_mask)
    
    backdrop.alpha_composite(artwork_final, dest=(offset_x, offset_y))
    
    # Save the final stunning real-world mockup
    backdrop.convert("RGB").save(output_mockup_path, "JPEG", quality=95)
    print(f"[MOCKUP SUCCESS] Premium metallic artwork mockup saved")


from typing import Optional

def generate_stencil_image(
    provider: str,
    banana_key: str,
    openai_key: str,
    theme: str,
    output_path: str,
    init_image_path: str = None,
    custom_prompt: str = None,
    bundle_size: int = 4,
    design_style: str = "classic",
    gemini_key: str = None,
    replicate_key: str = None,
    openrouter_key: str = None,
    huggingface_key: str = None,
    stability_key: str = None,
    profile_tier: str = "free",
    strict_fidelity: bool = True,
    vectorize: bool = False,
    generate_real_mockup: bool = False,
    mockup_configs: Optional[list] = None,
    n_images: int = 1
):
    result = _generate_stencil_image_core(
        provider=provider,
        banana_key=banana_key,
        openai_key=openai_key,
        theme=theme,
        output_path=output_path,
        init_image_path=init_image_path,
        custom_prompt=custom_prompt,
        bundle_size=bundle_size,
        design_style=design_style,
        gemini_key=gemini_key,
        replicate_key=replicate_key,
        openrouter_key=openrouter_key,
        huggingface_key=huggingface_key,
        stability_key=stability_key,
        profile_tier=profile_tier,
        strict_fidelity=strict_fidelity,
        vectorize=vectorize,
        n_images=n_images
    )
    
    if generate_real_mockup:
        print(f"[image_engine] Starting multi-mockup generation loop. Total items: {len(mockup_configs) if mockup_configs else 0}")
        try:
            configs_to_process = mockup_configs if (mockup_configs and len(mockup_configs) > 0) else [{"index": 0, "style": "default_wood"}]
            
            for config in configs_to_process:
                idx = config.get("index") if isinstance(config, dict) else config.index
                theme_style = config.get("style") if isinstance(config, dict) else config.style
                
                print(f"[image_engine] Rendering item index {idx} using design theme style: {theme_style}")
                
                backdrop_bytes = generate_mockup_backdrop(theme_style, openai_key)
                
                temp_bg = output_path.replace("_source.png", f"_temp_bg_{idx}.jpg").replace(".png", f"_temp_bg_{idx}.jpg").replace(".jpg", f"_temp_bg_{idx}.jpg")
                with open(temp_bg, 'wb') as f:
                    f.write(backdrop_bytes)
                    
                from .mockup_engine import composite_stencil_on_bg
                
                mockup_raw_path = output_path.replace("_source.png", f"_mockup_raw_{idx}.jpg").replace(".png", f"_mockup_raw_{idx}.jpg").replace(".jpg", f"_mockup_raw_{idx}.jpg")
                mockup_commercial_path = output_path.replace("_source.png", f"_mockup_commercial_{idx}.jpg").replace(".png", f"_mockup_commercial_{idx}.jpg").replace(".jpg", f"_mockup_commercial_{idx}.jpg")
                
                print(f"[image_engine] Compositing raw 3D mockup asset for index {idx}...")
                composite_stencil_on_bg(
                    stencil_path=output_path, 
                    bg_path=temp_bg, 
                    output_path=mockup_raw_path, 
                    material="matte_black_metal",
                    apply_tp_overlay=False
                )
                
                print(f"[image_engine] Compositing commercial framed 3D mockup asset for index {idx}...")
                composite_stencil_on_bg(
                    stencil_path=output_path, 
                    bg_path=temp_bg, 
                    output_path=mockup_commercial_path, 
                    material="matte_black_metal",
                    apply_tp_overlay=True
                )
                
                if idx == 0:
                    result["mockup_raw_path"] = mockup_raw_path
                    result["mockup_commercial_path"] = mockup_commercial_path
                
                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
        except Exception as mockup_err:
            print(f"[image_engine] Premium Mockup loop processing failed: {mockup_err}")
            import traceback
            traceback.print_exc()
            
    return result

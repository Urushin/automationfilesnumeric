"""
DALL-E 3 Stencil Image Generation Service
Generates laser-ready black & white stencil images using a hardcoded,
production-grade prompt that prevents structural compilation errors.
"""
import requests
import base64
from openai import OpenAI
from fastapi import HTTPException

# ─────────────────────────────────────────────────────────────────────────────
# HARDCODED PRODUCTION DALL-E 3 PROMPT TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────
DALLE_PROMPT_TEMPLATE = (
    "A crisp, perfect, flat vector-style stencil silhouette art of {theme}. "
    "Solid black shapes and lines on a solid stark white background only. "
    "CRITICAL STRUCTURAL CONSTRAINT: Every single black shape, line, pattern, and element MUST be "
    "physically and fully connected to the main body of the design to prevent any floating islands, "
    "isolated dots, or loose separate pieces — because this design will be physically laser cut from "
    "a single wood or acrylic sheet and must hold together as one connected piece. "
    "All lines must be thick, clear, bold, and uniform with no hairlines. "
    "Optimize every element for laser cutting or CNC routing. "
    "ABSOLUTELY NO: gradients, shadows, grey pixels, sketchy lines, soft edges, texture fills, halftones, "
    "watermarks, background patterns, or any text. "
    "Flat 2D graphic only. Centered symmetrical composition. Maximum contrast. Pure black (#000000) on pure white (#FFFFFF)."
)


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def legacy_generate_stencil_image(openai_api_key: str, theme: str, output_path: str) -> str:
    """
    Calls DALL-E 3 with the hardcoded laser-optimized prompt.
    Downloads the result and saves it to output_path.

    Args:
        openai_api_key: OpenAI API key from Settings
        theme: Design theme (e.g., "wolf head mandala geometric")
        output_path: Absolute filesystem path to save the PNG

    Returns:
        The DALL-E 3 image URL (for reference/logging)
    """
    if not openai_api_key:
        raise ValueError("OpenAI API key is missing. Configure it in Settings.")

    client = OpenAI(
        api_key=openai_api_key,
        base_url="https://api.openai.com/v1"
    )

    optimized_prompt = DALLE_PROMPT_TEMPLATE.format(theme=theme)

    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=optimized_prompt,
            n=1,
            size="1024x1024",
            quality="hd",
        )
        img_item = response.data[0]
        if img_item.b64_json:
            img_data = base64.b64decode(img_item.b64_json)
            image_url = ""
        elif img_item.url:
            image_url = img_item.url
            img_response = requests.get(image_url, timeout=60)
            img_response.raise_for_status()
            img_data = img_response.content
        else:
            raise ValueError("No image URL or b64_json found in response data")
            
        with open(output_path, "wb") as f:
            f.write(img_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"gpt-image-1 API Error: {str(e)}")

    return image_url

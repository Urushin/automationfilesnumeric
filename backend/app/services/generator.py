import json
import re
import requests
from openai import OpenAI
from google import genai


def generate_stencil_image(openai_key: str, theme: str, output_path: str):
    """
    Calls DALL-E 3 to generate a pure black and white stencil.
    Ensures all black lines are structurally connected (no islands).
    """
    if not openai_key:
        raise ValueError("OpenAI API key is missing. Configure it in Settings.")

    client = OpenAI(api_key=openai_key)

    strict_prompt = (
        f"A pure black and white stencil design of '{theme}'. "
        "A single solid black silhouette or clean solid black line art on a clean solid white background. "
        "No shading, no gradients, no grey colors, no texture. "
        "Crucial: The design must be a single connected piece, all black lines and elements must be "
        "structurally connected together so it can be laser cut from a single sheet of wood/acrylic "
        "without falling apart (no floating islands, all parts must connect to the main structure). "
        "Vector stencil format."
    )

    response = client.images.generate(
        model="dall-e-3",
        prompt=strict_prompt,
        n=1,
        size="1024x1024",
        response_format="url"
    )

    image_url = response.data[0].url

    # Download the image and save it
    img_data = requests.get(image_url).content
    with open(output_path, 'wb') as handler:
        handler.write(img_data)


def clean_json_response(raw_text: str) -> dict:
    """Helper to clean and parse JSON response from LLMs."""
    # Remove markdown code blocks if present
    cleaned = re.sub(r"```json\s*", "", raw_text)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def get_fallback_seo(theme: str) -> dict:
    """Generates clean, local SEO metadata when APIs are unavailable."""
    clean_theme = theme.replace("-", " ").capitalize()
    return {
        "title_fr": f"Fichier Laser {clean_theme} SVG, Découpe Bois Laser DXF, Pochoir Vectoriel pour Découpeuse",
        "title_en": f"{clean_theme} Laser Cut File SVG, Wood Cut Vector DXF, Stencil Design Template for Glowforge",
        "description": (
            f"Fichier de découpe laser de haute qualité - Thème : {clean_theme}.\n\n"
            "Ce produit numérique est spécialement optimisé pour la découpe laser (CNC, Glowforge, Trotec, CO2, etc.).\n\n"
            "CE QUI EST INCLUS DANS LE PACK ZIP :\n"
            "- 1 Fichier vectoriel SVG (Qualité supérieure, redimensionnable)\n"
            "- 1 Fichier CAO DXF (Pour logiciels de CAO et machines CNC)\n"
            "- 1 Fichier PDF haute définition (Pour impression ou transfert)\n"
            "- 1 Fichier PNG transparent haute résolution (Idéal pour sublimation ou prévisualisation)\n\n"
            "CONSEILS D'UTILISATION :\n"
            "- Recommandé pour des matériaux comme le bois (contreplaqué 3mm ou 4mm), l'acrylique ou le carton.\n"
            "- Veillez à bien adapter la vitesse et la puissance de votre laser en fonction du matériau.\n\n"
            "USAGE COMMERCIAL :\n"
            "Vous pouvez utiliser ce design pour créer des objets physiques destinés à la vente. "
            "Toutefois, la revente ou la distribution des fichiers numériques originaux est strictement interdite."
        ),
        "tags_fr": [
            "fichier laser", "decoupe bois", "stencil svg", "pochoir cnc",
            "motif vectoriel", "glowforge francais", "artisanat bois", "dxf laser",
            "decoupe laser", "decoration murale", "modelle numerique", "art laser"
        ],
        "tags_en": [
            "laser cut file", "wood svg dxf", "laser cut stencil", "glowforge svg",
            "vector stencil", "cnc cutting file", "woodworking dxf", "digital download",
            "wall art vector", "laser engrave", "svg cut file", "silhouette vector"
        ]
    }


def generate_seo_metadata(settings, theme: str) -> dict:
    """
    Compatibility wrapper around the complete Gemini SEO service.

    Older routes still call this helper, so keep the public function but route all
    SEO generation through the bilingual template engine used by the SSE pipeline.
    """
    from .gemini_seo import generate_etsy_seo

    return generate_etsy_seo(theme, getattr(settings, "gemini_key", "") or None)

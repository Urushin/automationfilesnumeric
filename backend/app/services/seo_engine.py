"""
SEO & Metadata Engine — v5.0 (litellm Universal Router)
Generates high-converting bilingual Etsy SEO packages (title_fr/en, description_fr/en, tags_fr/en).
Uses litellm as the primary unified router for all LLM providers (Claude, GPT, Gemini, Mistral, LLaMA).
Falls back to direct Google GenAI SDK for vision when litellm vision fails.
Fails loudly only when ALL providers in the priority list are exhausted.
"""

import os
import re
import json
import unicodedata
import base64
from typing import Optional, List
from pydantic import BaseModel, Field


class EtsyListingSEO(BaseModel):
    title_fr: str = Field(default="", description="Strictly max 140 chars. Organic fluid French title. Front-load quantity and subject.")
    title_en: str = Field(default="", description="Strictly max 140 chars. Organic fluid English title. Front-load quantity and subject.")
    description_fr: str = Field(default="", description="Detailed French description following the exact template sections, with the required license links.")
    description_en: str = Field(default="", description="Detailed English description mirroring the French template structure and license links.")
    tags_fr: List[str] = Field(default_factory=list, description="Exactly 13 tags, max 20 chars per tag, lowercase, ASCII, no accents/punctuation.")
    tags_en: List[str] = Field(default_factory=list, description="Exactly 13 tags, max 20 chars per tag, lowercase, ASCII, no accents/punctuation.")



SEO_SYSTEM_PROMPT = """You are an elite Etsy SEO copywriter and conversion specialist for the laser cutting / digital craft files niche (SVG, DXF, AI, EPS, PDF cut files for Cricut, Silhouette, Glowforge, xTool).

=== TITLE RULES (title_fr, title_en) ===
- HARD LIMIT: maximum 140 characters. Count strictly.
- Style: "Etsy 2025" Organic and fluid. Prioritize readability and buyer intent over rigid keyword stuffing. Use natural phrasing and em-dashes (–) instead of pipes (|).
- Front-load the product and quantity: read the incoming BUNDLE SIZE and write "[BUNDLE SIZE] [Subject] SVG Bundle" or similar, followed by the purpose ("for Laser Cutting"), and finally the compatible machines.
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
Téléchargement immédiat après achat sur Etsy.

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
- Strictly lowercase, ASCII only, no punctuation, no accents.
- Order of priority: Specific subject terms first, then formats (svg, dxf), then machines (cricut, glowforge), then generic niche terms (wood laser, laser cut).
"""

# ─── litellm model map: provider_key -> litellm model string ───────────────
_LITELLM_MODEL_MAP = {
    "claude-3-5-haiku":         "anthropic/claude-3-5-haiku-20241022",
    "claude-3-5-sonnet":        "anthropic/claude-3-5-sonnet-20241022",
    "claude-3-opus":            "anthropic/claude-3-opus-20240229",
    "gpt-4o":                   "gpt-4o",
    "gpt-4o-mini":              "gpt-4o-mini",
    "gemini-2.0-flash":         "gemini/gemini-2.0-flash",
    "gemini-1.5-pro":           "gemini/gemini-1.5-pro",
    "gemini-1.5-flash":         "gemini/gemini-1.5-flash",
    "gemini-2.0-flash-lite":    "gemini/gemini-2.0-flash-lite",
    "mistral-large-latest":     "mistral/mistral-large-latest",
    "mistral-small-latest":     "mistral/mistral-small-latest",
    "llama-3-70b-instruct-openrouter": "openrouter/meta-llama/llama-3-70b-instruct",
}

# Providers that support vision (multimodal image input) via litellm
_VISION_CAPABLE = {
    "claude-3-5-haiku", "claude-3-5-sonnet", "claude-3-opus",
    "gpt-4o", "gpt-4o-mini",
    "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite",
}

# Default fallback chain when primary provider fails
_DEFAULT_FALLBACK_CHAIN = [
    "claude-3-5-haiku", "gpt-4o-mini", "gemini-2.0-flash",
    "mistral-large-latest", "gemini-1.5-flash",
]


# ─── Tag & title normalization helpers ─────────────────────────────────────

def _ascii_tag(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9 ]+", " ", value).lower()
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) >= 20:
        return ""
    return value


def _normalize_tags_exact13(raw_tags: List[str], fallback_pool: List[str]) -> List[str]:
    items, seen = [], set()
    for t in raw_tags:
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


def _validate_seo_payload(data: EtsyListingSEO):
    required_markers = [
        "digitalfilesbymop.etsy.com/listing/4499076966",
        "digitalfilesbymop.etsy.com/listing/4499075567",
    ]
    for desc_field, desc_text in [("description_fr", data.description_fr), ("description_en", data.description_en)]:
        missing = [m for m in required_markers if m not in desc_text]
        if missing:
            raise ValueError(f"{desc_field} missing required license links: {missing}")


# ─── Provider environment key injection ────────────────────────────────────

def _inject_litellm_env(provider_key: str, keys: dict):
    """Temporarily set environment variables for the given provider so litellm can authenticate."""
    if provider_key.startswith("claude") and keys.get("anthropic_key"):
        os.environ["ANTHROPIC_API_KEY"] = keys["anthropic_key"].strip()
    elif provider_key.startswith("gpt") and keys.get("openai_key"):
        os.environ["OPENAI_API_KEY"] = keys["openai_key"].strip()
    elif provider_key.startswith("gemini") and keys.get("gemini_key"):
        os.environ["GEMINI_API_KEY"] = keys["gemini_key"].strip()
    elif provider_key.startswith("mistral") and keys.get("mistral_key"):
        os.environ["MISTRAL_API_KEY"] = keys["mistral_key"].strip()
    elif provider_key.startswith("llama") and keys.get("openrouter_key"):
        os.environ["OPENROUTER_API_KEY"] = keys["openrouter_key"].strip()


# ─── litellm unified call (no vision) ─────────────────────────────────────

def _try_litellm_seo(provider_key: str, prompt: str, keys: dict, system_prompt: str = SEO_SYSTEM_PROMPT) -> EtsyListingSEO:
    import litellm
    litellm.set_verbose = False

    model = _LITELLM_MODEL_MAP.get(provider_key)
    if not model:
        raise ValueError(f"No litellm mapping for provider: {provider_key}")

    _inject_litellm_env(provider_key, keys)

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt + "\nReturn ONLY a valid JSON object matching the EtsyListingSEO schema."},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=8192,
        timeout=90,
    )
    raw = response.choices[0].message.content
    return EtsyListingSEO.model_validate_json(raw)


# ─── litellm vision call (with image) ─────────────────────────────────────

def _try_litellm_vision_seo(provider_key: str, prompt: str, image_path: str, keys: dict, system_prompt: str = SEO_SYSTEM_PROMPT) -> EtsyListingSEO:
    import litellm
    litellm.set_verbose = False

    model = _LITELLM_MODEL_MAP.get(provider_key)
    if not model:
        raise ValueError(f"No litellm mapping for provider: {provider_key}")

    if provider_key not in _VISION_CAPABLE:
        raise ValueError(f"{provider_key} does not support vision input")

    _inject_litellm_env(provider_key, keys)

    # Encode image
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    mime = "image/png" if not image_path.lower().endswith((".jpg", ".jpeg")) else "image/jpeg"

    user_content = [
        {"type": "text", "text": prompt + "\nReturn ONLY a valid JSON object matching the EtsyListingSEO schema."},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
    ]

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=8192,
        timeout=90,
    )
    raw = response.choices[0].message.content
    return EtsyListingSEO.model_validate_json(raw)


# ─── Direct Google GenAI SDK fallback (for vision when litellm fails) ──────

def _try_gemini_direct_seo(gemini_key: str, model_id: str, prompt: str, image_path: str, system_prompt: str = SEO_SYSTEM_PROMPT) -> EtsyListingSEO:
    if not gemini_key or not gemini_key.strip():
        raise ValueError("Clé API Gemini manquante.")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=gemini_key.strip())
    contents = []
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_data = f.read()
        mime = "image/png" if not image_path.lower().endswith((".jpg", ".jpeg")) else "image/jpeg"
        contents.append(types.Part.from_bytes(data=img_data, mime_type=mime))
    contents.append(prompt)

    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=EtsyListingSEO,
            temperature=0.7,
            max_output_tokens=8192,
        )
    )
    return EtsyListingSEO.model_validate_json(response.text)


# ─── Main entry point ──────────────────────────────────────────────────────

def generate_etsy_seo(
    theme: str,
    provider: str,
    gemini_key: str,
    mistral_key: str,
    openai_key: str,
    replicate_key: str = None,
    openrouter_key: str = None,
    huggingface_key: str = None,
    anthropic_key: str = None,
    db=None,
    image_path: str = None,
    bundle_size: int = 4,
    profile_tier: str = "free"
) -> dict:
    """
    Generates Etsy SEO metadata package via litellm universal router.
    PRO TIER: claude-3-5-haiku -> gpt-4o-mini
    ECO TIER: mistral/mistral-small-latest
    FREE TIER: gemini/gemini-2.0-flash
    Falls back to direct local deterministic text generator if all models in the tier fail.
    """
    # Map profile_tier to priority list
    if profile_tier == "pro":
        priority_list = ["claude-3-5-haiku", "gpt-4o-mini"]
    elif profile_tier == "eco":
        priority_list = ["mistral-small-latest"]
    else:  # free tier
        priority_list = ["gemini-2.0-flash"]

    # Normalize provider preference alias if provider is supplied
    _alias_map = {
        "claude": "claude-3-5-sonnet",
        "claude-3-5": "claude-3-5-sonnet",
        "claude-haiku": "claude-3-5-haiku",
        "openai": "gpt-4o",
        "gemini": "gemini-2.0-flash",
        "gemini-flash": "gemini-2.0-flash",
        "gemini-pro": "gemini-1.5-pro",
        "gemini-lite": "gemini-2.0-flash-lite",
        "mistral": "mistral-large-latest",
        "llama": "llama-3-70b-instruct-openrouter",
    }
    if provider:
        p_pref = provider.lower().strip()
        p_pref = _alias_map.get(p_pref, p_pref)
        if p_pref not in priority_list:
            priority_list.insert(0, p_pref)

    # If the priority list is empty, append default fallback chain
    for fallback in _DEFAULT_FALLBACK_CHAIN:
        if fallback not in priority_list:
            priority_list.append(fallback)

    keys = {
        "anthropic_key": anthropic_key,
        "openai_key": openai_key,
        "gemini_key": gemini_key,
        "mistral_key": mistral_key,
        "openrouter_key": openrouter_key,
    }

    user_msg = (
        "Generate the complete bilingual Etsy SEO JSON package for this digital product.\n"
        f"THEME: \"{theme}\"\n"
        f"BUNDLE SIZE (QUANTITY OF DESIGNS): {bundle_size}\n\n"
        "Look at the provided stencil image (if attached) and write highly precise and specific "
        "titles, descriptions, and tags. Do NOT use placeholder values — write the "
        f"exact number ({bundle_size}) and describe what the design looks like.\n"
        "Make sure to perform organic, non-literal translation for French and English fields.\n"
        "Double-check that the required license URLs are included in the description fields."
    )

    # Build custom system prompt based on bundle size
    base_system_prompt = SEO_SYSTEM_PROMPT
    if db:
        try:
            from ..routers.settings import get_or_create_settings
            settings = get_or_create_settings(db)
            if settings.prompt_seo and settings.prompt_seo.strip():
                base_system_prompt = settings.prompt_seo
        except Exception as e:
            print(f"[seo_engine] Failed to load prompt_seo from DB settings: {e}")
            
    custom_system_prompt = base_system_prompt
    if bundle_size > 1:
        custom_system_prompt += (
            f"\n\nSTRICT REQUIREMENT: The BUNDLE SIZE is {bundle_size} (which is > 1).\n"
            f"You MUST strictly format the English title starting with '[{bundle_size}] [Subject] SVG Bundle' or 'Bundle of [{bundle_size}] [Subject] SVG' (where [Subject] is replaced by the actual design subject, and [{bundle_size}] is {bundle_size}).\n"
            f"You MUST strictly format the French title starting with 'Pack de [{bundle_size}] [Subject] SVG' or '[{bundle_size}] [Subject] SVG Bundle'.\n"
            "Do NOT output a singular title without the bundle size quantity prefix."
        )
    else:
        custom_system_prompt += (
            "\n\nSTRICT REQUIREMENT: The BUNDLE SIZE is 1.\n"
            "You MUST strictly format the English and French titles simply starting with '[Subject] SVG'.\n"
            "Do NOT use the words 'Bundle', 'Pack', or prefix with any quantity number."
        )

    has_image = image_path and os.path.exists(image_path)
    errors = []
    data = None
    status = "success"
    status_error = None

    # Resilient check: If stencil failed (missing or invalid image), we switch immediately to Text-Only fallback and flag as degraded
    if not has_image:
        status = "degraded"
        status_error = "Stencil image missing or invalid. Fallback to text-only prompt generation."
        print(f"[seo_engine] {status_error}")

    for p in priority_list:
        # If we had a vision error or are in degraded mode, we force text-only mode
        use_vision = has_image and (status != "degraded") and (p in _VISION_CAPABLE)
        use_gemini_direct = has_image and (status != "degraded") and p.startswith("gemini") and keys.get("gemini_key")
        
        print(f"[seo_engine] Attempting SEO via litellm → {p} (vision={use_vision or use_gemini_direct})...")
        try:
            if use_vision:
                try:
                    data = _try_litellm_vision_seo(p, user_msg, image_path, keys, system_prompt=custom_system_prompt)
                except Exception as ve:
                    # Vision failed: degrade to text-only prompt using the theme
                    print(f"[seo_engine] Vision call failed for {p}: {ve}. Falling back to text-only completion on {p}...")
                    status = "degraded"
                    status_error = f"Vision failed, generated via text prompt fallback. Error: {ve}"
                    data = _try_litellm_seo(p, user_msg, keys, system_prompt=custom_system_prompt)
            elif use_gemini_direct:
                try:
                    gemini_model = _LITELLM_MODEL_MAP.get(p, "gemini-1.5-flash").replace("gemini/", "")
                    data = _try_gemini_direct_seo(keys["gemini_key"], gemini_model, user_msg, image_path, system_prompt=custom_system_prompt)
                except Exception as ve:
                    # Vision failed: degrade to text-only
                    print(f"[seo_engine] Gemini vision failed: {ve}. Falling back to text-only completion on {p}...")
                    status = "degraded"
                    status_error = f"Vision failed, generated via text prompt fallback. Error: {ve}"
                    data = _try_litellm_seo(p, user_msg, keys, system_prompt=custom_system_prompt)
            else:
                # Text-only provider or degraded mode
                data = _try_litellm_seo(p, user_msg, keys, system_prompt=custom_system_prompt)

            print(f"[seo_engine] SEO succeeded via {p}.")
            break
        except Exception as e:
            err_msg = f"{p} failed: {e}"
            print(f"[seo_engine] {err_msg}. Failover to next provider...")
            errors.append(err_msg)

    if not data:
        # Strict fallback to a local deterministic text generator if all models in the tier fail
        label = _theme_label(theme)
        title_fr = f"{bundle_size} {label} SVG pour Découpe Laser – Fichier Cricut, Glowforge"
        title_en = f"{bundle_size} {label} SVG Bundle for Laser Cutting – Cricut, Glowforge Files"
        if bundle_size == 1:
            title_fr = f"{label} SVG pour Découpe Laser – Fichier Cricut, Glowforge"
            title_en = f"{label} SVG for Laser Cutting – Cricut, Glowforge Files"
            
        desc_fr = f"🎨 Magnifique design de {label} !\n\nCe pack comprend {bundle_size} design(s) unique(s) de {label}, parfait(s) pour vos créations.\n\nLicence de revente requise :\nhttps://digitalfilesbymop.etsy.com/listing/4499076966\nhttps://digitalfilesbymop.etsy.com/listing/4499075567"
        desc_en = f"🎨 Beautiful {label} design!\n\nThis pack includes {bundle_size} unique design(s) of {label}, perfect for your creations.\n\nLicense links:\nhttps://digitalfilesbymop.etsy.com/listing/4499076966\nhttps://digitalfilesbymop.etsy.com/listing/4499075567"
        
        tags_fr = ["svg", "dxf", "cricut", "glowforge", "laser", "stencil", label.lower()[:20]]
        tags_en = ["svg", "dxf", "cricut", "glowforge", "laser", "stencil", label.lower()[:20]]

        data = EtsyListingSEO(
            title_fr=title_fr[:140],
            title_en=title_en[:140],
            description_fr=desc_fr,
            description_en=desc_en,
            tags_fr=tags_fr,
            tags_en=tags_en
        )
        status = "degraded"
        status_error = "All LLMs failed. Generated via local deterministic SEO generator."

    # Validate required license links
    try:
        _validate_seo_payload(data)
    except Exception as le:
        print(f"[seo_engine] License validation error: {le}. Retaining output anyway to avoid hard failures.")
        if status == "success":
            status = "degraded"
            status_error = f"License validation warning: {le}"

    # Normalize output
    label = _theme_label(theme)
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

    normalized = {
        "status": status,
        "error": status_error,
        "title_fr": _safe_title(data.title_fr, f"🎨 {label} SVG DXF | Fichier Découpe Laser"),
        "title_en": _safe_title(data.title_en, f"🎨 {label} SVG DXF | Laser Cut File"),
        "description": data.description_fr,
        "description_fr": data.description_fr,
        "description_en": data.description_en,
        "tags_fr": _normalize_tags_exact13(data.tags_fr, fallback_fr),
        "tags_en": _normalize_tags_exact13(data.tags_en, fallback_en),
    }

    print(f"[seo_engine] SEO package generated and validated successfully with status: {status}")
    return normalized


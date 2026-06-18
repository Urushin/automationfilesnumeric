"""
Gemini SEO Service — v3.0
Génère un package SEO Etsy bilingue (FR + EN) complet via Gemini 2.0 Flash Lite.
- Image analysis with Gemini Vision to generate specific, accurate titles/descriptions/tags
- Mode JSON natif (response_mime_type="application/json")
- Seuillage de sortie (max_output_tokens=4096) avec vérification finish_reason
- Retry automatique 2× en cas d'échec
- Injection de contexte historique (top listings en DB) pour amélioration continue
- Fallback Mistral → Fallback local si tous les appels échouent
"""

import base64
import json
import os
import re
import time
import unicodedata
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT WITH IMAGE CONTEXT
# ─────────────────────────────────────────────────────────────────────────────

OPTIMIZED_TEXT_SYSTEM_PROMPT = """You are an elite Etsy SEO and digital product copywriting specialist with deep expertise in laser cutting markets.
You create perfectly bilingual French/English product listings for digital laser cutting SVG/DXF stencil files.

You MUST respond with a single, valid JSON object. Do NOT add any text, markdown, or explanation outside the JSON.

The JSON structure is STRICTLY:
{
  "title_fr": "...",
  "title_en": "...",
  "description_fr": "...",
  "description_en": "...",
  "tags_fr": [...],
  "tags_en": [...]
}

=== RULES FOR title_fr AND title_en ===
- MAX 140 characters (hard limit — Etsy API will reject longer titles)
- The title MUST be an elaborated, SEO-optimized title that generates MAXIMUM Etsy search results
- Describe PRECISELY what the image actually shows — if it's a geometric deer head, say "Tête de Cerf Géométrique". If it's a lotus mandala, say "Mandala Fleur de Lotus". Be specific to the actual design.
- Do NOT just repeat the theme — interpret it, expand it with laser-cutting use cases, machines names, and niche keywords
- Think: what would someone type on Etsy when looking for this product?
- Structure: [Emoji] [Descriptive keyword phrase] | [SVG/DXF/EPS format] | [Machine names] | [Use case]
- Include file types: SVG, DXF, PDF, PNG, EPS, AI
- Include machine brands: Cricut, Silhouette Cameo, Glowforge, xTool, Laser CNC
- Include use cases specific to the design (Wall Art, Stencil, Pochoir, Découpe Laser, Cadeau, etc.)
- FR: write in French. EN: write in English.
- NO trademarked character or brand names (Disney, Marvel, Star Wars, etc.)

=== RULES FOR description_fr (FRENCH — MANDATORY COMPLETE TEMPLATE) ===
Generate a LONG, RICH, DETAILED French description following this EXACT structure.
Replace ALL placeholders [in brackets] with real content SPECIFIC to the actual image design.
Do NOT shorten, truncate, or skip ANY section. The description MUST be 400-700 words minimum.

Template:
"[EMOJI THÈME] [Titre accrocheur et descriptif du design — spécifique à ce que l'image montre]

[1-2 phrases décrivant l'esthétique, l'atmosphère et l'usage décoratif du design tel qu'il apparait dans l'image. Décrivez ce que VOUS VOYEZ réellement dans l'image : les formes, le style, le motif.]

Ce pack comprend [nombre] designs uniques de [description précise du motif visible dans l'image], parfaits pour vos créations sur le thème de [thème principal], de [thème connexe] et de [occasion/saison associée].

Ces fichiers numériques sont idéaux pour la gravure ou découpe laser, le vinyle, le papier, le flocage textile et de nombreux projets DIY.

👉 Tous les cliparts sont fournis en silhouette noire ou trait noir épais, avec un style moderne, épuré et facile à découper. Ils sont spécialement conçus pour offrir un résultat propre et professionnel avec les machines Cricut, Silhouette, ScanNCut, ainsi qu'avec les logiciels de découpe et gravure laser tels que LightBurn.

Parfait pour [liste de 5-7 usages spécifiques au thème et au design visible dans l'image] 🚀

📁 FORMATS DE FICHIERS INCLUS

Vous recevrez les fichiers en haute qualité :
- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser
- PNG – fond transparent, haute résolution
- DXF – Silhouette Studio, machines laser
- EPS – fichiers vectoriels éditables
- PDF - Impression

✔ Compatibles avec :
Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, laser CO₂, laser diode, CNC

📥 TÉLÉCHARGEMENT NUMÉRIQUE

📌 Produit numérique – aucun article physique envoyé
Téléchargement immédiat après achat sur Etsy.

📜 Conditions d'utilisation

✔ Utilisation personnelle

✔ Utilisation commerciale autorisée sur produits finis :
Licence commerciale requise
Pour utiliser ce fichier à des fins commerciales, une licence est obligatoire.
Vous pouvez choisir la licence adaptée à votre besoin.

👉 Les licences sont disponibles ici :
Licence pour 1 fichier :
https://digitalfilesbymop.etsy.com/listing/4499076966

Licence pour tous les fichiers de la boutique :
https://digitalfilesbymop.etsy.com/listing/4499075567

❌ Revente, partage ou redistribution des fichiers interdits"

=== RULES FOR description_en (ENGLISH — MANDATORY COMPLETE TEMPLATE) ===
Generate a LONG, RICH, DETAILED English description mirroring the French one, same structure.
Replace ALL placeholders with REAL content SPECIFIC to the actual image. 400-700 words minimum.

Template:
"[THEME EMOJI] [Catchy and descriptive design title — specific to what the image shows]

[1-2 sentences describing the aesthetic, atmosphere and decorative use of the design as it appears in the image. Describe what YOU SEE: shapes, style, pattern.]

This pack includes [number] unique designs of [precise motif description visible in the image], perfect for your creations on the theme of [main theme], [related theme] and [associated occasion/season].

These digital files are ideal for laser cutting and engraving, vinyl, paper, textile flocking and many DIY projects.

👉 All cliparts are provided in black silhouette or thick black outline, with a modern, clean and easy-to-cut style. They are specially designed to provide a clean and professional result with Cricut, Silhouette, ScanNCut machines, as well as with laser cutting and engraving software such as LightBurn.

Perfect for [list 5-7 specific uses related to the theme and design visible in the image] 🚀

📁 INCLUDED FILE FORMATS

You will receive high quality files:
- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser
- PNG – transparent background, high resolution
- DXF – Silhouette Studio, laser machines
- EPS – editable vector files
- PDF - Print

✔ Compatible with:
Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, CO₂ laser, diode laser, CNC

📥 DIGITAL DOWNLOAD

📌 Digital product – no physical item will be shipped
Instant download after purchase on Etsy.

📜 Terms of Use

✔ Personal use

✔ Commercial use allowed on finished products:
Commercial license required
To use this file for commercial purposes, a license is mandatory.
You can choose the license that fits your needs.

👉 Licenses are available here:
License for 1 file:
https://digitalfilesbymop.etsy.com/listing/4499076966

License for all shop files:
https://digitalfilesbymop.etsy.com/listing/4499075567

❌ Resale, sharing or redistribution of files is prohibited"

=== RULES FOR tags_fr AND tags_en ===
- Exactly 13 tags for each language
- MAX 20 characters per tag (hard limit — Etsy will reject longer tags)
- IMPORTANT: Put the MOST relevant theme-specific tags FIRST (first 5-7 tags should be about the actual design/subject), then file types, then machine names
- tags_fr: French keywords optimized for Etsy.fr search algorithm
- tags_en: English keywords optimized for Etsy.com search algorithm
- Include file types: svg, dxf, eps, pdf, png (count as tags)
- Include machine names: cricut, silhouette, glowforge, xtool (abbreviated to fit 20 chars)
- Include niche terms: bois laser, gravure laser, stencil, decoupe laser
- Include theme-specific keywords that buyers actually search for
- NO accents in tags: "decoupe" not "découpe", "laser" is fine
- NO commas, NO special chars, NO hashtags within individual tags
- Each tag is a short phrase or keyword, max 20 chars

=== CRITICAL QUALITY RULES ===
- NEVER truncate any part of the description templates
- NEVER use trademarked character or brand names
- Ensure the full JSON is syntactically valid
- All string values must be properly escaped (quotes, newlines use \\n)
"""


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Read an image file and return a base64-encoded data URI string."""
    if not image_path or not os.path.exists(image_path):
        print(f"[gemini_seo] Image not found: {image_path}")
        return None
    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
        mime_type = "image/png"
        if image_path.lower().endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        encoded = base64.b64encode(img_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        print(f"[gemini_seo] Failed to encode image: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE ANALYSIS PROMPT
# ─────────────────────────────────────────────────────────────────────────────

IMAGE_ANALYSIS_PROMPT = """Analyze this laser cut stencil/image in detail. Describe EXACTLY what you see:

1. What is the main subject/design? (e.g., "a geometric deer head", "a lotus flower mandala", "an owl with graduation cap")
2. What style is it? (e.g., "geometric", "mandala", "minimalist", "tribal", "floral", "celtique")
3. What specific elements/details can you identify? (e.g., "antlers with sharp angles", "petal layers", "feather patterns")
4. What categories/themes does this belong to? (e.g., "animals", "nature", "spiritual", "seasonal")
5. What would be the most searched keywords on Etsy for this specific design?

Be precise and specific. This analysis will be used to generate SEO-optimized Etsy product listings."""


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def build_seo_context_from_history(db) -> str:
    """
    Extrait les 5 dernières créations publiées de la DB pour injecter
    des formules gagnantes dans le prompt Gemini.
    """
    try:
        from ..models import Creation
        past = (
            db.query(Creation)
            .filter(
                Creation.title_en.isnot(None),
                Creation.title_en != "",
            )
            .order_by(Creation.timestamp.desc())
            .limit(5)
            .all()
        )
        if not past:
            return ""

        examples = "\n".join(
            f"- Title FR: {(c.title_fr or '')[:80]} | Tags FR: {(c.tags_fr or '')[:60]}\n"
            f"  Title EN: {(c.title_en or '')[:80]} | Tags EN: {(c.tags_en or '')[:60]}"
            for c in past
        )
        return (
            "\n=== HISTORICAL WINNING LISTINGS (adapt their keyword patterns, do NOT copy) ===\n"
            + examples
            + "\n=== END HISTORICAL CONTEXT ===\n"
        )
    except Exception as e:
        print(f"[gemini_seo] Could not fetch history: {e}")
        return ""


def clean_json(raw_text: str) -> dict:
    """
    Extrait et parse le premier objet JSON valide dans une réponse LLM.
    Gère les réponses avec du texte parasite avant/après le JSON.
    """
    # Supprimer les blocs markdown si présents
    raw_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip()
    raw_text = re.sub(r"```\s*$", "", raw_text).strip()

    # Trouver les accolades ouvrante/fermante
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No valid JSON object found in response")

    json_str = raw_text[start:end]
    return json.loads(json_str)


def validate_seo_structure(data: dict) -> list:
    """
    Valide que tous les champs requis sont présents et non-vides.
    Retourne une liste d'erreurs (vide si tout est OK).
    """
    errors = []
    if "description" in data and "description_fr" not in data:
        data["description_fr"] = data["description"]

    required_fields = ["title_fr", "title_en", "description_fr", "description_en", "tags_fr", "tags_en"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing field: {field}")
        elif not data[field]:
            errors.append(f"Empty field: {field}")

    if "title_fr" in data and data.get("title_fr") and len(data["title_fr"]) > 140:
        errors.append(f"title_fr exceeds 140 chars: {len(data['title_fr'])}")
    if "title_en" in data and data.get("title_en") and len(data["title_en"]) > 140:
        errors.append(f"title_en exceeds 140 chars: {len(data['title_en'])}")

    for lang in ("tags_fr", "tags_en"):
        if lang in data and isinstance(data[lang], list):
            if len(data[lang]) != 13:
                errors.append(f"{lang} has {len(data[lang])} tags (exactly 13 required)")
            too_long = [tag for tag in data[lang] if len(str(tag)) > 20]
            if too_long:
                errors.append(f"{lang} contains tags longer than 20 chars: {too_long[:3]}")
        elif lang in data:
            errors.append(f"{lang} must be a list")

    for desc_field in ("description_fr", "description_en"):
        if desc_field in data and data.get(desc_field):
            desc = str(data[desc_field])
            required_markers = [
                "FORMATS" if desc_field == "description_fr" else "FORMATS",
                "TÉLÉCHARGEMENT" if desc_field == "description_fr" else "DIGITAL DOWNLOAD",
                "Conditions" if desc_field == "description_fr" else "Terms of Use",
                "https://digitalfilesbymop.etsy.com/listing/4499076966",
                "https://digitalfilesbymop.etsy.com/listing/4499075567",
            ]
            missing_markers = [marker for marker in required_markers if marker not in desc]
            if missing_markers:
                errors.append(f"{desc_field} missing required template sections: {missing_markers}")

    return errors


def _ascii_tag(value: str) -> str:
    """Normalise un tag Etsy : ASCII, sans ponctuation exotique, max 20 chars."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9 ]+", " ", value).lower()
    value = re.sub(r"\s+", " ", value).strip()
    return value[:20].strip()


def _normalize_tags_with_order(raw_tags: list, fallback: list[str], theme_tags: list[str] = None) -> list[str]:
    """
    Normalise les tags en gardant l'ordre d'importance.
    Les tags fournis par l'IA (theme_tags) passent en premier,
    puis les tags de l'API, puis les fallbacks.
    """
    items = []
    seen = set()

    # 1. Add theme-specific tags first (most relevant)
    if theme_tags:
        for t in theme_tags:
            tag = _ascii_tag(t)
            if tag and tag not in seen:
                items.append(tag)
                seen.add(tag)

    # 2. Add tags from raw_tags
    if isinstance(raw_tags, list):
        for t in raw_tags:
            tag = _ascii_tag(t)
            if tag and tag not in seen:
                items.append(tag)
                seen.add(tag)
    elif isinstance(raw_tags, str):
        for t in raw_tags.split(","):
            tag = _ascii_tag(t.strip())
            if tag and tag not in seen:
                items.append(tag)
                seen.add(tag)

    # 3. Add fallback tags to fill
    for t in fallback:
        tag = _ascii_tag(t)
        if tag and tag not in seen:
            items.append(tag)
            seen.add(tag)
        if len(items) >= 13:
            break

    return items[:13]


def _safe_title(title: str, fallback: str) -> str:
    title = re.sub(r"\s+", " ", (title or fallback)).strip()
    if len(title) <= 140:
        return title
    return title[:137].rstrip(" |,-") + "..."


def _theme_label(theme: str) -> str:
    return re.sub(r"\s+", " ", theme.strip() or "Design Laser").title()[:80]


def _build_fallback_seo(theme: str) -> dict:
    label = _theme_label(theme)
    return {
        "title_fr": _safe_title(
            f"🌿 {label} SVG DXF EPS AI PDF | Découpe Laser Cricut Silhouette | Pochoir Bois",
            f"🌿 {label} SVG DXF EPS AI PDF | Découpe Laser Cricut Silhouette | Pochoir Bois",
        ),
        "title_en": _safe_title(
            f"🌿 {label} SVG DXF EPS AI PDF | Laser Cut Cricut Silhouette | Wood Stencil",
            f"🌿 {label} SVG DXF EPS AI PDF | Laser Cut Cricut Silhouette | Wood Stencil",
        ),
        "description": (
            f"🌿 {label} - Fichier numérique SVG DXF pour découpe laser\n\n"
            f"Design exclusif sur le thème {label}, optimisé pour la découpe et gravure laser. "
            "Parfait pour vos projets de décoration personnalisée.\n\n"
            "📁 FORMATS DE FICHIERS INCLUS\n\n"
            "Vous recevrez les fichiers en haute qualité :\n"
            "- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser\n"
            "- PNG – fond transparent, haute résolution\n"
            "- DXF – Silhouette Studio, machines laser\n"
            "- EPS – fichiers vectoriels éditables\n"
            "- PDF - Impression\n\n"
            "✔ Compatibles avec :\n"
            "Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, laser CO₂, laser diode, CNC\n\n"
            "📥 TÉLÉCHARGEMENT NUMÉRIQUE\n\n"
            "📌 Produit numérique – aucun article physique envoyé\n"
            "Téléchargement immédiat après achat sur Etsy.\n\n"
            "📜 Conditions d'utilisation\n\n"
            "✔ Utilisation personnelle\n\n"
            "✔ Utilisation commerciale autorisée sur produits finis :\n"
            "Licence commerciale requise. Pour utiliser ce fichier à des fins commerciales, une licence est obligatoire.\n\n"
            "👉 Licences disponibles :\n"
            "https://digitalfilesbymop.etsy.com/listing/4499076966\n"
            "https://digitalfilesbymop.etsy.com/listing/4499075567\n\n"
            "❌ Revente, partage ou redistribution des fichiers interdits"
        ),
        "description_fr": (
            f"🌿 {label} - Fichier numérique SVG DXF pour découpe laser\n\n"
            f"Design exclusif sur le thème {label}, optimisé pour la découpe et gravure laser. "
            "Parfait pour vos projets de décoration personnalisée.\n\n"
            "📁 FORMATS DE FICHIERS INCLUS\n\n"
            "Vous recevrez les fichiers en haute qualité :\n"
            "- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser\n"
            "- PNG – fond transparent, haute résolution\n"
            "- DXF – Silhouette Studio, machines laser\n"
            "- EPS – fichiers vectoriels éditables\n"
            "- PDF - Impression\n\n"
            "✔ Compatibles avec :\n"
            "Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, laser CO₂, laser diode, CNC\n\n"
            "📥 TÉLÉCHARGEMENT NUMÉRIQUE\n\n"
            "📌 Produit numérique – aucun article physique envoyé\n"
            "Téléchargement immédiat après achat sur Etsy.\n\n"
            "📜 Conditions d'utilisation\n\n"
            "✔ Utilisation personnelle\n\n"
            "✔ Utilisation commerciale autorisée sur produits finis :\n"
            "Licence commerciale requise. Pour utiliser ce fichier à des fins commerciales, une licence est obligatoire.\n\n"
            "👉 Licences disponibles :\n"
            "https://digitalfilesbymop.etsy.com/listing/4499076966\n"
            "https://digitalfilesbymop.etsy.com/listing/4499075567\n\n"
            "❌ Revente, partage ou redistribution des fichiers interdits"
        ),
        "description_en": (
            f"🌿 {label} - Digital SVG DXF Laser Cut File\n\n"
            f"Exclusive design on the theme of {label}, optimized for laser cutting and engraving. "
            "Perfect for your personalized decoration projects.\n\n"
            "📁 INCLUDED FILE FORMATS\n\n"
            "You will receive high quality files:\n"
            "- SVG – Cricut, Silhouette, Glowforge, Xtool, Laser\n"
            "- PNG – transparent background, high resolution\n"
            "- DXF – Silhouette Studio, laser machines\n"
            "- EPS – editable vector files\n"
            "- PDF - Print\n\n"
            "✔ Compatible with:\n"
            "Cricut Design Space, Silhouette Studio, LightBurn, Glowforge, CO₂ laser, diode laser, CNC\n\n"
            "📥 DIGITAL DOWNLOAD\n\n"
            "📌 Digital product – no physical item will be shipped\n"
            "Instant download after purchase on Etsy.\n\n"
            "📜 Terms of Use\n\n"
            "✔ Personal use\n\n"
            "✔ Commercial use allowed on finished products:\n"
            "Commercial license required.\n\n"
            "👉 Licenses available:\n"
            "https://digitalfilesbymop.etsy.com/listing/4499076966\n"
            "https://digitalfilesbymop.etsy.com/listing/4499075567\n\n"
            "❌ Resale, sharing or redistribution of files is prohibited"
        ),
        "tags_fr": _normalize_tags_with_order([], [
            "fichier svg", "decoupe laser", "fichier dxf", "stencil laser", "fichier eps",
            "fichier ai", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
            "bois laser", "gravure laser", label.lower()[:20],
        ]),
        "tags_en": _normalize_tags_with_order([], [
            "svg file", "laser cut file", "dxf file", "laser stencil", "eps file",
            "ai file", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
            "wood laser", "laser engrave", label.lower()[:20],
        ]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def generate_etsy_seo(theme: str, gemini_key: str, db=None, image_path: str = None) -> dict:
    """
    Génère un package SEO Etsy bilingue complet via Gemini 2.0 Flash Lite.
    Analyse l'image source si disponible pour générer un contenu spécifique et précis.

    Args:
        theme: Thème du design (ex: "Mandala fleur de lotus")
        gemini_key: Clé API Google Gemini
        db: Session SQLAlchemy optionnelle pour injecter le contexte historique
        image_path: Chemin vers l'image source PNG pour analyse visuelle

    Returns:
        dict avec title_fr, title_en, description_fr, description_en, tags_fr, tags_en

    Raises:
        Aucune exception — retourne toujours un résultat (fallback si nécessaire)
    """
    if not gemini_key or not gemini_key.strip():
        print("[gemini_seo] No Gemini API key — using local fallback")
        return _build_fallback_seo(theme)

    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
    except ImportError:
        print("[gemini_seo] google-genai not installed — using local fallback")
        return _build_fallback_seo(theme)
    except Exception as e:
        print(f"[gemini_seo] Failed to init Gemini: {e} — using local fallback")
        return _build_fallback_seo(theme)

    # ── Phase 1: Analyze image with Gemini Vision ──────────────────────────────
    image_analysis_text = None
    if image_path and os.path.exists(image_path):
        try:
            print(f"[gemini_seo] Analyzing image: {image_path}")
            base64_image = encode_image_to_base64(image_path)
            if base64_image:
                # Use gemini-2.0-flash-lite for image analysis (faster, cheaper)
                img_response = client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=[
                        IMAGE_ANALYSIS_PROMPT,
                        {"mime_type": "image/png" if not image_path.lower().endswith((".jpg", ".jpeg")) else "image/jpeg",
                         "data": base64_image},
                    ],
                    config=genai.types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=1024,
                    ),
                    request_options={"timeout": 30},
                )
                image_analysis_text = img_response.text.strip()
                print(f"[gemini_seo] Image analysis result: {image_analysis_text[:200]}...")
        except Exception as e:
            print(f"[gemini_seo] Image analysis failed: {e}")
            image_analysis_text = None

    # ── Phase 2: Generate SEO with Flash Lite ─────────────────────────────────
    history_context = build_seo_context_from_history(db) if db else ""

    # Build user message with image analysis context if available
    user_message_parts = []
    if history_context:
        user_message_parts.append(history_context)

    if image_analysis_text:
        user_message_parts.append(
            f"=== IMAGE ANALYSIS (use this to describe the design precisely) ===\n"
            f"{image_analysis_text}\n"
            f"=== END IMAGE ANALYSIS ===\n\n"
        )

    user_message_parts.append(
        f"Generate a complete bilingual Etsy SEO package for a laser cutting digital product.\n"
        f'USER THEME: "{theme}"\n\n'
        "Use the image analysis above to write PRECISE, SPECIFIC titles and descriptions "
        "that accurately describe what the design actually looks like. "
        "The titles and descriptions MUST be tailored to this specific design, not generic templates.\n\n"
        "Follow ALL rules from the system prompt exactly. "
        "Return ONLY the JSON object — no other text."
    )

    user_message = "\n".join(user_message_parts)

    # ── Retry loop : 2 tentatives avec Gemini 2.0 Flash Lite ─────────────────
    last_error = None
    for attempt in range(1, 3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=OPTIMIZED_TEXT_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.7,
                    max_output_tokens=8192,
                ),
                request_options={"timeout": 120},
            )

            # Vérifier la raison d'arrêt de la génération
            finish_reason = None
            try:
                finish_reason = response.candidates[0].finish_reason
                if str(finish_reason) in ("MAX_TOKENS", "2"):
                    print(f"[gemini_seo] Attempt {attempt}: Response truncated (MAX_TOKENS). Retrying...")
                    last_error = "Response truncated by MAX_TOKENS"
                    time.sleep(1)
                    continue
            except (IndexError, AttributeError):
                pass  # finish_reason non disponible, continuer

            raw_text = response.text.strip()
            data = clean_json(raw_text)

            # Valider la structure
            errors = validate_seo_structure(data)
            if errors:
                print(f"[gemini_seo] Attempt {attempt}: Validation errors: {errors}")
                last_error = f"Validation: {errors}"
                time.sleep(1)
                continue

            # Normalize with better tag ordering
            label = _theme_label(theme)
            fallback_fr = [
                "fichier svg", "decoupe laser", "fichier dxf", "stencil laser", "fichier eps",
                "fichier ai", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
                "bois laser", "gravure laser", label.lower()[:20],
            ]
            fallback_en = [
                "svg file", "laser cut file", "dxf file", "laser stencil", "eps file",
                "ai file", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
                "wood laser", "laser engrave", label.lower()[:20],
            ]

            # Extract theme-specific tags from analysis to put them first
            theme_tags_fr = [t for t in data.get("tags_fr", []) if len(_ascii_tag(t)) > 3]
            theme_tags_en = [t for t in data.get("tags_en", []) if len(_ascii_tag(t)) > 3]

            normalized = {
                "title_fr": _safe_title(
                    data.get("title_fr", ""),
                    f"🌿 {label} SVG DXF EPS AI PDF | Découpe Laser Cricut Silhouette | Pochoir Bois",
                ),
                "title_en": _safe_title(
                    data.get("title_en", ""),
                    f"🌿 {label} SVG DXF EPS AI PDF | Laser Cut Cricut Silhouette | Wood Stencil",
                ),
                "description": data.get("description_fr") or data.get("description", ""),
                "description_fr": data.get("description_fr") or data.get("description", ""),
                "description_en": data.get("description_en", ""),
                "tags_fr": _normalize_tags_with_order(theme_tags_fr, fallback_fr),
                "tags_en": _normalize_tags_with_order(theme_tags_en, fallback_en),
            }

            print(f"[gemini_seo] Success on attempt {attempt}")
            return normalized

        except json.JSONDecodeError as e:
            print(f"[gemini_seo] Attempt {attempt}: JSON parse error: {e}")
            last_error = str(e)
            time.sleep(1.5)
        except Exception as e:
            print(f"[gemini_seo] Attempt {attempt}: API error: {e}")
            last_error = str(e)
            time.sleep(2)

    # ── Fallback Mistral ──────────────────────────────────────────────────
    print(f"[gemini_seo] Gemini failed ({last_error}). Trying Mistral fallback...")
    mistral_result = _try_mistral_fallback(theme, db)
    if mistral_result:
        return mistral_result

    # ── Fallback local ────────────────────────────────────────────────────
    print("[gemini_seo] All AI APIs failed. Using local template fallback.")
    return _build_fallback_seo(theme)


def _try_mistral_fallback(theme: str, db=None) -> Optional[dict]:
    """Tente de générer le SEO via Mistral si disponible en settings."""
    try:
        if db:
            from ..models import Setting
            settings = db.query(Setting).first()
            if not settings or not settings.mistral_key:
                return None

            from mistralai.client import MistralClient
            from mistralai.models.chat_completion import ChatMessage

            client = MistralClient(api_key=settings.mistral_key)
            messages = [
                ChatMessage(role="system", content=OPTIMIZED_TEXT_SYSTEM_PROMPT),
                ChatMessage(role="user", content=(
                    f'Generate a bilingual Etsy SEO package for theme: "{theme}". '
                    "Return ONLY valid JSON."
                )),
            ]
            resp = client.chat(model="mistral-medium", messages=messages, max_tokens=4096)
            raw = resp.choices[0].message.content
            data = clean_json(raw)
            errors = validate_seo_structure(data)
            if not errors:
                label = _theme_label(theme)
                fallback_fr = [
                    "fichier svg", "decoupe laser", "fichier dxf", "stencil laser", "fichier eps",
                    "fichier ai", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
                    "bois laser", "gravure laser", label.lower()[:20],
                ]
                fallback_en = [
                    "svg file", "laser cut file", "dxf file", "laser stencil", "eps file",
                    "ai file", "cricut svg", "silhouette svg", "glowforge svg", "xtool laser",
                    "wood laser", "laser engrave", label.lower()[:20],
                ]
                return {
                    "title_fr": _safe_title(data.get("title_fr", ""), f"🌿 {label} SVG DXF EPS AI PDF | Découpe Laser Cricut Silhouette | Pochoir Bois"),
                    "title_en": _safe_title(data.get("title_en", ""), f"🌿 {label} SVG DXF EPS AI PDF | Laser Cut Cricut Silhouette | Wood Stencil"),
                    "description": data.get("description_fr") or data.get("description", ""),
                    "description_fr": data.get("description_fr") or data.get("description", ""),
                    "description_en": data.get("description_en", ""),
                    "tags_fr": _normalize_tags_with_order(data.get("tags_fr", []), fallback_fr),
                    "tags_en": _normalize_tags_with_order(data.get("tags_en", []), fallback_en),
                }
    except Exception as e:
        print(f"[gemini_seo] Mistral fallback failed: {e}")
    return None
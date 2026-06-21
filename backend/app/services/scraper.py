"""
Scraper Service — Banque d'Idées & Tendances Actuelles
Aggregates real-world trending digital craft files and stencils from general web searches (via Yahoo organic product results, which bypasses cloudflare blocks and returns proxied image URLs) and Creative Fabrica / Design Bundles.
Includes an AI-driven generator that calls the configured LLM (Gemini or Mistral) to propose seasonal concept ideas.
"""

import json
import re
import time
import random
import urllib.parse
from collections import Counter
from datetime import datetime, date
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from app.models import IdeaBank
from app.routers.settings import get_or_create_settings
from openai import OpenAI

# Pool of rotating headers
HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    },
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }
]

# Static fallback image URLs from Unsplash for laser-cut/wood aesthetic
FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1615840287214-7fe58a8b668f?w=600&q=80",
    "https://images.unsplash.com/photo-1606744824163-985d376605aa?w=600&q=80",
    "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=600&q=80",
    "https://images.unsplash.com/photo-1507608869274-d3177c8bb4c7?w=600&q=80",
    "https://images.unsplash.com/photo-1444492442229-16b3474eb5e6?w=600&q=80"
]

def _get_seasonal_context() -> dict:
    """Retourne le contexte saisonnier basé sur la date courante."""
    today = date.today()
    month = today.month

    seasons = {
        1:  {"label": "Nouvel An / Hiver",     "keywords": ["hiver", "neige", "nouvel an"], "category": "Winter"},
        2:  {"label": "Saint-Valentin",         "keywords": ["amour", "coeur", "saint valentin"], "category": "Valentine"},
        3:  {"label": "Printemps / Pâques",     "keywords": ["printemps", "paques", "lapin"], "category": "Spring"},
        4:  {"label": "Printemps / Nature",     "keywords": ["jardin", "fleur", "nature"], "category": "Spring"},
        5:  {"label": "Fête des Mères / Jardin","keywords": ["mere", "jardin", "mariage"], "category": "Mother"},
        6:  {"label": "Été / Mariage",          "keywords": ["ete", "mariage", "soleil"], "category": "Summer"},
        7:  {"label": "Été / Vacances",         "keywords": ["ete", "vacances", "plage"], "category": "Summer"},
        8:  {"label": "Fin d'été / Rentrée",    "keywords": ["rentree", "ecole", "crayon"], "category": "BackToSchool"},
        9:  {"label": "Automne / Rentrée",      "keywords": ["automne", "feuille", "ecole"], "category": "Autumn"},
        10: {"label": "Halloween / Automne",    "keywords": ["halloween", "citrouille", "fantome"], "category": "Halloween"},
        11: {"label": "Noël / Hiver",           "keywords": ["noel", "sapin", "etoile"], "category": "Christmas"},
        12: {"label": "Noël / Nouvel An",       "keywords": ["noel", "sapin", "flocon"], "category": "Christmas"},
    }
    return seasons.get(month, {"label": "Générique", "keywords": ["laser", "svg", "dxf"], "category": "General"})


def _get_etsy_api_key(db) -> Optional[str]:
    """Extrait la clé API Etsy configurée."""
    settings = get_or_create_settings(db)
    if settings and settings.etsy_client_id and settings.etsy_client_id.strip():
        return settings.etsy_client_id.strip()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# YAHOO ORGANIC PRODUCT SEARCH (UNBLOCKED THUMBNAILS & DIRECT LINKS)
# ─────────────────────────────────────────────────────────────────────────────

def _scrape_yahoo_products(query: str, section: str, max_items: int = 8) -> List[dict]:
    """
    Interroge Yahoo Search pour en extraire des résultats de produits réels
    (Etsy, Creative Fabrica, Pinterest, Design Bundles) accompagnés de visuels.
    Yahoo utilise un CDN proxy d'images non bloqué qui s'affiche parfaitement.
    """
    items = []
    try:
        # Request delay before firing to prevent basic rate limiters
        time.sleep(random.uniform(0.5, 2.0))

        encoded_q = urllib.parse.quote_plus(query)
        url = f"https://search.yahoo.com/search?q={encoded_q}"
        headers = random.choice(HEADERS_POOL)
        
        try:
            resp = requests.get(url, headers=headers, timeout=8, proxies={"http": None, "https": None})
            if resp.status_code != 200:
                print(f"[scraper_yahoo] Code non-200 pour '{query}': {resp.status_code}")
                return items
        except requests.exceptions.Timeout:
            print(f"[scraper_yahoo] Timeout atteint pour la requête '{query}'. Saut gracieux.")
            return items
        except requests.exceptions.RequestException as req_err:
            print(f"[scraper_yahoo] Erreur de requête pour '{query}': {req_err}. Saut gracieux.")
            return items
            
        # Fallback BeautifulSoup parsers to bridge parsing glitches
        soup = None
        for parser in ["html.parser", "lxml", "html5lib"]:
            try:
                temp_soup = BeautifulSoup(resp.content, parser)
                if temp_soup.find_all("a", href=True):
                    soup = temp_soup
                    break
            except Exception:
                continue
        
        if not soup:
            soup = BeautifulSoup(resp.content, "html.parser")
        
        for a in soup.find_all("a", href=True):
            img = a.find("img")
            if img and img.get("src") and "yimg.com" in img["src"] and "favicon" not in img["src"]:
                href = a["href"]
                dest = href
                if "RU=" in href:
                    m = re.search(r"RU=([^&]+)", href)
                    if m:
                        dest = urllib.parse.unquote(m.group(1))
                
                # Validation de produit réel spécifique
                is_product = False
                source_name = "internet"
                if "etsy.com" in dest:
                    if "/listing/" in dest:
                        is_product = True
                        source_name = "etsy"
                elif "pinterest.com" in dest:
                    if "/pin/" in dest or "/pin-" in dest:
                        is_product = True
                        source_name = "pinterest"
                elif "creativefabrica.com" in dest:
                    if "/product/" in dest:
                        is_product = True
                        source_name = "creative_fabrica"
                elif "designbundles.net" in dest:
                    if not any(x in dest for x in ["/search", "/free-design-resources", "/store", "/category"]):
                        is_product = True
                        source_name = "design_bundles"
                else:
                    # Produits généraux d'autres sites web (Vecteezy, boutiques Shopify, etc.)
                    # Exclure les moteurs de recherche et sites généraux connus
                    if not any(x in dest.lower() for x in ["/search", "query=", "tags=", "/category", "/market", "google.com", "bing.com", "yahoo.com", "youtube.com", "wikipedia.org"]):
                        # Assurer que l'URL a au moins deux sous-chemins (indique une fiche produit)
                        parsed_uri = urllib.parse.urlparse(dest)
                        path_parts = [p for p in parsed_uri.path.split("/") if p.strip()]
                        if len(path_parts) >= 2:
                            is_product = True
                            source_name = "internet"
                
                if is_product:
                    if any(x["source_url"] == dest for x in items):
                        continue
                        
                    title = img.get("alt") or img.get("title") or a.get("title") or a.get_text().strip()
                    if not title or len(title.strip()) < 5:
                        slug = dest.rstrip("/").split("/")[-1]
                        slug = re.sub(r"^\d+", "", slug)
                        title = slug.replace("-", " ").replace("_", " ").strip().title()
                    
                    # Nettoyer le titre
                    title = re.sub(r"\s+", " ", title).strip()
                    title = re.sub(r"\s*\|\s*(?:3d|cnc|laser|cricut|silhouette|dxf|svg|dossier|fichier).*$", "", title, flags=re.IGNORECASE)
                    
                    items.append({
                        "listing_id": str(abs(hash(dest))),
                        "title": title[:110],
                        "description": f"Produit populaire détecté sur {source_name.title()} via les tendances actuelles.",
                        "source_url": dest,
                        "thumbnail_url": img["src"],
                        "query": query,
                        "badge_bonus": 30 if section == "popular" else 15,
                        "section": section,
                        "source": source_name,
                    })
                    if len(items) >= max_items:
                        break
    except Exception as e:
        print(f"[scraper_yahoo] Échec sur '{query}': {e}")
    return items


# ─────────────────────────────────────────────────────────────────────────────
# AI CONCEPT IDEAS GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def _clean_json_api(raw_text: str):
    """Extrait proprement un tableau ou un objet JSON d'une chaîne LLM."""
    text = re.sub(r"```(?:json)?\s*", "", raw_text or "").strip()
    text = re.sub(r"```\s*$", "", text).strip()
    
    start_arr = text.find("[")
    end_arr = text.rfind("]") + 1
    
    start_obj = text.find("{")
    end_obj = text.rfind("}") + 1
    
    if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        json_str = text[start_arr:end_arr]
    elif start_obj != -1:
        json_str = text[start_obj:end_obj]
    else:
        raise ValueError("Format JSON introuvable dans la réponse")
        
    return json.loads(json_str)


def _try_concepts_gemini(api_key: str, model: str, prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=api_key.strip())
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.8,
            max_output_tokens=2048,
            response_mime_type="application/json"
        )
    )
    return response.text.strip()


def _try_concepts_openai(api_key: str, model: str, prompt: str) -> str:
    client = OpenAI(
        api_key=api_key.strip(),
        base_url="https://api.openai.com/v1"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content.strip()


def _try_concepts_claude(api_key: str, model: str, prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key.strip(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022" if "3-5" in model else "claude-3-opus-20240229",
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt + "\n\nIMPORTANT: Return ONLY a raw JSON array of objects starting with [ and ending with ]."}
        ]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()

def _try_concepts_mistral(api_key: str, model: str, prompt: str) -> str:
    from mistralai import Mistral
    
    # Initialisation avec le nouveau client synchrone / asynchrone unifié
    client = Mistral(api_key=api_key.strip())
    
    # Le modèle par défaut si le provider n'est pas propre
    model_to_use = model if model.startswith("mistral") else "mistral-large-latest"
    
    # Appel de l'API avec la nouvelle syntaxe client.chat.complete
    resp = client.chat.complete(
        model=model_to_use,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        # Optionnel mais recommandé pour forcer le JSON si le modèle le supporte
        response_format={"type": "json_object"} 
    )
    
    return resp.choices[0].message.content.strip()
def _try_concepts_openrouter(api_key: str, model: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key.strip()
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=2048
    )
    return response.choices[0].message.content.strip()


def generate_concept_ideas_via_ai(db) -> List[dict]:
    """
    Appelle l'IA pour générer 10 idées de concepts de motifs vectoriels
    basées sur les thèmes populaires et le mois de l'année courant.
    """
    settings = get_or_create_settings(db)
    provider = getattr(settings, "text_ai_provider", "gemini-2.0-flash-lite")
    
    # Extract keys
    gemini_key = (getattr(settings, "gemini_key", "") or "").strip()
    openai_key = (getattr(settings, "openai_key", "") or "").strip()
    anthropic_key = (getattr(settings, "anthropic_key", "") or "").strip()
    mistral_key = (getattr(settings, "mistral_key", "") or "").strip()
    openrouter_key = (getattr(settings, "openrouter_key", "") or "").strip()
    
    season = _get_seasonal_context()
    
    prompt = f"""You are an expert market analyst in digital files and laser-cutting designs (SVG, DXF).
Analyze the current date/season context: Month {datetime.today().month} ({season['label']}).
Generate 10 highly trending, original, and highly profitable concept ideas for digital laser-cut designs.
For each concept, provide:
1. Title: A clean, commercial product title (French).
2. Description: Why it is trending, what materials to use, and why it sells (French).
3. Category: The theme category (e.g. Nature, Animals, Geometric, Wedding, Halloween, Christmas, etc.).
4. Trend Score: An integer from 80 to 99 based on expected popularity.
5. Keywords: A list of 5 relevant search keywords (French).

Respond strictly with a JSON array of objects. Do not wrap it in markdown or add explanations.
The JSON structure must be:
[
  {{
    "title": "...",
    "description": "...",
    "category": "...",
    "trend_score": 90,
    "keywords": ["...", "...", "..."]
  }}
]
"""

    # Normalize provider
    p_pref = provider.lower().strip() if provider else "gemini-2.0-flash-lite"
    if p_pref in ("claude-3-5-sonnet", "claude-3-opus", "claude"):
        p_pref = "claude"
    elif p_pref in ("gpt-4o", "gpt-4o-mini", "openai"):
        p_pref = "openai"
    elif p_pref.startswith("gemini"):
        p_pref = "gemini"
    elif p_pref.startswith("mistral"):
        p_pref = "mistral"
    elif "openrouter" in p_pref:
        p_pref = "openrouter"

    # Priority fallback loop
    all_providers = ["gemini", "openai", "claude", "mistral", "openrouter"]
    if p_pref in all_providers:
        all_providers.remove(p_pref)
        priority_list = [p_pref] + all_providers
    else:
        priority_list = [p_pref] + all_providers

    raw_text = None
    errors = []
    
    for p in priority_list:
        try:
            if p == "gemini" and gemini_key:
                model_name = provider if provider.startswith("gemini") else "gemini-2.0-flash-lite"
                raw_text = _try_concepts_gemini(gemini_key, model_name, prompt)
            elif p == "openai" and openai_key:
                model_name = provider if (provider.startswith("gpt") or provider == "openai") else "gpt-4o-mini"
                raw_text = _try_concepts_openai(openai_key, model_name, prompt)
            elif p == "claude" and anthropic_key:
                model_name = provider if "claude" in provider else "claude-3-5-sonnet"
                raw_text = _try_concepts_claude(anthropic_key, model_name, prompt)
            elif p == "mistral" and mistral_key:
                model_name = provider if provider.startswith("mistral") else "mistral-large-latest"
                raw_text = _try_concepts_mistral(mistral_key, model_name, prompt)
            elif p == "openrouter" and openrouter_key:
                model_name = provider if "openrouter" in provider else "google/flux-active"
                if model_name == "google/flux-active" or "flux" in model_name:
                    # If model is configured as flux, fall back to llama for text generation
                    model_name = "meta-llama/llama-3-70b-instruct"
                raw_text = _try_concepts_openrouter(openrouter_key, model_name, prompt)
            
            if raw_text:
                print(f"[scraper_ai] Concept generation succeeded via provider: {p}")
                break
        except Exception as e:
            err_msg = f"{p} failed: {str(e)}"
            print(f"[scraper_ai] {err_msg}")
            errors.append(err_msg)

    if not raw_text:
        print(f"[scraper_ai] Fallback local concepts. Errors: {'; '.join(errors)}")
        return _generate_fallback_concepts(season)

    try:
        data = _clean_json_api(raw_text)
        if isinstance(data, list):
            concepts = []
            for item in data:
                title = item.get("title", "").strip()
                if not title:
                    continue
                query_encoded = urllib.parse.quote_plus(title + " laser cut")
                source_url = f"https://www.etsy.com/search?q={query_encoded}"
                
                concepts.append({
                    "title": title,
                    "description": item.get("description", ""),
                    "thumbnail_url": None,
                    "source_url": source_url,
                    "trend_score": item.get("trend_score", 85),
                    "category": item.get("category", "General"),
                    "keywords": json.dumps(item.get("keywords", [])),
                    "section": "ideas",
                    "source": "ai_generation"
                })
            return concepts
    except Exception as e:
        print(f"[scraper_ai] JSON parse error: {e}. Raw was: {raw_text[:200]}")
        
    return _generate_fallback_concepts(season)


def _generate_fallback_concepts(season: dict) -> List[dict]:
    """Idées de repli locales si l'IA échoue."""
    category = season["category"]
    label = season["label"]
    
    raw = [
        {
            "title": f"Trophée Animal Origami 3D - Fichier Découpe Laser Bois",
            "description": f"Concept de puzzle 3D en bois à assembler. Très recherché pour la décoration d'intérieur style scandinave, thème {label}.",
            "category": "Animal",
            "trend_score": 93,
            "keywords": ["origami 3d", "trophee bois", "puzzle 3d", "laser cut", "cerf"]
        },
        {
            "title": f"Veilleuse Mandala Multicouche - SVG Luminaire Découpé",
            "description": f"Luminaire à strates superposées créant un effet de profondeur en bois. Idéal pour éclairage d'ambiance de saison {label}.",
            "category": "Mandala",
            "trend_score": 89,
            "keywords": ["veilleuse mandala", "luminaire bois", "multicouche svg", "laser stencil", "deco zen"]
        },
        {
            "title": f"Pack Marque-Pages Gravés {label} - SVG Lot de 6",
            "description": "Fichiers de découpe fins et rapides pour chutes de bois ou cuir. Fort potentiel de vente en lot cadeau.",
            "category": category,
            "trend_score": 85,
            "keywords": ["marque page", "gravure rapide", "chute bois", "cadeau original", "svg lot"]
        }
    ]
    
    concepts = []
    for item in raw:
        query_encoded = urllib.parse.quote_plus(item["title"] + " laser cut")
        concepts.append({
            "title": item["title"],
            "description": item["description"],
            "thumbnail_url": None,
            "source_url": f"https://www.etsy.com/search?q={query_encoded}",
            "trend_score": item["trend_score"],
            "category": item["category"],
            "keywords": json.dumps(item["keywords"]),
            "section": "ideas",
            "source": "fallback"
        })
    return concepts


# ─────────────────────────────────────────────────────────────────────────────
# AUTOMATIC SCORE & CATEGORIZATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_keywords(title: str) -> List[str]:
    title_lower = title.lower()
    clean = re.sub(r'\b(svg|dxf|eps|pdf|png|ai|cnc|laser|cricut|silhouette|glowforge|xtool|lightburn)\b', '', title_lower)
    clean = re.sub(r'[^\w\s]', ' ', clean)
    words = [w.strip() for w in clean.split() if len(w.strip()) > 3]
    seen, keywords = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            keywords.append(w)
        if len(keywords) >= 5:
            break
    return keywords


def _detect_category(title: str) -> str:
    title_lower = title.lower()
    category_map = {
        "Halloween":    ["halloween", "pumpkin", "citrouille", "ghost", "fantome", "bat", "witch", "sorciere"],
        "Christmas":    ["christmas", "noel", "xmas", "sapin", "santa", "reindeer", "snowflake", "flocon"],
        "Valentine":    ["valentine", "heart", "coeur", "love", "amour", "rose"],
        "Easter":       ["easter", "paques", "bunny", "lapin", "egg"],
        "Mother":       ["mother", "mama", "maman", "mere", "mom"],
        "Wedding":      ["wedding", "mariage", "bride", "mariee", "floral"],
        "Nature":       ["tree", "arbre", "flower", "fleur", "leaf", "feuille", "bird", "oiseau", "forest"],
        "Animal":       ["cat", "chat", "dog", "chien", "fox", "renard", "wolf", "deer", "cerf", "owl", "hibou"],
        "Mandala":      ["mandala", "lotus", "zen", "geometric"],
        "Geometric":    ["geometric", "geometrique", "hexagon", "hexagone", "triangle"],
        "BackToSchool": ["school", "ecole", "teacher", "professeur", "student", "etudiant", "graduation"],
        "Summer":       ["summer", "ete", "beach", "plage", "tropical", "sun", "soleil"],
    }
    for category, terms in category_map.items():
        if any(term in title_lower for term in terms):
            return category
    return "General"


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_full_scrape(db):
    """
    Scrape et synchronise les tendances :
    1. Supprime les tendances non verrouillées (non injectées).
    2. Appelle l'IA (ou repli) pour peupler la section "Idées de concepts".
    3. Scrape Yahoo Search pour extraire des PRODUITS RÉELS avec IMAGES pour les tendances et les populaires.
    4. Enregistre en base de données.
    """
    season = _get_seasonal_context()
    yield {"step": 1, "msg": f"Initialisation. Contexte saisonnier : {season['label']}"}

    # 1. Purger les anciennes tendances non injectées
    try:
        db.query(IdeaBank).filter(IdeaBank.is_injected == False).delete()
        db.commit()
    except Exception as e:
        print(f"[scraper] Clear db error: {e}")

    # 2. Section "Idées de concepts" via IA
    yield {"step": 2, "msg": "Génération des concepts par Intelligence Artificielle..."}
    ai_concepts = generate_concept_ideas_via_ai(db)
    for c in ai_concepts:
        db_item = IdeaBank(
            title=c["title"],
            description=c["description"],
            thumbnail_url=c["thumbnail_url"],
            source_url=c["source_url"],
            trend_score=c["trend_score"],
            section="ideas",
            category=c["category"],
            detected_at=datetime.utcnow(),
            keywords=c["keywords"],
            source=c["source"],
        )
        db.add(db_item)
    db.commit()
    yield {"step": 3, "msg": f"Concepts IA : {len(ai_concepts)} fiches générées."}

    # 3. Section "Tendances du moment" & "Les Plus Populaires (Général)"
    yield {"step": 4, "msg": "Recherche Web : Extraction des Tendances du moment..."}
    
    raw_listings = []
    
    # Récupérer les tendances du moment
    raw_listings.extend(_scrape_yahoo_products("etsy laser cut files svg", "trending", max_items=8))
    raw_listings.extend(_scrape_yahoo_products("creative fabrica laser cut svg", "trending", max_items=8))
    
    yield {"step": 5, "msg": "Recherche Web : Extraction des fichiers Populaires..."}
    # Récupérer les populaires
    raw_listings.extend(_scrape_yahoo_products("pinterest laser cut files wood", "popular", max_items=8))
    raw_listings.extend(_scrape_yahoo_products("design bundles laser cut", "popular", max_items=8))

    # 4. Fallback si échec complet de connexion réseau (aucun produit trouvé)
    if not raw_listings:
        yield {"step": 6, "msg": "Mode Hors-ligne : Chargement des produits de démonstration..."}
        # Charger des produits mockés complets avec de belles images Unsplash
        for idx, img_url in enumerate(FALLBACK_IMAGES):
            title_t = f"Stencil {['Loup Mandalas', 'Fleur de Vie', 'Lanternes Jardin', 'Animaux Forêt', 'Panneaux Directifs'][idx]} SVG DXF"
            title_p = f"Bestseller {['Puzzle Dinosaure', 'Organisateur Bureau', 'Porte-Bijoux', 'Décoration Murale', 'Boîte Secrète'][idx]} Découpe Laser"
            
            raw_listings.append({
                "listing_id": f"mock_t_{idx}",
                "title": title_t,
                "description": "Fichier de découpe laser populaire.",
                "source_url": f"https://www.etsy.com/listing/mock_t_{idx}",
                "thumbnail_url": img_url,
                "badge_bonus": 15,
                "section": "trending",
                "source": "demo"
            })
            raw_listings.append({
                "listing_id": f"mock_p_{idx}",
                "title": title_p,
                "description": "Fichier de découpe laser best-seller.",
                "source_url": f"https://www.etsy.com/listing/mock_p_{idx}",
                "thumbnail_url": img_url,
                "badge_bonus": 30,
                "section": "popular",
                "source": "demo"
            })

    # 5. Dédupliquer et sauvegarder
    yield {"step": 7, "msg": "Analyse finale et sauvegarde en base de données..."}
    seen_titles = set()
    deduplicated = []
    title_counter = Counter()

    for item in raw_listings:
        t = item["title"][:60].lower()
        title_counter[t] += 1

    for item in raw_listings:
        t = item["title"][:60].lower()
        if t not in seen_titles:
            seen_titles.add(t)
            deduplicated.append(item)

    total = len(deduplicated)
    inserted = 0

    for rank, item in enumerate(deduplicated):
        # Règles strictes d'affichage :
        # S'il n'y a pas d'image ou si la source est une page de recherche générale,
        # on ignore le produit pour éviter de polluer "trending"/"popular" et les "idées de concepts" réservées à l'IA.
        thumbnail = item.get("thumbnail_url")
        source_url = item.get("source_url") or ""
        
        if not thumbnail or any(x in source_url for x in ["/search", "query=", "?q=", "/market"]):
            continue

        keywords = _extract_keywords(item["title"])
        category = _detect_category(item["title"])
        
        # Calculer le score final
        query_count = title_counter.get(item["title"][:60].lower(), 1)
        score = int((1 - rank / total) * 55) + min(query_count * 5, 15) + item.get("badge_bonus", 0)
        score = max(1, min(100, score))

        if any(kw in item["title"].lower() for kw in season["keywords"]):
            score = min(100, score + 20)

        existing = db.query(IdeaBank).filter(IdeaBank.title == item["title"]).first()
        if existing:
            existing.trend_score = score
            existing.section = item.get("section", "trending")
            existing.detected_at = datetime.utcnow()
            existing.thumbnail_url = thumbnail
            existing.source_url = source_url
        else:
            db_item = IdeaBank(
                title=item["title"],
                description=item.get("description", ""),
                thumbnail_url=thumbnail,
                source_url=source_url,
                trend_score=score,
                section=item.get("section", "trending"),
                category=category,
                detected_at=datetime.utcnow(),
                keywords=json.dumps(keywords),
                source=item.get("source", "web"),
            )
            db.add(db_item)
            inserted += 1

    db.commit()
    yield {"step": 8, "msg": f"Succès ! {inserted} nouvelles tendances indexées, {total - inserted} fiches mises à jour.", "done": True}

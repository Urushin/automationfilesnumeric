"""
Scraper Service — Banque d'Idées / Tendances
Agrège les tendances de découpe laser depuis :
1. Flux RSS Etsy (lecture XML sans risque de blocage)
2. API publique Etsy (top listings digital crafts)
3. Données saisonnières calendaires (automatique)

Calcule un trend_score 1-100 basé sur la fréquence d'apparition.
"""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# CATÉGORIES SAISONNIÈRES AUTOMATIQUES
# ─────────────────────────────────────────────────────────────────────────────

def _get_seasonal_context() -> dict:
    """Retourne le contexte saisonnier basé sur la date courante."""
    today = date.today()
    month = today.month

    seasons = {
        1:  {"label": "Nouvel An / Hiver",     "keywords": ["hiver", "neige", "nouvel an", "janvier"], "category": "Winter"},
        2:  {"label": "Saint-Valentin",         "keywords": ["amour", "coeur", "saint valentin", "rose"], "category": "Valentine"},
        3:  {"label": "Printemps / Pâques",     "keywords": ["printemps", "paques", "lapin", "fleur"], "category": "Spring"},
        4:  {"label": "Printemps / Nature",     "keywords": ["jardin", "fleur", "nature", "oiseau"], "category": "Spring"},
        5:  {"label": "Fête des Mères / Jardin","keywords": ["mere", "jardin", "mariage", "fleur"], "category": "Mother"},
        6:  {"label": "Été / Mariage",          "keywords": ["ete", "mariage", "soleil", "plage"], "category": "Summer"},
        7:  {"label": "Été / Vacances",         "keywords": ["ete", "vacances", "tropical", "soleil"], "category": "Summer"},
        8:  {"label": "Fin d'été / Rentrée",    "keywords": ["rentree", "ecole", "hibou", "crayon"], "category": "BackToSchool"},
        9:  {"label": "Automne / Rentrée",      "keywords": ["automne", "feuille", "ecole", "arbre"], "category": "Autumn"},
        10: {"label": "Halloween / Automne",    "keywords": ["halloween", "citrouille", "fantome", "sorciere"], "category": "Halloween"},
        11: {"label": "Noël / Hiver",           "keywords": ["noel", "sapin", "etoile", "cadeau"], "category": "Christmas"},
        12: {"label": "Noël / Nouvel An",       "keywords": ["noel", "sapin", "flocon", "reveillon"], "category": "Christmas"},
    }
    return seasons.get(month, {"label": "Générique", "keywords": ["laser", "svg", "dxf"], "category": "General"})


# ─────────────────────────────────────────────────────────────────────────────
# RSS ETSY AGGREGATOR
# ─────────────────────────────────────────────────────────────────────────────

ETSY_RSS_QUERIES = [
    "laser cut file SVG",
    "Glowforge SVG bundle",
    "laser engraving file",
    "cricut SVG bundle",
    "silhouette svg laser",
    "dxf laser cut wood",
    "svg stencil file",
    "découpe laser fichier",
]

def _fetch_rss(query: str, max_items: int = 10) -> List[dict]:
    """Lit un flux RSS Etsy pour une requête et retourne les items parsés."""
    items = []
    try:
        encoded_q = urllib.parse.quote_plus(query) if hasattr(urllib, 'parse') else query.replace(" ", "+")
        url = f"https://www.etsy.com/search/rss?q={encoded_q}&order=most_relevant"

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; EtsyLaserBot/1.0)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read().decode("utf-8", errors="replace")

        root = ET.fromstring(xml_data)
        ns = {"media": "http://search.yahoo.com/mrss/"}
        channel = root.find("channel")
        if channel is None:
            return items

        for item in channel.findall("item")[:max_items]:
            title_el = item.find("title")
            link_el = item.find("link")
            thumb_el = item.find("media:thumbnail", ns)
            desc_el = item.find("description")

            title = title_el.text.strip() if title_el is not None and title_el.text else query
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            thumb = thumb_el.attrib.get("url") if thumb_el is not None else None
            # Extract plain text description from CDATA HTML
            desc_text = ""
            if desc_el is not None and desc_el.text:
                import re as _re
                raw = desc_el.text
                raw = _re.sub(r'<[^>]+>', ' ', raw)
                raw = _re.sub(r'\s+', ' ', raw).strip()
                desc_text = raw[:300]

            # Ensure thumbnail URL is absolute
            if thumb and not thumb.startswith("http"):
                thumb = "https://www.etsy.com" + thumb if thumb.startswith("/") else "https://www.etsy.com/" + thumb

            items.append({
                "title": title,
                "description": desc_text,
                "source_url": link,
                "thumbnail_url": thumb,
                "query": query,
            })
    except Exception as e:
        print(f"[scraper] RSS fetch failed for '{query}': {e}")
    return items


# ─────────────────────────────────────────────────────────────────────────────
# TREND SCORE CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_trend_score(rank: int, total: int, query_count: int) -> int:
    """
    Calcule un score 1-100 basé sur :
    - Rang d'apparition dans les résultats (plus haut = meilleur)
    - Nombre de requêtes dans lesquelles l'item apparaît (multi-source boost)
    """
    if total == 0:
        return 50
    position_score = int((1 - rank / total) * 70)  # 0-70 pts selon position
    cross_query_bonus = min(query_count * 10, 30)   # 0-30 pts selon nb sources
    return max(1, min(100, position_score + cross_query_bonus))


def _extract_keywords(title: str) -> List[str]:
    """Extrait les mots-clés pertinents d'un titre Etsy concurrent."""
    # Normaliser
    title_lower = title.lower()

    # Supprimer les extensions de fichier communes pour extraire le sujet
    clean = re.sub(r'\b(svg|dxf|eps|pdf|png|ai|cnc|laser|cricut|silhouette|glowforge|xtool|lightburn)\b', '', title_lower)
    clean = re.sub(r'[^\w\s]', ' ', clean)

    # Extraire les mots de plus de 3 caractères
    words = [w.strip() for w in clean.split() if len(w.strip()) > 3]

    # Retourner au maximum 5 mots-clés uniques
    seen = set()
    keywords = []
    for w in words:
        if w not in seen:
            seen.add(w)
            keywords.append(w)
        if len(keywords) >= 5:
            break

    return keywords


def _detect_category(title: str) -> str:
    """Détecte automatiquement la catégorie saisonnière/thématique d'un produit."""
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
# MOCK DATA FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def _generate_mock_ideas(season: dict) -> List[dict]:
    """Génère des idées mock quand le scraping échoue (mode hors-ligne)."""
    seasonal_kw = season["keywords"][0] if season["keywords"] else "laser"
    category = season["category"]

    ideas = [
        {
            "title": f"Mandala Géométrique SVG - Fichier Découpe Laser",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=mandala+svg+laser",
            "trend_score": 87,
            "category": "Mandala",
            "keywords": json.dumps(["mandala", "geometrique", "svg", "laser", "zen"]),
            "source": "mock",
        },
        {
            "title": f"Hibou {season['label']} - SVG DXF Bundle Laser Cut",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=owl+svg+laser",
            "trend_score": 75,
            "category": "Animal",
            "keywords": json.dumps(["hibou", "oiseau", seasonal_kw, "svg", "laser"]),
            "source": "mock",
        },
        {
            "title": f"Décoration {season['label']} - Pack SVG Découpe Laser Bois",
            "thumbnail_url": None,
            "source_url": f"https://www.etsy.com/search?q={seasonal_kw}+svg+laser",
            "trend_score": 92,
            "category": category,
            "keywords": json.dumps(season["keywords"][:3] + ["svg", "laser"]),
            "source": "mock",
        },
        {
            "title": "Cerf Géométrique Mandala SVG - Tête de Cerf Laser Cut",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=deer+head+mandala+svg",
            "trend_score": 83,
            "category": "Animal",
            "keywords": json.dumps(["cerf", "geometrique", "mandala", "svg", "laser"]),
            "source": "mock",
        },
        {
            "title": "Arbre de Vie Celtique SVG DXF - Fichier Laser Bois",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=tree+of+life+svg+laser",
            "trend_score": 78,
            "category": "Nature",
            "keywords": json.dumps(["arbre", "celtique", "vie", "svg", "laser"]),
            "source": "mock",
        },
        {
            "title": "Bonsai Japonais SVG - Décoration Zen Laser Cut Wall Art",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=bonsai+svg+laser",
            "trend_score": 71,
            "category": "Nature",
            "keywords": json.dumps(["bonsai", "japonais", "zen", "svg", "decor"]),
            "source": "mock",
        },
        {
            "title": "Lion Mandala SVG - Tête de Lion Géométrique Laser Cut",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=lion+mandala+svg",
            "trend_score": 88,
            "category": "Animal",
            "keywords": json.dumps(["lion", "mandala", "geometrique", "svg", "laser"]),
            "source": "mock",
        },
        {
            "title": f"Clipart {season['label']} - Pack SVG DXF Silhouette",
            "thumbnail_url": None,
            "source_url": f"https://www.etsy.com/search?q={seasonal_kw}+clipart+svg",
            "trend_score": 69,
            "category": category,
            "keywords": json.dumps(season["keywords"][:2] + ["clipart", "svg", "silhouette"]),
            "source": "mock",
        },
        {
            "title": "Attrape-Rêves SVG - Dream Catcher Laser Cut DXF Bundle",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=dreamcatcher+svg+laser",
            "trend_score": 65,
            "category": "General",
            "keywords": json.dumps(["attrape-reves", "dreamcatcher", "svg", "laser", "boho"]),
            "source": "mock",
        },
        {
            "title": "Fleur de Lotus Mandala SVG - Yoga Spiritual Laser Cut",
            "thumbnail_url": None,
            "source_url": "https://www.etsy.com/search?q=lotus+mandala+svg+laser",
            "trend_score": 73,
            "category": "Mandala",
            "keywords": json.dumps(["lotus", "mandala", "yoga", "svg", "spiritual"]),
            "source": "mock",
        },
    ]
    return ideas


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_full_scrape(db) -> dict:
    """
    Lance le scraping complet et stocke les résultats dans ideas_bank.
    Retourne un résumé de l'opération.
    """
    from ..models import IdeaBank

    season = _get_seasonal_context()
    print(f"[scraper] Starting scrape. Seasonal context: {season['label']}")

    all_raw_items = []
    scraped_ok = False

    # ── Phase 1: RSS Etsy ────────────────────────────────────────────────────
    for query in ETSY_RSS_QUERIES[:4]:  # Limiter à 4 requêtes pour éviter les blocages
        items = _fetch_rss(query, max_items=8)
        if items:
            scraped_ok = True
            all_raw_items.extend(items)

    # ── Fallback mock si scraping impossible ─────────────────────────────────
    if not scraped_ok or len(all_raw_items) < 5:
        print("[scraper] RSS scraping failed or insufficient — using mock data.")
        mock_ideas = _generate_mock_ideas(season)
        inserted = 0
        for idea in mock_ideas:
            # Vérifier si une idée similaire existe déjà
            existing = db.query(IdeaBank).filter(IdeaBank.title == idea["title"]).first()
            if not existing:
                item = IdeaBank(
                    title=idea["title"],
                    thumbnail_url=idea.get("thumbnail_url"),
                    source_url=idea.get("source_url"),
                    trend_score=idea.get("trend_score", 50),
                    category=idea.get("category", "General"),
                    detected_at=datetime.utcnow(),
                    keywords=idea.get("keywords"),
                    source=idea.get("source", "mock"),
                )
                db.add(item)
                inserted += 1
        db.commit()
        return {
            "status": "mock_data",
            "inserted": inserted,
            "season": season["label"],
            "message": "Données de démonstration insérées (scraping RSS non disponible)",
        }

    # ── Déduplification et scoring ───────────────────────────────────────────
    seen_titles = set()
    deduplicated = []
    for item in all_raw_items:
        title_key = item["title"][:60].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            deduplicated.append(item)

    total = len(deduplicated)
    inserted = 0

    for rank, item in enumerate(deduplicated):
        keywords = _extract_keywords(item["title"])
        category = _detect_category(item["title"])
        score = _calculate_trend_score(rank, total, 1)

        # Ajouter un boost saisonnier
        if any(kw in item["title"].lower() for kw in season["keywords"]):
            score = min(100, score + 20)

        existing = db.query(IdeaBank).filter(IdeaBank.title == item["title"]).first()
        if existing:
            # Mise à jour du score et description
            existing.trend_score = score
            existing.detected_at = datetime.utcnow()
            if item.get("description") and not existing.description:
                existing.description = item.get("description")
        else:
            db_item = IdeaBank(
                title=item["title"],
                description=item.get("description"),
                thumbnail_url=item.get("thumbnail_url"),
                source_url=item.get("source_url"),
                trend_score=score,
                category=category,
                detected_at=datetime.utcnow(),
                keywords=json.dumps(keywords),
                source="etsy_rss",
            )
            db.add(db_item)
            inserted += 1

    db.commit()
    print(f"[scraper] Done. Inserted {inserted} new ideas, updated existing.")

    return {
        "status": "success",
        "inserted": inserted,
        "total_scraped": total,
        "season": season["label"],
    }


# Import urllib.parse needed for URL encoding
import urllib.parse

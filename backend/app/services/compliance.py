"""
Compliance Service
Analyse les textes SEO générés pour détecter les marques protégées,
les caractères illégaux Etsy, et les mots-clés à risque avant publication.
"""
import re
import json
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# LISTES DE RISQUE
# ─────────────────────────────────────────────────────────────────────────────

# Marques déposées → suspension de boutique immédiate si utilisées dans titre/tags
TRADEMARK_BLACKLIST = [
    # Entertainment / Animation
    "disney", "mickey", "minnie", "donald duck", "goofy", "winnie the pooh",
    "piglet", "tigger", "bambi", "dumbo", "stitch", "lilo",
    "marvel", "avengers", "iron man", "spider-man", "spiderman", "captain america",
    "thor", "hulk", "black widow", "deadpool", "wolverine", "x-men",
    "star wars", "baby yoda", "grogu", "mandalorian", "darth vader", "yoda",
    "harry potter", "hogwarts", "hermione", "dumbledore", "voldemort",
    # Gaming
    "nintendo", "pokemon", "pikachu", "mario", "zelda", "link", "luigi",
    "kirby", "donkey kong", "metroid", "splatoon",
    "fortnite", "among us", "minecraft", "roblox",
    "playstation", "xbox",
    # Other well-known brands in crafting context
    "spongebob", "patrick star", "hello kitty", "sanrio",
    "paw patrol", "peppa pig", "bluey",
    "nfl", "nba", "mlb", "nhl",
    # Machine brands that can't be used as descriptors in tags
    "cricut", "silhouette cameo", "glowforge",
]

# Caractères illégaux dans les titres Etsy (rejetés par l'API)
ILLEGAL_TITLE_CHARS_PATTERN = re.compile(r'[<>&"\x00-\x1f]')

# Caractères illégaux dans les tags Etsy
ILLEGAL_TAG_CHARS_PATTERN = re.compile(r'[,;:!@#$%^*()+={}\[\]|\\<>/\x00-\x1f]')

# Mots potentiellement problématiques (niveau WARNING seulement)
RISKY_KEYWORDS = [
    "handmade",     # Etsy flague si le fichier est numérique + "handmade" dans la description
    "authentic",
    "official",
    "licensed",
    "genuine",
]


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURES DE RÉSULTAT
# ─────────────────────────────────────────────────────────────────────────────
class ComplianceWarning:
    def __init__(self, level: str, code: str, message: str, matched_term: Optional[str] = None):
        self.level = level
        self.code = code
        self.message = message
        self.matched_term = matched_term

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "matched_term": self.matched_term,
        }


class ComplianceResult:
    def __init__(self, warnings: List[ComplianceWarning]):
        self.warnings = warnings
        self.is_safe = not any(w.level in ("CRITICAL", "ERROR") for w in warnings)

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "warnings": [w.to_dict() for w in self.warnings],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────
def run_compliance_check(
    title_fr: Optional[str] = "",
    title_en: Optional[str] = "",
    description: Optional[str] = "",
    description_en: Optional[str] = "",
    tags_fr: Optional[str] = "",
    tags_en: Optional[str] = "",
) -> ComplianceResult:
    """
    Scanne tous les champs texte d'une création pour détecter :
    - Les marques protégées (niveau CRITICAL → bloque la publication)
    - Les caractères illégaux Etsy (niveau ERROR → rejetés par l'API)
    - Les mots à risque (niveau WARNING → notification seulement)

    Returns:
        ComplianceResult avec is_safe=True uniquement si aucun CRITICAL/ERROR
    """
    warnings: List[ComplianceWarning] = []

    # ── Concaténer tout le texte pour la recherche de marques ─────────────
    all_text = " ".join(filter(None, [
        title_fr, title_en, description, description_en, tags_fr, tags_en
    ])).lower()

    # ── Scan marques protégées ─────────────────────────────────────────────
    for brand in TRADEMARK_BLACKLIST:
        # Recherche avec word-boundary pour éviter les faux positifs
        # (ex: "criquet" ne doit pas matcher "cricut")
        pattern = r'\b' + re.escape(brand) + r'\b'
        if re.search(pattern, all_text):
            warnings.append(ComplianceWarning(
                level="CRITICAL",
                code="TRADEMARK_DETECTED",
                message=(
                    f"Marque protégée détectée : '{brand}'. "
                    "La publication sur Etsy risque de provoquer la suspension de votre boutique. "
                    "Supprimez ce terme de tous vos champs texte."
                ),
                matched_term=brand,
            ))

    # ── Scan caractères illégaux dans les titres ───────────────────────────
    for lang, title in [("FR", title_fr or ""), ("EN", title_en or "")]:
        match = ILLEGAL_TITLE_CHARS_PATTERN.search(title)
        if match:
            warnings.append(ComplianceWarning(
                level="ERROR",
                code="ILLEGAL_TITLE_CHAR",
                message=(
                    f"Titre {lang} contient un caractère illégal : '{match.group()}' "
                    f"(position {match.start()}). Ce caractère sera rejeté par l'API Etsy."
                ),
                matched_term=match.group(),
            ))

    # ── Scan caractères illégaux dans les tags ─────────────────────────────
    for lang, tags_str in [("FR", tags_fr or ""), ("EN", tags_en or "")]:
        tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
        for tag in tags_list:
            match = ILLEGAL_TAG_CHARS_PATTERN.search(tag)
            if match:
                warnings.append(ComplianceWarning(
                    level="ERROR",
                    code="ILLEGAL_TAG_CHAR",
                    message=(
                        f"Tag {lang} '{tag}' contient un caractère illégal : '{match.group()}'. "
                        "Les tags Etsy ne peuvent pas contenir de ponctuation spéciale."
                    ),
                    matched_term=match.group(),
                ))

            if len(tag) > 20:
                warnings.append(ComplianceWarning(
                    level="ERROR",
                    code="TAG_TOO_LONG",
                    message=(
                        f"Tag {lang} '{tag}' dépasse 20 caractères ({len(tag)} chars). "
                        "Il sera tronqué ou rejeté par Etsy."
                    ),
                    matched_term=tag,
                ))

    # ── Scan mots à risque ─────────────────────────────────────────────────
    for keyword in RISKY_KEYWORDS:
        if keyword in all_text:
            warnings.append(ComplianceWarning(
                level="WARNING",
                code="RISKY_KEYWORD",
                message=(
                    f"Mot potentiellement problématique détecté : '{keyword}'. "
                    "Etsy peut déclencher une revue manuelle avec ce terme pour un produit numérique."
                ),
                matched_term=keyword,
            ))

    # ── Validation nombre de tags ──────────────────────────────────────────
    for lang, tags_str in [("FR", tags_fr or ""), ("EN", tags_en or "")]:
        count = len([t for t in tags_str.split(",") if t.strip()])
        if count > 13:
            warnings.append(ComplianceWarning(
                level="ERROR",
                code="TOO_MANY_TAGS",
                message=f"Trop de tags {lang} : {count}/13 maximum autorisés par Etsy.",
                matched_term=None,
            ))

    return ComplianceResult(warnings)

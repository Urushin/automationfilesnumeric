from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    openai_key = Column(String, nullable=True)
    mistral_key = Column(String, nullable=True)
    gemini_key = Column(String, nullable=True)
    banana_key = Column(String, nullable=True)
    replicate_key = Column(String, nullable=True)
    openrouter_key = Column(String, nullable=True)
    huggingface_key = Column(String, nullable=True)
    anthropic_key = Column(String, nullable=True)
    stability_key = Column(String, nullable=True)

    image_ai_provider = Column(String, default="banana")
    stencil_image_provider = Column(String, default="banana")
    mockup_image_provider = Column(String, default="banana")
    stencil_image_quality = Column(String, default="auto")
    mockup_image_quality = Column(String, default="auto")
    text_ai_provider = Column(String, default="gemini-2.0-flash-lite")
    etsy_client_id = Column(String, nullable=True)
    etsy_client_secret = Column(String, nullable=True)
    etsy_oauth_token = Column(String, nullable=True)
    default_price = Column(Float, default=3.0)
    default_quantity = Column(Integer, default=999)
    default_status = Column(String, default="draft")
    potrace_path = Column(String, default="potrace")
    inkscape_path = Column(String, default="inkscape")
    mockup_background_path = Column(String, nullable=True)
    watermark_text = Column(String, default="digitalfilesbymop")
    default_apply_watermark = Column(Boolean, default=False)
    mockup_pack_count = Column(Integer, default=4)

    prompt_seo = Column(Text, nullable=True)
    prompt_image_generation = Column(Text, nullable=True)
    prompt_inpainting = Column(Text, nullable=True)
    prompt_trend_scraping = Column(Text, nullable=True)

    prompt_stencil_single = Column(Text, nullable=True)
    prompt_stencil_multiple = Column(Text, nullable=True)
    prompt_stencil_framed_filigree = Column(Text, nullable=True)
    prompt_vision_description = Column(Text, nullable=True)
    prompt_imagen3_negative_suffix = Column(Text, nullable=True)
    prompt_legacy_framed_filigree = Column(Text, nullable=True)
    prompt_legacy_classic = Column(Text, nullable=True)
    prompt_legacy_image_to_image = Column(Text, nullable=True)
    prompt_legacy_grad_cap = Column(Text, nullable=True)
    prompt_mockup_banana = Column(Text, nullable=True)
    prompt_mockup_dalle3 = Column(Text, nullable=True)
    prompt_mockup_degraded = Column(Text, nullable=True)


class Creation(Base):
    __tablename__ = "creations"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    theme = Column(String, nullable=True)

    # ── SEO bilingual ───────────────────────────────────────────────────────
    title_fr = Column(String, nullable=True)
    title_en = Column(String, nullable=True)
    description = Column(Text, nullable=True)        # Description Française complète
    description_en = Column(Text, nullable=True)     # Description Anglaise complète [NEW]
    tags_fr = Column(String, nullable=True)          # Comma-separated
    tags_en = Column(String, nullable=True)          # Comma-separated

    # ── Fichiers générés ────────────────────────────────────────────────────
    source_png_path = Column(String, nullable=True)
    svg_path = Column(String, nullable=True)
    dxf_path = Column(String, nullable=True)
    ai_path = Column(String, nullable=True)          # Adobe Illustrator .ai [NEW]
    eps_path = Column(String, nullable=True)         # Encapsulated PostScript .eps [NEW]
    pdf_path = Column(String, nullable=True)
    upscale_png_path = Column(String, nullable=True)
    mockup_path = Column(String, nullable=True)
    real_mockup_path = Column(String, nullable=True)
    zip_path = Column(String, nullable=True)

    source_type = Column(String, default="text_prompt")
    png_paths_raw = Column(Text, nullable=True)
    svg_paths_raw = Column(Text, nullable=True)
    pdf_paths_raw = Column(Text, nullable=True)
    source_png_variants_raw = Column(Text, nullable=True)

    @property
    def source_png_variants(self):
        if not self.source_png_variants_raw:
            return []
        return [p.strip() for p in self.source_png_variants_raw.split(",") if p.strip()]

    @source_png_variants.setter
    def source_png_variants(self, value):
        if isinstance(value, list):
            self.source_png_variants_raw = ",".join(value)
        else:
            self.source_png_variants_raw = value

    @property
    def png_paths(self):
        if not self.png_paths_raw:
            return []
        return [p.strip() for p in self.png_paths_raw.split(",") if p.strip()]

    @png_paths.setter
    def png_paths(self, value):
        if isinstance(value, list):
            self.png_paths_raw = ",".join(value)
        else:
            self.png_paths_raw = value

    @property
    def svg_paths(self):
        if not self.svg_paths_raw:
            return []
        return [p.strip() for p in self.svg_paths_raw.split(",") if p.strip()]

    @svg_paths.setter
    def svg_paths(self, value):
        if isinstance(value, list):
            self.svg_paths_raw = ",".join(value)
        else:
            self.svg_paths_raw = value

    @property
    def pdf_paths(self):
        if not self.pdf_paths_raw:
            return []
        return [p.strip() for p in self.pdf_paths_raw.split(",") if p.strip()]

    @pdf_paths.setter
    def pdf_paths(self, value):
        if isinstance(value, list):
            self.pdf_paths_raw = ",".join(value)
        else:
            self.pdf_paths_raw = value

    @property
    def selected_images(self):
        if not self.selected_images_raw:
            return []
        return [p.strip() for p in self.selected_images_raw.split(",") if p.strip()]

    @selected_images.setter
    def selected_images(self, value):
        if isinstance(value, list):
            self.selected_images_raw = ",".join(value)
        else:
            self.selected_images_raw = value

    @property
    def mockup_paths(self):
        if not self.mockup_paths_raw:
            return []
        return [p.strip() for p in self.mockup_paths_raw.split(",") if p.strip()]

    @mockup_paths.setter
    def mockup_paths(self, value):
        if isinstance(value, list):
            self.mockup_paths_raw = ",".join(value)
        else:
            self.mockup_paths_raw = value

    @property
    def real_mockup_paths(self):
        if not self.real_mockup_paths_raw:
            return []
        return [p.strip() for p in self.real_mockup_paths_raw.split(",") if p.strip()]

    @real_mockup_paths.setter
    def real_mockup_paths(self, value):
        if isinstance(value, list):
            self.real_mockup_paths_raw = ",".join(value)
        else:
            self.real_mockup_paths_raw = value

    @property
    def commercial_mockup_paths(self):
        if not self.commercial_mockup_paths_raw:
            return []
        return [p.strip() for p in self.commercial_mockup_paths_raw.split(",") if p.strip()]

    @commercial_mockup_paths.setter
    def commercial_mockup_paths(self, value):
        if isinstance(value, list):
            self.commercial_mockup_paths_raw = ",".join(value)
        else:
            self.commercial_mockup_paths_raw = value

    @property
    def dxf_paths(self):
        if not self.dxf_paths_raw:
            return []
        return [p.strip() for p in self.dxf_paths_raw.split(",") if p.strip()]

    @dxf_paths.setter
    def dxf_paths(self, value):
        if isinstance(value, list):
            self.dxf_paths_raw = ",".join(value)
        else:
            self.dxf_paths_raw = value

    @property
    def ai_paths(self):
        if not self.ai_paths_raw:
            return []
        return [p.strip() for p in self.ai_paths_raw.split(",") if p.strip()]

    @ai_paths.setter
    def ai_paths(self, value):
        if isinstance(value, list):
            self.ai_paths_raw = ",".join(value)
        else:
            self.ai_paths_raw = value

    @property
    def eps_paths(self):
        if not self.eps_paths_raw:
            return []
        return [p.strip() for p in self.eps_paths_raw.split(",") if p.strip()]

    @eps_paths.setter
    def eps_paths(self, value):
        if isinstance(value, list):
            self.eps_paths_raw = ",".join(value)
        else:
            self.eps_paths_raw = value

    # ── Etsy ────────────────────────────────────────────────────────────────
    is_published_etsy = Column(Boolean, default=False)
    etsy_listing_id = Column(String, nullable=True)
    price = Column(Float, default=3.0)
    quantity = Column(Integer, default=999)

    # ── Statut pipeline ─────────────────────────────────────────────────────
    status = Column(String, default="pending")       # pending/processing/completed/failed
    current_step = Column(String, nullable=True)
    failed_reason = Column(String, nullable=True)
    session_token = Column(String, nullable=True)    # UUID pour recovery SSE [NEW]

    # ── Qualité & conformité ────────────────────────────────────────────────
    bundle_size = Column(Integer, default=1)                  # Nb de designs dans le pack [NEW]
    connectivity_warnings = Column(Integer, default=0)        # Nb d'îles SVG détectées [NEW]
    compliance_warnings = Column(Text, nullable=True)         # JSON list des warnings [NEW]
    pipeline_status = Column(Text, nullable=True)             # JSON status of each component [NEW]
    selected_images_raw = Column(Text, nullable=True)         # Comma-separated selected image paths [NEW]
    mockup_styles = Column(Text, nullable=True)                # JSON array des styles mockup sélectionnés [NEW]
    apply_watermark = Column(Boolean, default=False)
    mockup_paths_raw = Column(Text, nullable=True)
    real_mockup_paths_raw = Column(Text, nullable=True)
    commercial_mockup_paths_raw = Column(Text, nullable=True)
    dxf_paths_raw = Column(Text, nullable=True)
    ai_paths_raw = Column(Text, nullable=True)
    eps_paths_raw = Column(Text, nullable=True)

    # ── Relation normalisée CreationAsset ───────────────────────────────────
    assets = relationship("CreationAsset", back_populates="creation", cascade="all, delete-orphan", lazy="selectin")


class CreationAsset(Base):
    """Table relationnelle normalisée pour tous les fichiers et médias générés."""
    __tablename__ = "creation_assets"

    id = Column(Integer, primary_key=True, index=True)
    creation_id = Column(Integer, ForeignKey("creations.id", ondelete="CASCADE"), index=True, nullable=False)
    asset_type = Column(String, index=True, nullable=False)  # "source_png", "svg", "dxf", "ai", "eps", "pdf", "mockup", "zip", "variant"
    file_path = Column(String, nullable=False)
    filename = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    creation = relationship("Creation", back_populates="assets")


class IdeaBank(Base):
    """Stockage local de la banque d'idées / tendances scrapées."""
    __tablename__ = "ideas_bank"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)        # Description du produit
    thumbnail_url = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    trend_score = Column(Integer, default=50)        # 1-100
    section = Column(String, default="trending")     # "trending", "popular", "ideas"
    category = Column(String, nullable=True)         # e.g. "Halloween", "Wedding", "Nature"
    detected_at = Column(DateTime, default=datetime.utcnow)
    is_injected = Column(Boolean, default=False)     # True quand injectée dans le pipeline
    keywords = Column(Text, nullable=True)           # Mots-clés extraits (JSON list)
    source = Column(String, default="etsy_rss")     # "etsy_rss" | "etsy_api" | "manual"

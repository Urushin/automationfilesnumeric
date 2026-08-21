from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class SettingBase(BaseModel):
    openai_key: Optional[str] = None
    mistral_key: Optional[str] = None
    gemini_key: Optional[str] = None
    banana_key: Optional[str] = None
    replicate_key: Optional[str] = None
    openrouter_key: Optional[str] = None
    huggingface_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    stability_key: Optional[str] = None

    image_ai_provider: str = "banana"
    stencil_image_provider: str = "banana"
    mockup_image_provider: str = "banana"
    stencil_image_quality: str = "auto"
    mockup_image_quality: str = "auto"
    text_ai_provider: str = "gemini-2.0-flash-lite"
    etsy_client_id: Optional[str] = None
    etsy_client_secret: Optional[str] = None
    etsy_oauth_token: Optional[str] = None
    default_price: float = 3.0
    default_quantity: int = 999
    default_status: str = "draft"
    potrace_path: str = "potrace"
    inkscape_path: str = "inkscape"
    mockup_background_path: Optional[str] = None
    watermark_text: Optional[str] = "digitalfilesbymop"
    default_apply_watermark: Optional[bool] = False
    mockup_pack_count: Optional[int] = 4

    prompt_seo: Optional[str] = None
    prompt_image_generation: Optional[str] = None
    prompt_inpainting: Optional[str] = None
    prompt_trend_scraping: Optional[str] = None

    prompt_stencil_single: Optional[str] = None
    prompt_stencil_multiple: Optional[str] = None
    prompt_stencil_framed_filigree: Optional[str] = None
    prompt_vision_description: Optional[str] = None
    prompt_imagen3_negative_suffix: Optional[str] = None
    prompt_legacy_framed_filigree: Optional[str] = None
    prompt_legacy_classic: Optional[str] = None
    prompt_legacy_image_to_image: Optional[str] = None
    prompt_legacy_grad_cap: Optional[str] = None
    prompt_mockup_banana: Optional[str] = None
    prompt_mockup_dalle3: Optional[str] = None
    prompt_mockup_degraded: Optional[str] = None

class SettingUpdate(SettingBase):
    pass

class SettingResponse(SettingBase):
    id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# CREATION SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class CreationBase(BaseModel):
    theme: Optional[str] = None
    title_fr: Optional[str] = None
    title_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None          # [NEW]
    tags_fr: Optional[str] = None
    tags_en: Optional[str] = None

class CreationUpdate(BaseModel):
    title_fr: Optional[str] = None
    title_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    tags_fr: Optional[str] = None
    tags_en: Optional[str] = None
    is_published_etsy: Optional[bool] = None
    etsy_listing_id: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    selected_images_raw: Optional[str] = None
    bundle_size: Optional[int] = None
    mockup_path: Optional[str] = None
    real_mockup_path: Optional[str] = None
    png_paths_raw: Optional[str] = None
    source_png_variants_raw: Optional[str] = None
    apply_watermark: Optional[bool] = None

class CreationResponse(CreationBase):
    id: int
    timestamp: datetime
    source_png_path: Optional[str] = None
    svg_path: Optional[str] = None
    dxf_path: Optional[str] = None
    ai_path: Optional[str] = None                 # [NEW]
    eps_path: Optional[str] = None                # [NEW]
    pdf_path: Optional[str] = None
    upscale_png_path: Optional[str] = None
    mockup_path: Optional[str] = None
    real_mockup_path: Optional[str] = None
    zip_path: Optional[str] = None
    is_published_etsy: bool = False
    etsy_listing_id: Optional[str] = None
    price: Optional[float] = 3.0
    quantity: Optional[int] = 999
    status: Optional[str] = "pending"
    current_step: Optional[str] = None
    failed_reason: Optional[str] = None
    session_token: Optional[str] = None
    bundle_size: Optional[int] = 1
    connectivity_warnings: Optional[int] = 0
    compliance_warnings: Optional[str] = None     # JSON string
    source_type: Optional[str] = "text_prompt"
    apply_watermark: Optional[bool] = False
    png_paths: Optional[List[str]] = []
    svg_paths: Optional[List[str]] = []
    pdf_paths: Optional[List[str]] = []
    mockup_paths: Optional[List[str]] = []
    real_mockup_paths: Optional[List[str]] = []
    commercial_mockup_paths: Optional[List[str]] = []
    dxf_paths: Optional[List[str]] = []
    ai_paths: Optional[List[str]] = []
    eps_paths: Optional[List[str]] = []
    pipeline_status: Optional[str] = None          # JSON status of each component [NEW]
    selected_images_raw: Optional[str] = None
    source_png_variants_raw: Optional[str] = None
    source_png_variants: Optional[List[str]] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class GlobalPipelineRequest(BaseModel):
    theme: str
    image_ai_provider: Optional[str] = "openai"
    text_ai_provider: Optional[str] = "gemini"
    design_style: Optional[str] = "classic"
    apply_watermark: Optional[bool] = False
    watermark_text: Optional[str] = None

class ModularPipelineRequest(BaseModel):
    theme: Optional[str] = None
    generate_ai_stencil: bool = False
    vectorize: bool = False
    convert_cad: bool = False
    format_pdf: bool = False
    upscale: bool = False
    package: bool = False
    generate_seo: bool = False
    generate_real_mockup: bool = False
    use_ai_mockup: bool = False
    apply_tp_overlay: bool = False
    apply_watermark: bool = False
    watermark_text: Optional[str] = None
    image_ai_provider: Optional[str] = "openai"
    text_ai_provider: Optional[str] = "gemini"
    design_style: Optional[str] = "classic"
    source_type: Optional[str] = "text_prompt"


# ─────────────────────────────────────────────────────────────────────────────
# COMPLIANCE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class ComplianceWarning(BaseModel):
    level: str          # "CRITICAL" | "ERROR" | "WARNING"
    code: str           # e.g. "TRADEMARK_DETECTED"
    message: str
    matched_term: Optional[str] = None

class ComplianceResult(BaseModel):
    is_safe: bool
    warnings: List[ComplianceWarning] = []


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class BinaryStatus(BaseModel):
    name: str
    status: str         # "OK" | "FAILED" | "FALLBACK"
    path: str
    resolved_path: Optional[str] = None
    error: Optional[str] = None

class EtsyTokenStatus(BaseModel):
    connected: bool
    expires_in_hours: Optional[float] = None
    refresh_expires_in_days: Optional[float] = None
    warning: Optional[str] = None

class HealthResponse(BaseModel):
    status: str         # "healthy" | "degraded" | "critical"
    binaries: List[BinaryStatus]
    etsy_token: EtsyTokenStatus


# ─────────────────────────────────────────────────────────────────────────────
# IDEA BANK SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class IdeaBankItem(BaseModel):
    id: int
    title: str
    thumbnail_url: Optional[str] = None
    source_url: Optional[str] = None
    trend_score: int = 50
    category: Optional[str] = None
    section: str = "trending"
    detected_at: datetime
    is_injected: bool = False
    keywords: Optional[str] = None   # JSON string
    source: Optional[str] = None

    class Config:
        from_attributes = True

class IdeaBankCreate(BaseModel):
    title: str
    thumbnail_url: Optional[str] = None
    source_url: Optional[str] = None
    trend_score: int = 50
    category: Optional[str] = None
    keywords: Optional[str] = None
    source: Optional[str] = "manual"

class PublishRequest(BaseModel):
    selected_assets: Optional[List[str]] = None


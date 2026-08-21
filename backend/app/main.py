import os
for key in list(os.environ.keys()):
    if os.environ[key] == "None":
        del os.environ[key]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .routers import settings, creations, etsy
from .routers import pipeline as pipeline_router
from .routers import health as health_router
from .routers import scraper as scraper_router

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-CREATE + MIGRATE DB TABLES
# ─────────────────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

from sqlalchemy import text
try:
    with engine.connect() as conn:
        # Enable WAL mode dynamically on migration connection
        conn.execute(text("PRAGMA journal_mode=WAL;"))

        # ── Table creations ───────────────────────────────────────────────
        result = conn.execute(text("PRAGMA table_info(creations)"))
        columns = [row[1] for row in result]

        migrations_creations = {
            "status":                  "ALTER TABLE creations ADD COLUMN status VARCHAR DEFAULT 'pending'",
            "current_step":            "ALTER TABLE creations ADD COLUMN current_step VARCHAR",
            "failed_reason":           "ALTER TABLE creations ADD COLUMN failed_reason VARCHAR",
            "description_en":          "ALTER TABLE creations ADD COLUMN description_en TEXT",
            "ai_path":                 "ALTER TABLE creations ADD COLUMN ai_path VARCHAR",
            "eps_path":                "ALTER TABLE creations ADD COLUMN eps_path VARCHAR",
            "session_token":           "ALTER TABLE creations ADD COLUMN session_token VARCHAR",
            "bundle_size":             "ALTER TABLE creations ADD COLUMN bundle_size INTEGER DEFAULT 1",
            "connectivity_warnings":   "ALTER TABLE creations ADD COLUMN connectivity_warnings INTEGER DEFAULT 0",
            "compliance_warnings":     "ALTER TABLE creations ADD COLUMN compliance_warnings TEXT",
            "price":                   "ALTER TABLE creations ADD COLUMN price FLOAT DEFAULT 3.0",
            "real_mockup_path":        "ALTER TABLE creations ADD COLUMN real_mockup_path VARCHAR",
            "source_type":             "ALTER TABLE creations ADD COLUMN source_type VARCHAR DEFAULT 'text_prompt'",
            "png_paths_raw":           "ALTER TABLE creations ADD COLUMN png_paths_raw TEXT",
            "svg_paths_raw":           "ALTER TABLE creations ADD COLUMN svg_paths_raw TEXT",
            "pdf_paths_raw":           "ALTER TABLE creations ADD COLUMN pdf_paths_raw TEXT",
            "pipeline_status":         "ALTER TABLE creations ADD COLUMN pipeline_status TEXT",
            "selected_images_raw":     "ALTER TABLE creations ADD COLUMN selected_images_raw TEXT",
            "source_png_variants_raw": "ALTER TABLE creations ADD COLUMN source_png_variants_raw TEXT",
            "mockup_paths_raw":        "ALTER TABLE creations ADD COLUMN mockup_paths_raw TEXT",
            "real_mockup_paths_raw":   "ALTER TABLE creations ADD COLUMN real_mockup_paths_raw TEXT",
            "dxf_paths_raw":           "ALTER TABLE creations ADD COLUMN dxf_paths_raw TEXT",
            "ai_paths_raw":            "ALTER TABLE creations ADD COLUMN ai_paths_raw TEXT",
            "eps_paths_raw":           "ALTER TABLE creations ADD COLUMN eps_paths_raw TEXT",
            "mockup_styles":           "ALTER TABLE creations ADD COLUMN mockup_styles TEXT",
            "apply_watermark":         "ALTER TABLE creations ADD COLUMN apply_watermark BOOLEAN DEFAULT 0",
        }

        for col_name, sql in migrations_creations.items():
            if col_name not in columns:
                conn.execute(text(sql))
                print(f"[migration] Added column: creations.{col_name}")

        # ── Table settings ────────────────────────────────────────────────
        result = conn.execute(text("PRAGMA table_info(settings)"))
        settings_columns = [row[1] for row in result]

        migrations_settings = {
            "mockup_background_path": "ALTER TABLE settings ADD COLUMN mockup_background_path VARCHAR",
            "watermark_text":         "ALTER TABLE settings ADD COLUMN watermark_text VARCHAR DEFAULT 'digitalfilesbymop'",
            "default_apply_watermark": "ALTER TABLE settings ADD COLUMN default_apply_watermark BOOLEAN DEFAULT 0",
            "mockup_pack_count":      "ALTER TABLE settings ADD COLUMN mockup_pack_count INTEGER DEFAULT 4",
            "banana_key":             "ALTER TABLE settings ADD COLUMN banana_key VARCHAR",
            "image_ai_provider":      "ALTER TABLE settings ADD COLUMN image_ai_provider VARCHAR DEFAULT 'banana'",
            "stencil_image_provider":  "ALTER TABLE settings ADD COLUMN stencil_image_provider VARCHAR DEFAULT 'banana'",
            "mockup_image_provider":   "ALTER TABLE settings ADD COLUMN mockup_image_provider VARCHAR DEFAULT 'banana'",
            "stencil_image_quality":   "ALTER TABLE settings ADD COLUMN stencil_image_quality VARCHAR DEFAULT 'auto'",
            "mockup_image_quality":    "ALTER TABLE settings ADD COLUMN mockup_image_quality VARCHAR DEFAULT 'auto'",
            "text_ai_provider":       "ALTER TABLE settings ADD COLUMN text_ai_provider VARCHAR DEFAULT 'gemini-2.0-flash-lite'",
            "replicate_key":          "ALTER TABLE settings ADD COLUMN replicate_key VARCHAR",
            "openrouter_key":         "ALTER TABLE settings ADD COLUMN openrouter_key VARCHAR",
            "huggingface_key":        "ALTER TABLE settings ADD COLUMN huggingface_key VARCHAR",
            "anthropic_key":          "ALTER TABLE settings ADD COLUMN anthropic_key VARCHAR",
            "stability_key":          "ALTER TABLE settings ADD COLUMN stability_key VARCHAR",
            "prompt_seo":             "ALTER TABLE settings ADD COLUMN prompt_seo TEXT",
            "prompt_image_generation": "ALTER TABLE settings ADD COLUMN prompt_image_generation TEXT",
            "prompt_inpainting":       "ALTER TABLE settings ADD COLUMN prompt_inpainting TEXT",
            "prompt_trend_scraping":   "ALTER TABLE settings ADD COLUMN prompt_trend_scraping TEXT",
            "prompt_stencil_single":   "ALTER TABLE settings ADD COLUMN prompt_stencil_single TEXT",
            "prompt_stencil_multiple": "ALTER TABLE settings ADD COLUMN prompt_stencil_multiple TEXT",
            "prompt_stencil_framed_filigree": "ALTER TABLE settings ADD COLUMN prompt_stencil_framed_filigree TEXT",
            "prompt_vision_description": "ALTER TABLE settings ADD COLUMN prompt_vision_description TEXT",
            "prompt_imagen3_negative_suffix": "ALTER TABLE settings ADD COLUMN prompt_imagen3_negative_suffix TEXT",
            "prompt_legacy_framed_filigree": "ALTER TABLE settings ADD COLUMN prompt_legacy_framed_filigree TEXT",
            "prompt_legacy_classic":   "ALTER TABLE settings ADD COLUMN prompt_legacy_classic TEXT",
            "prompt_legacy_image_to_image": "ALTER TABLE settings ADD COLUMN prompt_legacy_image_to_image TEXT",
            "prompt_legacy_grad_cap":  "ALTER TABLE settings ADD COLUMN prompt_legacy_grad_cap TEXT",
            "prompt_mockup_banana":    "ALTER TABLE settings ADD COLUMN prompt_mockup_banana TEXT",
            "prompt_mockup_dalle3":    "ALTER TABLE settings ADD COLUMN prompt_mockup_dalle3 TEXT",
            "prompt_mockup_degraded":  "ALTER TABLE settings ADD COLUMN prompt_mockup_degraded TEXT",
        }

        for col_name, sql in migrations_settings.items():
            if col_name not in settings_columns:
                conn.execute(text(sql))
                print(f"[migration] Added column: settings.{col_name}")

        # ── Table ideas_bank ──────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ideas_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR NOT NULL,
                description TEXT,
                thumbnail_url TEXT,
                source_url TEXT,
                trend_score INTEGER DEFAULT 50,
                section VARCHAR DEFAULT 'trending',
                category VARCHAR,
                detected_at DATETIME,
                is_injected BOOLEAN DEFAULT 0,
                keywords TEXT,
                source VARCHAR DEFAULT 'etsy_rss'
            )
        """))
        print("[migration] Ensured ideas_bank table exists.")

        # Migration pour ajouter 'section' et 'description' si la table existait déjà
        result_ib = conn.execute(text("PRAGMA table_info(ideas_bank)"))
        ib_columns = [row[1] for row in result_ib]
        if "section" not in ib_columns:
            conn.execute(text("ALTER TABLE ideas_bank ADD COLUMN section VARCHAR DEFAULT 'trending'"))
            print("[migration] Added column: ideas_bank.section")
        if "description" not in ib_columns:
            conn.execute(text("ALTER TABLE ideas_bank ADD COLUMN description TEXT"))
            print("[migration] Added column: ideas_bank.description")

        conn.commit()
except Exception as e:
    print(f"[migration] Warning during DB migration: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Etsy Laser Automation Backend",
    description="Local microservices for generating vector graphics and publishing on Etsy",
    version="3.0.0",
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# DIRECTORY SETUP
# ─────────────────────────────────────────────────────────────────────────────
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
STORAGE_DIR = os.path.join(BACKEND_DIR, "storage")
ASSETS_DIR  = os.path.join(BACKEND_DIR, "assets")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.join(ASSETS_DIR, "backgrounds"), exist_ok=True)



# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILE SERVING
# ─────────────────────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=STORAGE_DIR), name="static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ─────────────────────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(settings.router)
app.include_router(creations.router)
app.include_router(etsy.router)
app.include_router(etsy.oauth_router)
app.include_router(pipeline_router.router)
app.include_router(health_router.router)
app.include_router(scraper_router.router)


@app.get("/")
def read_root():
    return {"message": "Etsy Laser Automation API v3.0 is running."}

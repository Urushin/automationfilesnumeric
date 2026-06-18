import os
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
            "quantity":                "ALTER TABLE creations ADD COLUMN quantity INTEGER DEFAULT 999",
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
                category VARCHAR,
                detected_at DATETIME,
                is_injected BOOLEAN DEFAULT 0,
                keywords TEXT,
                source VARCHAR DEFAULT 'etsy_rss'
            )
        """))
        print("[migration] Ensured ideas_bank table exists.")

        # Migrate ideas_bank to add description column if missing
        result = conn.execute(text("PRAGMA table_info(ideas_bank)"))
        ideas_columns = [row[1] for row in result]
        if "description" not in ideas_columns:
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

# Generate default wood background if missing
wood_bg_path = os.path.join(ASSETS_DIR, "wood_background.jpg")
if not os.path.exists(wood_bg_path):
    try:
        from .services.image import create_fallback_background
        fallback_bg = create_fallback_background(1200, 1200)
        fallback_bg.save(wood_bg_path, "JPEG", quality=90)
        print("[startup] Generated default wood background image asset.")
    except Exception as e:
        print(f"[startup] Could not generate default background: {e}")

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

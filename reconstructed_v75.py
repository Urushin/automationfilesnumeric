# Implementation Plan - System Audit and Surgical Correction

This plan outlines the fixes for identified critical database, image pipeline, async blocking, and Next.js routing issues.

## User Review Required

> [!IMPORTANT]
> - **Next.js Asset Proxies**: We will update `next.config.ts` to route `/static/:path*` to the FastAPI backend. This is crucial for rendering generated images and download files correctly.
> - **Database Migrations**: Startup code in `main.py` will be modified to safely inject missing columns (`pipeline_status`, `selected_images_raw`, `description`) into any existing databases to prevent startup crashes.

## Proposed Changes

---

### Core Database and Startup Stabilization

#### [MODIFY] [main.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/main.py)
- Include missing columns `pipeline_status` and `selected_images_raw` in `migrations_creations`.
- Fix the `ideas_bank` manual table DDL to include the `description` column.
- Execute `PRAGMA journal_mode=WAL;` at engine connection to enable Write-Ahead Logging for SQLite concurrency safety.

#### [MODIFY] [database.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/database.py)
- Ensure WAL journal mode is set on connection creation.

---

### Image Engine and Pipeline Robustness

#### [MODIFY] [image_engine.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/bac
# MISSING LINE 30
# MISSING LINE 31
# MISSING LINE 32
# MISSING LINE 33
# MISSING LINE 34
# MISSING LINE 35
# MISSING LINE 36

---

### Router Optimization and Event Loop Preservation

#### [MODIFY] [pipeline.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py)
- Wrap synchronous blocking I/O calls (`shutil.copyfileobj`, `requests.get`, `open()`, and `db.commit()`) in `upload_source_file` and `pipeline_local_correction` with `asyncio.to_thread`.

---

### Frontend URL and Routing Alignment

#### [MODIFY] [next.config.ts](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/next.config.ts)
- Add `/static/:path*` to `rewrites()` pointing to the backend.

#### [MODIFY] [CanvasEditor.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/CanvasEditor.tsx)
- Replace hardcoded relative URLs `"/api/..."` with `apiUrl("/api/...")`.

#### [MODIFY] [ImageWorkspace.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/ImageWorkspace.tsx)
- Replace relative URLs `"/api/..."` with `apiUrl("/api/...")`.

#### [MODIFY] [page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/trends/page.tsx)
- Replace relative URLs `"/api/..."` with `apiUrl("/api/...")`.

#### [MODIFY] [page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/settings/page.tsx)
- Replace relative URLs `"/api/..."` with `apiUrl("/api/...")`.

---

## Verification Plan

### Automated Tests
- Run database migrations: check table structure after startup.
- Validate element splitting with transparent input PNGs.

### Manual Verification
- Verify Next.js serves static assets without 404 errors.
- Run local corrections in Workspace to ensure non-blocking file updates.


# WORKFLOW

## 1. Database and Migration Repairs
- [ ] Add `pipeline_status` and `selected_images_raw` columns to `migrations_creations` migration dictionary in `backend/app/main.py`.
- [ ] Add `description` column to manual table creation DDL for `ideas_bank` in `backend/app/main.py`.
- [ ] Enable WAL journal mode (`PRAGMA journal_mode=WAL;`) on database startup connection in `backend/app/main.py` and `backend/app/database.py`.

## 2. Robust Image and Contour Processing
- [ ] Refactor `split_multielement_image` in `backend/app/services/image_engine.py` to use PIL for loading transparent/alpha images, composite them over white, convert to grayscale numpy arrays, and pass to OpenCV for contour detection.
- [ ] Update `convert_to_transparent_png` in `backend/app/services/image.py` to check and preserve existing alpha channels (`alpha_arr < 10`) when isolating white backgrounds.

## 3. Asynchronous Blocking I/O Fixes
- [ ] Wrap all synchronous I/O operations (`shutil.copyfileobj`, `requests.get`, `open()`, and `db.commit()`) in `upload_source_file` and `pipeline_local_correction` in `backend/app/routers/pipeline.py` using `asyncio.to_thread`.
- [ ] Ensure background task token refresh in `etsy.py` and other synchronous operations run off the main event loop correctly.

## 4. Frontend Asset Routing & API Standardization
- [ ] Add `/static/:path*` rewrite rules to `frontend/next.config.ts` so all assets served from backend storage folder resolve correctly.
- [ ] Replace all hardcoded relative `/api/` fetch endpoints in `CanvasEditor.tsx`, `ImageWorkspace.tsx`, `trends/page.tsx`, and `settings/page.tsx` with unified `apiUrl(...)` calls.
- [ ] Fix potential silent mock-up failures in `mockup_engine.py` by ensuring errors in transparency generation are logged and handled.

## 5. Non-Destructive Binarization and Splitting Pipeline Refactor
- [ ] Refactor routing logic in `backend/app/routers/pipeline.py` to only call `local_binarize_image` when `source_type == "clean_bw_stencil"`, otherwise routing to the AI Stencil Pipeline.
- [ ] Update GPT-4o Vision instructions and the gpt-image-1 prompt in `backend/app/services/image_engine.py` to enforce detailed negative-space white lines inside stencils to prevent solid black blobs.
- [ ] Rewrite `split_multielement_image` in `backend/app/services/image_engine.py` to perform non-destructive NumPy bounding-box cropping with 20px padding instead of filled contour masking.
- [ ] Implement safety guards to catch contour detection failures, falling back to returning the original image.


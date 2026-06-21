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
- [ ] Replace all hardcoded relative `/api/` 
# MISSING LINE 19
# MISSING LINE 20
# MISSING LINE 21
# MISSING LINE 22
# MISSING LINE 23
- [ ] Rewrite `split_multielement_image` in `backend/app/services/image_engine.py` to perform non-destructive NumPy bounding-box cropping with 20px padding instead of filled contour masking.
- [ ] Implement safety guards to catch contour detection failures, falling back to returning the original image.

## 6. Element Quantity Choice & Copy Prompts Feature
- [ ] Add `bundle_size` to `CreationUpdate` in `backend/app/schemas.py` and `InstructionsBody` in `backend/app/routers/creations.py`.
- [ ] Save updated `bundle_size` in `regenerate_creation_image` endpoint in `backend/app/routers/creations.py`.
- [ ] Update `generate_stencil_image` and `regenerate_stencil_image_guided` in `backend/app/services/image_engine.py` to respect `custom_prompt` in `gpt-image-2`, include `bundle_size` in `huggingface-flux-free` prompts, and instruct Gemini on `bundle_size` target.
- [ ] Pass `generate_ai_stencil` and mockup parameters in `handleModularSubmit` query params in `frontend/app/page.tsx`.
- [ ] Add `bundleSize` state, selector input, and payload parameters to `frontend/app/review/[id]/page.tsx`.
- [ ] Implement `accordionOpen` state, parse `pipeline_status` json, and render "📋 Mode Manuel & Balises de Fichiers" collapsible panel in `frontend/app/review/[id]/page.tsx`.

## 7. Mockup Masking & Fusion Corrections
- [ ] Implement `extract_artwork_mask` in `mockup_engine.py` and `generator.py` to correctly extract transparency masks.
- [ ] Update `composite_stencil_on_bg` and `create_real_mockup` to use `extract_artwork_mask`.
- [ ] Generate the AI room backdrop once in `pipeline.py` and pass it to both mockup functions.
- [ ] Clean up temporary background files in `pipeline.py`.



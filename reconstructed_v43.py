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
# MISSING LINE 24
- [x] Mandate 5: CanvasEditor Workspace Pan & Zoom + Exclusion Brush Tool
- [x] Mandate 7: Trend Scraper rotating headers, request delays, and BeautifulSoup fallback parsers
- [x] Mandate 8: High-End Asset Review Grid, Checkbox Selection overlays, Select All toggle, and Etsy publish filtering
- [x] Mandate 9: SEO "Translate & Optimize to English" FastAPI endpoint & Frontend trigger button
- [ ] Save updated `bundle_size` in `regenerate_creation_image` endpoint in `backend/app/routers/creations.py`.
- [ ] Update `generate_stencil_image` and `regenerate_stencil_image_guided` in `backend/app/services/image_engine.py` to respect `custom_prompt` in `gpt-image-2`, include `bundle_size` in `huggingface-flux-free` prompts, and instruct Gemini on `bundle_size` target.
- [ ] Pass `generate_ai_stencil` and mockup parameters in `handleModularSubmit` query params in `frontend/app/page.tsx`.
- [ ] Add `bundleSize` state, selector input, and payload parameters to `frontend/app/review/[id]/page.tsx`.
- [ ] Implement `accordionOpen` state, parse `pipeline_status` json, and render "📋 Mode Manuel & Balises de Fichiers" collapsible panel in `frontend/app/review/[id]/page.tsx`.

## 8. Quality Gate Modal and Canvas Improvements
- [ ] Backend: Fix URL/Path concatenation bug by adding path sanitization block for `http://` / `https://` URLs in `execute_inpainting` (image_engine.py) and `pipeline_inpainting`/`pipeline_local_correction`/`save_workspace` endpoints (pipeline.py).
- [ ] Backend: Add a new POST route `/api/pipeline/save-workspace` to accept `creation_id` and base64 `canvasData`, decode and save the image to disk, binarize it as opaque white, and return success.
- [ ] Frontend: Add zoom buttons (+ / -) in `CanvasEditor.tsx` that modify a scale state and apply CSS transform scale to the canvas wrapper container.
- [ ] Frontend: Add Undo and Redo buttons in `CanvasEditor.tsx` linking to the canvas ref's undo/redo functionality.
- [ ] Frontend: Refactor `RetouchModal`'s save handler and validation handler in `page.tsx` and `review/[id]/page.tsx` to strictly wait for `/api/pipeline/save-workspace` before closing the modal and triggering downstream steps.




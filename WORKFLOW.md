# WORKFLOW - MOCKUP PURIFICATION & DOUBLE EXPORT

## 1. Backend: Refactor `image_engine.py`
- [x] Remove `generate_mockup` parameter from `generate_stencil_image` function signature and body.
- [x] Refactor `generate_real_mockup` logic to output `_mockup_raw.jpg` (clean 3D scene without watermark) and `_mockup_commercial.jpg` (framed 3D scene with `tp.png` foreground overlay).

## 2. Backend: Clean up `pipeline.py` & Reprocessing
- [x] Eliminate `generate_mockup` routing parameters and logic across all endpoints.
- [x] Update `reprocess_creation_assets` to generate both `_mockup_raw.jpg` (saved in `mockup_path`) and `_mockup_commercial.jpg` (saved in `real_mockup_path`).
- [x] Update ZIP packaging loop to skip old `_mockup.jpg` and cleanly embed `_mockup_raw.jpg` and `_mockup_commercial.jpg` in the archive.

## 3. Backend: Refactor `creations.py`
- [x] Update creations endpoints and regeneration helpers to match the double-export mockup logic, mapping `mockup_path` to the raw version and `real_mockup_path` to the commercial version.

## 4. Frontend: Obliterate Legacy Toggles
- [x] Remove Standard Mockup checkbox from `PipelineForm.tsx` and rename the remaining option to "Générer le Vrai Mockup 3D (Bois)".
- [x] Clean up state and option parameters in `page.tsx` and `review/[id]/page.tsx` to completely remove `generate_mockup`.
- [x] Update Review display grid in `review/[id]/page.tsx` to load and display both returned image paths side-by-side with labels "Aperçu Brut" and "Aperçu Commercial avec Cadre".

## Sprint Tasks - Stencil Pipeline Stabilization & Feature Expansion
- [x] Mandate 1: Workspace Inpainting Mask Cleanup (backend & upload endpoint)
- [x] Mandate 2: Multi-Style Mockup Engine (frontend dropdown / array builder, backend iteration logic)
- [x] Mandate 3: OpenCV Contour Noise Reduction & Dynamic min_area Scaling
- [x] Mandate 4: Progressive Streaming Real-time Preview Fix in LiveStreamPanel
- [x] Mandate 5: CanvasEditor Workspace Pan & Zoom + Exclusion Brush Tool
- [x] Mandate 7: Trend Scraper rotating headers, request delays, and BeautifulSoup fallback parsers
- [x] Mandate 8: High-End Asset Review Grid, Checkbox Selection overlays, Select All toggle, and Etsy publish filtering
- [x] Mandate 9: SEO "Translate & Optimize to English" FastAPI endpoint & Frontend trigger button
- [x] Mandate 10: Strict Tag Character limits (< 20 chars) in SEO & Translation prompts & post-processing
- [x] Mandate 11: Prompt Management Dashboard GET endpoint and `/settings/prompts` React Page

## New Tasks - Feature Completeness & Gap Resolution
- [ ] Task 11b: Backend: Reconstruct and clean up `backend/app/routers/pipeline.py`
  - Reassemble modular pipeline routes (`_modular_pipeline_generator`, `/upload`, `/inpainting`, `/local-correction`, `/save-workspace`) from `reconstructed_merged.py` and base file contents.
  - Ensure correct imports, WAL DB transactions, and proper error handling.
- [ ] Task 12: Backend: Add image count parameter (`n_images`) to generation pipelines & endpoints
  - Update `_modular_pipeline_generator` to support `n_images` parameter.
  - Save all generated paths inside `creation.source_png_variants_raw` as a comma-separated list of static paths.
  - Return the array of generated images in the SSE stream event `image_ready`.
- [ ] Task 13: Frontend: Add image count input dropdown (1-4) in `PipelineForm`
  - Add dropdown under AI Generation Options to select between 1 and 4 images.
  - Forward selection via form payload.
- [ ] Task 14: Frontend & Backend: Support displaying and selecting the best variant when multiple images are generated
  - Add `POST /api/creations/{creation_id}/select-variant` taking a `variant_path` body parameter, updating the primary stencil, and re-running downstream conversion tools.
  - Render an interactive variant gallery at the top of the review page, allowing the user to select their preferred stencil.
- [ ] Task 15: Frontend: Add copy-to-clipboard buttons next to prompt inputs and SEO fields in the review page
  - Integrate quick copy actions on all text inputs in `/review/[id]`.
- [ ] Task 16: Frontend & Backend: Allow direct stencil regeneration via custom prompt / theme modification on the review page
  - Display editable theme/prompt field on `/review/[id]`.
  - Add a regeneration action triggering modular pipeline reprocessing for that creation.
- [ ] Task 17: Frontend & Backend: Make the prompt management dashboard editable
  - Add custom prompt text columns to the `Setting` model (`models.py`) and schema migrations (`main.py`).
  - Read from DB in settings router and add `POST /api/settings/prompts` to update them.
  - Redesign `/settings/prompts` UI with editable textareas and save buttons.





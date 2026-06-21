# Implementation Plan — Universal AI Engine & Dynamic Failover

This plan outlines the refactoring of frontend configuration and backend engines to create an agnostic, multi-provider failover architecture for image and text/vision generation.

## User Review Required

> [!IMPORTANT]
> - New API keys (`replicate_key`, `openrouter_key`, `huggingface_key`, `anthropic_key`) will be added to the SQLite settings table via an automatic DB migration on startup.
1. **[image_engine.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/services/image_engine.py)**:
   - Added `local_binarize_opaque()` function to convert stencils to high-contrast opaque black `#000000` and white `#FFFFFF`.
   - Updated `execute_inpainting` to composite transparent input images onto a solid white background sheet using Pillow before invoking `client.images.edit` with the `gpt-image-2` model.
   - Updated unified mockup generation (`generate_real_mockup` and `generate_mockup` fallback) inside `generate_stencil_image` to force the application of the `tp.png` frame overlay (`apply_tp_overlay=True`) natively during automatic and manual generation loops.
   - Replaced all legacy `"dall-e-2"` model calls inside `stream_dalle_image_progressive` with native `"gpt-image-2"` to prevent HTTP 400 payload request crashes.
2. **[pipeline.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py)**:
   - Updated the initial binarization of uploaded `ready_bw_image` files in `_modular_pipeline_generator` to keep the canvas opaque white.
### 1. Database Model & Migration (`models.py`, `schemas.py`, `main.py`)
- Add fields to `Setting` model & Pydantic schemas:
  - `replicate_key`, `openrouter_key`, `huggingface_key`, `anthropic_key`
- In `main.py`, run SQLite `ALTER TABLE` migrations on startup to automatically add any missing columns.

### 2. Frontend Configuration & Create UI (`settings/page.tsx`, `page.tsx`)
- Update `settings/page.tsx` to include dropdowns and API key input fields for all providers:
  - **Image Provider Options**: `dall-e-3`, `dall-e-2`, `imagen-3-generate`, `imagen-3-edit`, `stable-diffusion-xl-core`, `stable-diffusion-3-pro`, `openrouter-flux-free`, `bria-2.3`, `black-forest-labs-flux-pro`.
  - **Text/Vision Options**: `claude-3-5-sonnet`, `claude-3-opus`, `gpt-4o`, `gpt-4o-mini`, `gemini-1.5-pro`, `gemini-1.5-flash`, `mistral-large-latest`, `llama-3-70b-instruct-openrouter`.
- Update `page.tsx` (the generation initiator) to fetch settings and send the advanced configuration payload to the backend stream URLs.

### 3. Agnostic Image Engine (`image_engine.py`)
- Create `ImageFactory` class to handle image generation via Replicate, Banana, Hugging Face, OpenAI, and Google GenAI.
- Implement priority loop fallback sequence starting with the user's preferred option.

### 4. Agnostic SEO & Vision Engine (`seo_engine.py`)
- Implement similar fallback loop with native structured Pydantic `EtsyListingSEO` validation for each provider.
- For providers without image vision capabilities (e.g. Mistral, LLaMA), catch/skip vision requests and dynamically route to vision-capable models (Claude 3.5 Sonnet, GPT-4o, Gemini).

### 5. Routers & Pipeline (`pipeline.py`, `creations.py`)
- Update SSE streaming pipeline and background tasks to parse the user's preferred provider choices and invoke the engines with failover safety.

---

## Verification Plan

### Automated Tests
- Run python compilation verification:
  ```bash
  python3 -m py_compile backend/app/routers/pipeline.py backend/app/routers/creations.py backend/app/services/*.py
  ```

### Manual Verification
- Access settings page, configure alternative image/text APIs.
- Trigger stencil generation and verify that quota errors (e.g., mock 429 errors or key exhaustion) gracefully cascade to fallback providers.


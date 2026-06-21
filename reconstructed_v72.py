# Implementation Plan — Backend Refactoring

This plan outlines the restructuring of the backend services to solve silent crashes, optimize image-to-image/text-to-image processing, ensure 100% mockup fidelity, and guarantee structured bilingual SEO packages.

## Proposed Architecture

To make the codebase robust and clean, we will split the responsibilities of `generator.py` into dedicated engine services:

```mermaid
graph TD
    Router[backend/app/routers/pipeline.py] --> ImageEngine[backend/app/services/image_engine.py]
    Router --> SEOEngine[backend/app/services/seo_engine.py]
    Router --> MockupEngine[backend/app/services/mockup_engine.py]
    Router --> VectorEngine[backend/app/services/vector.py]
```

### New Directory Structure
- [NEW] [image_engine.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/services/image_engine.py) : Pure local binarization (OpenCV/Pillow) for user-uploaded files vs. ex-nihilo generative AI (DALL-E 3 / Imagen 3) for text prompts.
- [NEW] [seo_engine.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/services/seo_engine.py) : Structured Gemini/Mistral output using Pydantic validation (or JSON output mode) and Multimodal Vision.
- [NEW] [mockup_engine.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/services/mockup_engine.py) : AI lifestyle background generator + local Python Pillow compositing (shadows/textures
# MISSING LINE 21
# MISSING LINE 22
# MISSING LINE 23
# MISSING LINE 24
# MISSING LINE 25
# MISSING LINE 26
# MISSING LINE 27
# MISSING LINE 28
# MISSING LINE 29
# MISSING LINE 30
# MISSING LINE 31
# MISSING LINE 32
# MISSING LINE 33
  - Raises standard exceptions (HTTP 500) if APIs fail (no silent Pillow fallback drawings).

### 2. SEO & Metadata Engine (`seo_engine.py`)
- Defines a Pydantic schema for the Etsy listing:
  ```python
  class EtsyListingSEO(BaseModel):
      title_fr: str
      title_en: str
      description_fr: str
      description_en: str
      tags_fr: list[str]
      tags_en: list[str]
  ```
- Uses Gemini Vision (`gemini-2.0-flash-lite` or `gemini-1.5-flash`) to analyze the generated/uploaded B&W stencil.
- Feeds this analysis into the text model using `response_mime_type="application/json"` with schema validation to guarantee a perfect JSON payload structure without regex/clean parsing.

### 3. Mockup Engine (`mockup_engine.py`)
- Generates only the background wall scene via AI (Imagen 3 / DALL-E 3).
- Uses Pillow locally to composite the SVG path/PNG stencil onto the background wall with natural drop-shadow offsets, keeping the original artwork 100% identical.

### 4. Router Update (`pipeline.py`)
- Update the SSE stream router to import and orchestrate the new image, SEO, and mockup engine functions.
- Ensure proper exception handling that yields the exact error details back to the client instead of silent fallbacks.

---

## Verification Plan

### Automated Tests
- Syntax and compilation verification:
  ```bash
  python3 -m py_compile backend/app/routers/pipeline.py backend/app/services/*.py
  ```

### Manual Verification
- Test image upload workflow: Verify it bypasses AI generation and performs a clean local binarization.
- Test text-to-stencil workflow: Verify the generated stencil doesn't have 3D effects, gradients, or shadows.
- Test SEO generation: Verify it produces correct Pydantic validated output for both languages based on image content.


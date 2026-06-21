# Implementation Plan - Image Retouching Quality Gate Modal

This plan outlines the refactoring of the image retouching workspace from a standalone tab/page into a strict, blocking Quality-Gate popup modal embedded in the creation pipeline flow (automatic/manual) and the review screen.

## User Review Required

> [!IMPORTANT]
> - The standalone `/workspace` page will be removed. The workspace will now strictly open as a modal inside the automatic/manual creation flows right after AI image generation completes, and from the Review page.
> - The canvas will strictly manipulate the master stencil image with its solid white background (`#FFFFFF`) and black shapes (`#000000`). Binarization and transparency conversion will only run after validation.

## Proposed Changes

### Backend Components

#### [MODIFY] [image_engine.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/services/image_engine.py)
- Add `local_binarize_opaque(input_path: str, output_path: str)` to convert an image to solid black `#000000` and solid white `#FFFFFF` (no transparent pixels).

#### [MODIFY] [pipeline.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py)
- Import `local_binarize_opaque` from `image_engine.py`.
- Update `_modular_pipeline_generator` for the `ready_bw_image` case to call `local_binarize_opaque` instead of `local_binarize_image` to ensure the canvas remains opaque white.
- Update `
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
# MISSING LINE 34
# MISSING LINE 35
# MISSING LINE 36
# MISSING LINE 37
# MISSING LINE 38
# MISSING LINE 39
# MISSING LINE 40
# MISSING LINE 41
# MISSING LINE 42
# MISSING LINE 43
# MISSING LINE 44
# MISSING LINE 45
# MISSING LINE 46
# MISSING LINE 47
# MISSING LINE 48
# MISSING LINE 49
#### [MODIFY] [page.tsx](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/frontend/app/review/%5Bid%5D/page.tsx)
- Remove the old Workspace shortcut panel.
- Import `RetouchModal` from `@/components/RetouchModal`.
- Add states `isRetouchModalOpen` and `reprocessing`.
- Add an "Edit/Retouch" button underneath each image/mockup/element card thumbnail in the Etsy Presentation Photos grid.
- Clicking the button opens `RetouchModal` pre-loaded with `creation.source_png_path` (stable opaque white background sheet).
- Upon `onValidate` inside the modal:
  - Set `reprocessing = true` (showing a loading spinner).
  - Make a POST request to `/api/pipeline/reprocess/{creation_id}` to regenerate all transparent elements, DXF/AI/EPS/PDF files, mockups, and ZIP.
  - Run `fetchCreation()` to update the page state cache with the new assets and close the modal.

---

## Verification Plan

### Automated Tests
- Build both frontend and backend to verify zero typescript/python compilation errors.

### Manual Verification
- **Automatic / Manual Flow**:
  1. Go to homepage, run a global theme design generation.
  2. Verify that the pipeline pauses right after the stencil is ready, opening the `RetouchModal`.
  3. Verify that the stencil background is opaque white.
  4. Perform some manual corrections (eraser/brush) and/or AI inpainting.
  5. Validate, and verify that the SSE stream resumes, runs downstream tasks, and shows mockups and CAD options reflecting the edits.
- **Review Gateway**:
  1. Go to a review page, verify the "Workspace" shortcut is gone.
  2. Click "Edit/Retouch" under any of the presentation thumbnails.
  3. Verify the modal opens with the opaque white sheet.
  4. Save an edit, validate, and verify that the page displays a spinner and then successfully updates all mockups and downloads.


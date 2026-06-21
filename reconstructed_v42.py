# Implementation Plan - Image Retouching Quality Gate Modal

This plan outlines the refactoring of the image retouching workspace from a standalone tab/page into a strict, blocking Quality-Gate popup modal embedded in the creation pipeline flow (automatic/manual) and the review screen.

## User Review Required

> [!IMPORTANT]
> - The standalone `/workspace` page will be removed. The workspace will now strictly open as a modal inside the automatic/manual creation flows right after AI image generation completes, and from the Review page.
> - The canvas will strictly manipulate the master stencil image with its solid white background (`#FFFFFF`) and black shapes (`#000000`). Binarization and transparency conversion will only run after validation.

## Proposed Changes

### Backend changes

#### [MODIFY] [pipeline.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py)
- Ensure `/stream/global` and `/stream/modular` can be paused or run in steps.
- Provide a clear endpoint route to save canvas modifications, overwrite the master `_source.png` file, and dynamically trigger downstream pipeline updates (slicing, CAD, PDF, mockup regenerations).
- Ensure the `generate_stencil_image` call does not apply `vectorize=True` during initial stencil creation, preserving the solid white background.

### Frontend changes

#### [NEW] [RetouchModal.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/RetouchModal.tsx)
- Create a purified workspace modal containing ONLY the Canvas Editor with the brush, eraser, manual canvas masking, and GPT-Image-2 layout-guided regeneration (excluding SEO/metadata fields).

#### [MODIFY] [page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/page.tsx)
- Refactor the pipeline execution hook to pause immediately after the `image_ready` event is received.
- Show the blocking `RetouchModal` popup asking: "Is the design correct or do you want to retouch it?".
- Upon clicking "Validate & Confirm", resume the pipeline by launching the downstream pipeline step sequence (vectorize, CAD, PDF, mockups, ZIP).

#### [MODIFY] [page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/review/%5Bid%5D/page.tsx)
- Add a prominent "Edit/Retouch" button under the main asset card thumbnail.
- Clicking it opens the `RetouchModal` pre-loaded with the opaque white master stencil.
- Validating the modal sends the modifications to the backend, forces regeneration of mockups and CAO files, and refreshes the review state.

## Verification Plan

### Manual Verification
- Launch a new creation in automatic mode. Verify the pipeline pauses right after image generation and shows the retouch modal.
- Verify the brush/eraser functions on the white canvas.
- Validate and confirm, and check that downstream steps run automatically and mockups update.
- Navigate to the review page, click "Edit/Retouch" under the thumbnail, perform an edit, validate, and verify that the review view updates with the modified design and lifestyle mockups.


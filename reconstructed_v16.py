# Walkthrough - Feature Restoration & SVG Fallback Correction

We have performed a complete review and restored all masked frontend options, including additional source type options and sub-mockup configuration controls. We also corrected the backend fallback search logic for unsuffixed single SVG and PNG files.

## Changes Made

### Frontend
- **PipelineForm Component**: Restored all source conditions (transparent PNG, vector SVG) and sub-mockup options (AI mockup, template wood backdrop) to [PipelineForm.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/PipelineForm.tsx) so all original features are fully visible and configureable.

### Backend
- **Source Files Fallback**: Corrected search logic in `_modular_pipeline_generator` within [pipeline.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py) to look for unsuffixed single `.svg` and `.png` files when there is no file count suffix like `_1`.

## Verification
- Clean compilation of all files.
- Successful Next.js build.


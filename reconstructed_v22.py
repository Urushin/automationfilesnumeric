# Walkthrough - Batch Upload & Output Splitter

We have implemented support for processing multiple files simultaneously and exporting them in assembled or split formats.

## Changes Made

### Frontend
- **FileUpload Component**: Updated [FileUpload.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/FileUpload.tsx) to accept multiple file selection. Added an alert warning that multiple files will share the same design theme and must be of the same format (PNG/SVG).
- **Workspace Settings**: Updated [page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/page.tsx) with:
  - Single/Multi-element structure selector for black & white images.
  - Automatic bundle size calculation/disabling when multiple files or multi-element layout is selected.
  - "Renvoyer en assemblée" and "Renvoyer en divisée" output checkboxes.
  - Submission payload forwarding of the multiple files list and selection states.

### Backend
- **Upload Route**: Modified the upload route in [pipeline.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py) to save all uploaded files sequentially with file indices (`_1_source.png`, `_2_source.png`).
- **Modular Pipeline Splitter**: Updated `_modular_pipeline_generator` to process all uploaded files. Integrated options for outputting elements in split layouts (separating sub-elements into individual files via contour analysis) or assembled formats.

## Verification
- Clean compilation of all files.
- Front-to-back integration complete.


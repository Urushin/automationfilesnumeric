# MISSING LINE 1
# MISSING LINE 2
# MISSING LINE 3
# MISSING LINE 4
# MISSING LINE 5
# MISSING LINE 6
# MISSING LINE 7
# MISSING LINE 8
1. **[image_engine.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/services/image_engine.py)**:
   - Added `local_binarize_opaque()` function to convert stencils to high-contrast opaque black `#000000` and white `#FFFFFF`.
   - Updated `execute_inpainting` to composite transparent input images onto a solid white background sheet using Pillow before invoking `client.images.edit` with the `gpt-image-2` model.
   - Updated unified mockup generation (`generate_real_mockup` and `generate_mockup` fallback) inside `generate_stencil_image` to force the application of the `tp.png` frame overlay (`apply_tp_overlay=True`) natively during automatic and manual generation loops.
2. **[pipeline.py](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py)**:
# MISSING LINE 14
# MISSING LINE 15
# MISSING LINE 16
# MISSING LINE 17
# MISSING LINE 18
# MISSING LINE 19
# MISSING LINE 20
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
# MISSING LINE 50

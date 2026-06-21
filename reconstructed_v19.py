# Action Checklist

## Step 1: Database & Migration Repairs
- [ ] Add `pipeline_status` and `selected_images_raw` columns to migrations in [main.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/main.py)
- [ ] Add `description` column to manual table creation DDL for `ideas_bank` in [main.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/main.py)
- [ ] Enable WAL mode in [main.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/main.py) and [database.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/database.py)

## Step 2: Image Pipeline & Multi-Element Split fixes
- [ ] Refactor `split_multielement_image` in [image_engine.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/services/image_engine.py) to use PIL-based white background composition.
- [ ] Update `convert_to_transparent_png` in [image.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/services/image.py) to preserve existing alpha channel.
- [ ] Fix swallowed exceptions in [mockup_engine.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/services/mockup_engine.py).

## Step 3: Event Loop Preservation & Async Routers
- [ ] Wrap blocking synchronous operations with `asyncio.to_thread` in [pipeline.py](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py).

## Step 4: Next.js Proxies and Unified Frontend Routing
- [ ] Add static rewrite rules in [next.config.ts](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/next.config.ts).
- [ ] Refactor relative api URLs to use `apiUrl` in [CanvasEditor.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/CanvasEditor.tsx), [ImageWorkspace.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/components/ImageWorkspace.tsx), [trends/page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/trends/page.tsx), and [settings/page.tsx](file:///Users/issam/Documents/Projets perso/AutomatisationNumericFiles/frontend/app/settings/page.tsx).


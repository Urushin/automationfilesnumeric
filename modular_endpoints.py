        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/stream/modular")
async def stream_modular_pipeline(
    creation_id: int,
    theme: str = "",
    generate_ai_stencil: bool = False,
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_real_mockup: bool = False,
    use_ai_mockup: bool = False,
    package: bool = False,
    generate_seo: bool = False,
    image_ai_provider: Optional[str] = None,
    text_ai_provider: Optional[str] = None,
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True
):
    pref_img = preferred_image_provider or image_ai_provider
    pref_txt = preferred_text_provider or text_ai_provider
    return StreamingResponse(
        _modular_pipeline_generator(
            creation_id=creation_id,
            generate_ai_stencil=generate_ai_stencil,
            vectorize=vectorize,
            convert_cad=convert_cad,
@router.get("/stream/modular")
async def stream_modular_pipeline(
    creation_id: int,
    theme: str = "",
    generate_ai_stencil: bool = False,
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_real_mockup: bool = False,
    use_ai_mockup: bool = False,
    package: bool = False,
    generate_seo: bool = False,
    image_ai_provider: Optional[str] = None,
    text_ai_provider: Optional[str] = None,
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True,
    mockup_styles: Optional[str] = None
):
    pref_img = preferred_image_provider or image_ai_provider
    pref_txt = preferred_text_provider or text_ai_provider
    return StreamingResponse(
        _modular_pipeline_generator(
            creation_id=creation_id,
            generate_ai_stencil=generate_ai_stencil,
            vectorize=vectorize,
            convert_cad=convert_cad,
            format_pdf=format_pdf,
            upscale=upscale,
            generate_real_mockup=generate_real_mockup,
            use_ai_mockup=use_ai_mockup,
            package=package,
            generate_seo=generate_seo,
            theme=theme,
            image_ai_provider=pref_img,
            text_ai_provider=pref_txt,
            design_style=design_style,
            source_type=source_type,
            output_assembled=output_assembled,
            output_split=output_split,
            strict_fidelity=strict_fidelity,
            mockup_styles=mockup_styles
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/stream/image")
async def stream_image(
    prompt: str,
    init_image_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    settings = get_or_create_settings(db)
    openai_key = settings.openai_key or os.getenv("OPENAI_API_KEY") or ""
    if not openai_key:
        raise HTTPException(status_code=400, detail="OpenAI API Key is missing.")
    return StreamingResponse(
        stream_dalle_image_progressive(openai_key, prompt, init_image_path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD FILE FOR MODULAR MODE
# ─────────────────────────────────────────────────────────────────────────────
from fastapi import UploadFile, File, Form
from ..schemas import CreationResponse


@router.post("/upload", response_model=CreationResponse)
async def upload_source_file(
    files: Optional[list[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    theme: str = Form("Fichier Importé"),
    bundle_size: int = Form(1),
    design_style: str = Form("classic"),
    source_type: Optional[str] = Form(None),
    source_is_multi_element: str = Form("single"),
    output_assembled: bool = Form(True),
    output_split: bool = Form(False),
    strict_fidelity: bool = Form(True),
    db: Session = Depends(get_db),
):
    # Resolve files
    uploaded_files = []
    if files:
        uploaded_files = files
    elif file:
        uploaded_files = [file]

    if not uploaded_files and not image_url and source_type != "text_prompt":
        raise HTTPException(status_code=400, detail="Aucun fichier ou image_url fourni.")

    # Intercept mask upload to strictly save it in tempfile directory to prevent DB pollution
    if theme.startswith("mask_") or theme.startswith("mask"):
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()

        # Save uploaded file
        if uploaded_files:
            with open(temp_file_path, "wb") as f_out:
                shutil.copyfileobj(uploaded_files[0].file, f_out)
        elif image_url:
            resp = requests.get(image_url, timeout=15)
            resp.raise_for_status()
            with open(temp_file_path, "wb") as f_out:
                f_out.write(resp.content)

        return {
            "id": 0,
            "theme": theme,
            "source_png_path": temp_file_path,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "is_published_etsy": False,
            "bundle_size": 1,
            "source_type": "ready_bw_image"
        }

    # Determine first file
    ref_filename = uploaded_files[0].filename if uploaded_files else (image_url or "file.png")
    inferred_type = source_type
    if not inferred_type:
        inferred_type = "raw_image"
        if ref_filename.lower().endswith(".svg"):
            inferred_type = "vector_svg"

    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
        bundle_size=bundle_size if len(uploaded_files) <= 1 else len(uploaded_files),
        source_type=inferred_type,
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)

    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)

    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme).strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation.id}"

    # For multiple files, save each file. First file is the reference master source.
    saved_paths = []
    is_svg = ref_filename.lower().endswith(".svg") or inferred_type == "vector_svg"

    def _save_upload_sync(file_file, path):
        with open(path, "wb") as f_out:
            shutil.copyfileobj(file_file, f_out)

    def _download_url_sync(url, path):
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(path, "wb") as f_out:
            f_out.write(resp.content)

    for idx, f_obj in enumerate(uploaded_files):
        suffix = f"_{idx+1}" if len(uploaded_files) > 1 else ""
        if is_svg:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.svg")
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
            saved_paths.append(target_path)
        else:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.png")
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
            saved_paths.append(target_path)

    # Handle image url fallback
    if not uploaded_files and image_url:
        suffix = ""
        if is_svg:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.svg")
            await asyncio.to_thread(_download_url_sync, image_url, target_path)
            saved_paths.append(target_path)
        else:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.png")
            await asyncio.to_thread(_download_url_sync, image_url, target_path)
            saved_paths.append(target_path)
        # Setup paths
        creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
        import re
        safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
        if not safe_theme:
            safe_theme = f"design_{creation_id}"
            
        source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
        binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
        
        # 1. Binarize
        local_binarize_image(source_png, binarized_png)
        
        # 2. Slice
        bundle_size = creation.bundle_size or 4
        element_paths = []
        if bundle_size > 1 and (creation.source_type or "text_prompt") != "vector_svg":
            element_paths = split_multielement_image(binarized_png, creation_dir, bundle_size)
        if not element_paths:
            element_paths = [binarized_png]
            
        elements = []
        for idx, el_png in enumerate(element_paths):
            el_name = f"{safe_theme}_{idx+1}" if len(element_paths) > 1 else safe_theme
            elements.append({
                "source_png": el_png,
                "base_name": el_name,
                "svg_path": os.path.join(creation_dir, f"{el_name}.svg"),
                "dxf_path": os.path.join(creation_dir, f"{el_name}.dxf"),
                "ai_path": os.path.join(creation_dir, f"{el_name}.ai"),
                "eps_path": os.path.join(creation_dir, f"{el_name}.eps"),
                "pdf_path": os.path.join(creation_dir, f"{el_name}.pdf"),
                "upscale_png": os.path.join(creation_dir, f"{el_name}.png"),
            })
            
        # 3. Vectorize, CAD, Upscale, PDF
        svg_urls = []
        dxf_urls = []
        ai_urls = []
        eps_urls = []
                pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
                
        # 4. Mockups
        master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
        if os.path.exists(binarized_png):
            convert_to_transparent_png(binarized_png, master_upscale, 3)
        png_for_mockup = master_upscale if os.path.exists(master_upscale) else binarized_png
        
        mockup_raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
        mockup_commercial_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
        
        try:
            from ..services.image_engine import generate_mockup_backdrop
            backdrop_bytes = generate_mockup_backdrop(creation.theme or "Design", settings.openai_key)
            import tempfile
            temp_bg = tempfile.mktemp(suffix=".jpg")
            with open(temp_bg, 'wb') as f:
                f.write(backdrop_bytes)
                
            from ..services.mockup_engine import composite_stencil_on_bg
            
            # Export 1: Raw Mockup
            composite_stencil_on_bg(
                stencil_path=png_for_mockup,
                bg_path=temp_bg,
                output_path=mockup_raw_path,
                material="matte_black_metal",
                apply_tp_overlay=False
            )
                
            # PDF
            png_to_pdf(el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"], el["pdf_path"])
            if os.path.exists(el["pdf_path"]):
                pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
                
        # 4. Mockups
        master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
        if os.path.exists(binarized_png):
            convert_to_transparent_png(binarized_png, master_upscale, 3)
        png_for_mockup = master_upscale if os.path.exists(master_upscale) else binarized_png
        
        mockup_raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
        mockup_commercial_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
        
        try:
            from ..services.image_engine import generate_mockup_backdrop
            backdrop_bytes = generate_mockup_backdrop(creation.theme or "Design", settings.openai_key)
            import tempfile
            temp_bg = tempfile.mktemp(suffix=".jpg")
            with open(temp_bg, 'wb') as f:
                f.write(backdrop_bytes)
                
            from ..services.mockup_engine import composite_stencil_on_bg
            
            # Export 1: Raw Mockup
            composite_stencil_on_bg(
                stenc
            package_assets(assets_to_zip, zip_path)
            
        # Update DB
        creation.svg_path = svg_urls[0] if svg_urls else None
        creation.svg_paths = svg_urls
        creation.dxf_path = dxf_urls[0] if dxf_urls else None
        creation.ai_path = ai_urls[0] if ai_urls else None
        creation.eps_path = eps_urls[0] if eps_urls else None
        creation.upscale_png_path = png_urls[0] if png_urls else None
        creation.png_paths = png_urls
        creation.pdf_path = pdf_urls[0] if pdf_urls else None
        creation.pdf_paths = pdf_urls
        creation.mockup_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
        creation.real_mockup_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}" if os.path.exists(zip_path) else None
        creation.status = "completed"
        creation.current_step = "Terminé ✓"
        db.commit()
    except Exception as e:
        print(f"[pipeline] Downstream regeneration error: {e}")
        import traceback
        traceback.print_exc()
                )
                # Commercial Mockup
                composite_stencil_on_bg(
                    stencil_path=png_for_mockup,
                    bg_path=temp_bg,
                    output_path=mockup_commercial_path,
                    material="matte_black_metal",
                    apply_tp_overlay=True
                )
                
                if idx == 0:
                    first_raw_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}"
                    first_comm_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial_path)}"
                
                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
        except Exception as mockup_err:
            print(f"[pipeline] Reprocess Mockup dual-processing failed: {mockup_err}")
            
        # 5. ZIP
        zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
        assets_to_zip = []
        for el in elements:
            for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                p = el[path_key]
                if p and os.path.exists(p):
                    assets_to_zip.append(p)
        
        # Include all fresh mockup paths in ZIP
        for idx in range(len(parsed_styles)):
            raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw_{idx+1}.jpg")
            comm_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial_{idx+1}.jpg")
            if os.path.exists(raw_path):
                assets_to_zip.append(raw_path)
            if os.path.exists(comm_path):
                assets_to_zip.append(comm_path)
                
        if assets_to_zip:
            assets_to_zip = list(dict.fromkeys(assets_to_zip))
            package_assets(assets_to_zip, zip_path)
            
        # Update DB
        creation.svg_path = svg_urls[0] if svg_urls else None
        creation.svg_paths = svg_urls
        creation.dxf_path = dxf_urls[0] if dxf_urls else None
        creation.ai_path = ai_urls[0] if ai_urls else None
        creation.eps_path = eps_urls[0] if eps_urls else None
        creation.upscale_png_path = png_urls[0] if png_urls else None
        creation.png_paths = png_urls
        creation.pdf_path = pdf_urls[0] if pdf_urls else None
        creation.pdf_paths = pdf_urls
        creation.mockup_path = first_raw_path
        creation.real_mockup_path = first_comm_path
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}" if os.path.exists(zip_path) else None
        creation.status = "completed"
        creation.current_step = "Terminé ✓"
        db.commit()
    except Exception as e:
        print(f"[pipeline] Downstream regeneration error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


@router.post("/inpainting")
async def pipeline_inpainting(
    background_tasks: BackgroundTasks,
    image_path: str = Form(...),
    mask_path: str = Form(...),
    prompt: str = Form(...),
    output_path: str = Form(...),
    creation_id: int = Form(...)
):
    try:
        from ..services.image_engine import execute_inpainting
        from ..routers.settings import get_or_create_settings
        db = SessionLocal()
        settings = get_or_create_settings(db)
        openai_key = settings.openai_key
        db.close()
        
        # Strip local server domain prefix if accidentally appended by the frontend
        for var_name in ["image_path", "mask_path", "output_path"]:
            val = locals().get(var_name)
            if val and (val.startswith("http://") or val.startswith("https://")):
                import urllib.parse
                parsed_url = urllib.parse.urlparse(val)
                if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                    if var_name == "image_path":
                        image_path = parsed_url.path
                    elif var_name == "mask_path":
                        mask_path = parsed_url.path
                    elif var_name == "output_path":
                        output_path = parsed_url.path

        # Convert web relative paths to server local paths if necessary
        # e.g., /static/creation_1/design_1_source.png -> backend/storage/creation_1/design_1_source.png
        image_path_clean = image_path.split("?")[0]
        mask_path_clean = mask_path.split("?")[0]
        output_path_clean = output_path.split("?")[0]
        
        local_img = image_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_mask = mask_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_out = output_path_clean.replace("/static/", STORAGE_DIR + "/")
        
        # Make directories if needed
        os.makedirs(os.path.dirname(local_out), exist_ok=True)

        await asyncio.to_thread(
            execute_inpainting,
            local_img,
            local_mask,
            prompt,
            local_out,
            openai_key
        )
        
        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)
        
        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-correction")
async def pipeline_local_correction(
    background_tasks: BackgroundTasks,
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
            local_mask,
            prompt,
            local_out,
            openai_key
        )
        
        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)
        
        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-correction")
async def pipeline_local_correction(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    creation_id: int = Form(...),
    output_path: str = Form(...)
):
    try:
        # Strip local server domain prefix if accidentally appended by the frontend
        if output_path.startswith("http://") or output_path.startswith("https://"):

@router.post("/save-workspace", status_code=202)
async def save_workspace_canvas(
    req: SaveWorkspaceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        creation = db.query(Creation).filter(Creation.id == req.creation_id).first()
        if not creation:
            raise HTTPException(status_code=404, detail="Creation non trouvée")

        asset_path = req.asset_path
        if asset_path:
            if asset_path.startswith("http://") or asset_path.startswith("https://"):
                asset_path = "/" + asset_path.split("/", 3)[-1]
            local_path = asset_path.replace("/static/", STORAGE_DIR + "/")
        else:
            source_png_path = creation.source_png_path
    theme: Optional[str] = None
    canvas_data: Optional[str] = None  # Holds the serialized canvas strokes/mask data
    canvasData: Optional[str] = None  # Alias/Fallback for compatibility
    asset_path: Optional[str] = None
    asset_type: Optional[str] = "master_stencil"

    class Config:
        from_attributes = True


def run_downstream_pipeline_operations(creation_id: int, local_path: str, asset_type: str):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
        
        if asset_type == "master_stencil":
            from ..services.image_engine import local_binarize_opaque
            local_binarize_opaque(local_path, local_path)
            reprocess_creation_assets(creation.id)

        elif asset_type == "split_element":
            from ..services.image_engine import convert_to_transparent_png
            convert_to_transparent_png(local_path, local_path, 3)

            settings = get_or_create_settings(db)
            creation_dir = os.path.dirname(local_path)
            import re
            safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
            if not safe_theme:
                safe_theme = f"design_{creation.id}"

            mockup_raw_path = os.path.join(crea
            "selected_images_raw": creation.selected_images_raw,
            if asset_path.startswith("http://") or asset_path.startswith("https://"):
                asset_path = "/" + asset_path.split("/", 3)[-1]
            local_path = asset_path.replace("/static/", STORAGE_DIR + "/")
        else:
            source_png_path = creation.source_png_path
            if not source_png_path:
                import re
                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
                if not safe_theme:
                    safe_theme = f"design_{creation.id}"
                
                # Export 1: Raw Mockup (WITHOUT watermark)
                composite_stencil_on_bg(
                    stencil_path=local_path,
                    bg_path=temp_bg,
                    output_path=mockup_raw_path,
                    material="matte_black_metal",
                    apply_tp_overlay=False
                )
                
                # Export 2: Commercial Mockup (WITH watermark)
                composite_stencil_on_bg(
                    stencil_path=local_path,
                    bg_path=temp_bg,
                    output_path=mockup_commercial_path,
                    material="matte_black_metal",
                    apply_tp_overlay=True
                )
                
                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
            except Exception as mockup_err:
                print(f"[pipeline] split_element mockup generation failed: {mockup_err}")

            creation.mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
            creation.real_mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
            creation.status = "completed"
            creation.current_step = "Terminé ✓"
            db.commit()
            
    except Exception as e:
        print(f"[pipeline] Background processing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


@router.post("/save-workspace", status_code=202)
async def save_workspace_canvas(
    req: SaveWorkspaceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        creation = db.query(Creation).filter(Creation.id == req.creation_id).first()
        if not creation:
            raise HTTPException(status_code=404, detail="Creation non trouvée")

        asset_path = req.asset_path
        if asset_path:
            if asset_path.startswith("http://") or asset_path.startswith("https://"):
                asset_path = "/" + asset_path.split("/", 3)[-1]
            local_path = asset_path.replace("/static/", STORAGE_DIR + "/")
        else:
            source_png_path = creation.source_png_path
            if not source_png_path:
                import re
                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
                if not safe_theme:
                    safe_theme = f"design_{creation.id}"
                source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
                creation.source_png_path = source_png_path
                db.commit()
            local_path = source_png_path.replace("/static/", STORAGE_DIR + "/")

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        canvas_data_raw = req.canvas_data or req.canvasData
        if not canvas_data_raw:
            raise HTTPException(status_code=400, detail="Missing canvasData or canvas_data")
        header, encoded = canvas_data_raw.split(",", 1)
        data = base64.b64decode(encoded)

        def _write_bytes():
            with open(local_path, "wb") as f:
                f.write(data)
        await asyncio.to_thread(_write_bytes)

        asset_type = req.asset_type or "master_stencil"
        
        # Enforce pipeline status to "processing" to trigger the spinner/polling on UI
        creation.status = "processing"
        creation.current_step = "Régénération des assets..."
        db.commit()

        # Schedule the heavy processing as a background task
        background_tasks.add_task(
            run_downstream_pipeline_operations,
            creation_id=creation.id,
            local_path=local_path,
            asset_type=asset_type
        )

        return {
            "status": "processing",
            "message": "Workspace saved. Downstream generation started in background."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))




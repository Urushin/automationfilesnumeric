import os
import json
import time
import requests
import base64
import hashlib
import re
from typing import Optional, Dict, Any

ETSY_API_URL = "https://api.etsy.com/v3/application"
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def clean_text_for_title(text: str) -> str:
    if not text:
        return ""
    # Replace & with and
    text = text.replace("&", "and")
    # Remove < > " and control characters
    text = re.sub(r'[<>"\\\x00-\x1f]', "", text)
    # Strip multiple spaces
    text = re.sub(r'\s+', " ", text)
    return text.strip()

def clean_tag(tag: str) -> str:
    if not tag:
        return ""
    import unicodedata
    # Normalize accents/diacritics
    tag = unicodedata.normalize("NFKD", str(tag))
    tag = tag.encode("ascii", "ignore").decode("ascii")
    # Remove illegal tag chars: , ; : ! @ # $ % ^ * ( ) + = { } [ ] | \ < > / and control chars
    tag = re.sub(r'[,;:!@#$%\^\*\(\)\+=\{\}\[\]\|\\<>\/\x00-\x1f]', "", tag)
    # Strip multiple spaces
    tag = re.sub(r'\s+', " ", tag)
    # Truncate to 20 chars max
    return tag.strip()[:20]

def auto_clean_metadata_for_etsy(creation):
    """
    Cleans and conforms creation titles, tags, and descriptions to strictly respect
    Etsy API limits and illegal character restrictions.
    """
    # Clean titles
    if creation.title_en:
        creation.title_en = clean_text_for_title(creation.title_en)[:140]
    if creation.title_fr:
        creation.title_fr = clean_text_for_title(creation.title_fr)[:140]
        
    # Clean tags EN
    if creation.tags_en:
        tags = [clean_tag(t) for t in creation.tags_en.split(",") if t.strip()]
        # Remove empty tags and keep first 13
        tags = [t for t in tags if t][:13]
        creation.tags_en = ",".join(tags)
        
    # Clean tags FR
    if creation.tags_fr:
        tags = [clean_tag(t) for t in creation.tags_fr.split(",") if t.strip()]
        tags = [t for t in tags if t][:13]
        creation.tags_fr = ",".join(tags)

def generate_pkce_pair() -> tuple:
    """Generates code verifier and code challenge for PKCE OAuth."""
    # Create random string of 32 bytes
    verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').replace('=', '')
    
    # Create challenge
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    challenge = base64.urlsafe_b64encode(sha256).decode('utf-8').replace('=', '')
    
    return verifier, challenge

def is_token_expired(token_data: Dict[str, Any]) -> bool:
    """Check if the access token has expired (adding a 60 second safety buffer)."""
    if not token_data or 'access_token' not in token_data:
        return True
    
    created_at = token_data.get('created_at', 0)
    expires_in = token_data.get('expires_in', 0)
    
    return time.time() > (created_at + expires_in - 60)

def refresh_etsy_token(client_id: str, client_secret: Optional[str], refresh_token: str) -> Dict[str, Any]:
    """Refreshes the Etsy access token."""
    url = "https://api.etsy.com/v3/public/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token
    }
    
    # If client secret is provided, add it (Etsy confidential vs public client)
    if client_secret:
        payload["client_secret"] = client_secret
        
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(url, data=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Failed to refresh Etsy token: {response.text}")
        
    new_token_data = response.json()
    new_token_data["created_at"] = time.time()
    return new_token_data

def get_valid_token(settings, db) -> tuple:
    """Gets a valid access token. Refreshes if expired. Raises error if not connected."""
    if not settings.etsy_client_id or not settings.etsy_oauth_token:
        raise ValueError("Etsy credentials or connection is missing.")
        
    token_data = json.loads(settings.etsy_oauth_token)
    
    if is_token_expired(token_data):
        print("Etsy token is expired. Refreshing...")
        try:
            new_token_data = refresh_etsy_token(
                settings.etsy_client_id, 
                settings.etsy_client_secret, 
                token_data.get("refresh_token")
            )
            settings.etsy_oauth_token = json.dumps(new_token_data)
            db.commit()
            return new_token_data.get("access_token"), settings.etsy_client_id
        except Exception as e:
            raise Exception(f"Etsy authentication token refresh failed: {e}")
            
    return token_data.get("access_token"), settings.etsy_client_id

def get_etsy_shop_id(access_token: str, client_id: str) -> str:
    """Retrieves the primary Shop ID for the authenticated user."""
    headers = {
        "x-api-key": client_id,
        "Authorization": f"Bearer {access_token}"
    }
    
    # Get user ID
    user_url = f"{ETSY_API_URL}/users/me"
    user_resp = requests.get(user_url, headers=headers, timeout=30)
    if user_resp.status_code != 200:
        raise Exception(f"Etsy /users/me failed: {user_resp.text}")
        
    user_id = user_resp.json().get("user_id")
    
    # Get shop ID
    shop_url = f"{ETSY_API_URL}/users/{user_id}/shops"
    shop_resp = requests.get(shop_url, headers=headers, timeout=30)
    if shop_resp.status_code != 200:
        raise Exception(f"Etsy fetch shops failed: {shop_resp.text}")
        
    shops_data = shop_resp.json()
    if "results" in shops_data and shops_data["results"]:
        return str(shops_data["results"][0].get("shop_id"))
    if not shops_data or "shop_id" not in shops_data:
        raise Exception("Authenticated Etsy account has no associated shop.")
        
    return str(shops_data.get("shop_id"))

def storage_url_to_path(storage_url: Optional[str]) -> Optional[str]:
    """Convert a /static/... or /assets/... URL stored in SQLite to a backend filesystem path."""
    if not storage_url:
        return None
    if os.path.isabs(storage_url):
        return storage_url
    if storage_url.startswith("/static/"):
        return os.path.join(BACKEND_DIR, "storage", storage_url.removeprefix("/static/"))
    if storage_url.startswith("/assets/"):
        return os.path.join(BACKEND_DIR, "assets", storage_url.removeprefix("/assets/"))
    return storage_url


# ─────────────────────────────────────────────────────────────────────────────
# TAXONOMY SUGGESTION
# ─────────────────────────────────────────────────────────────────────────────
# Mapping thème → taxonomy_id Etsy
TAXONOMY_RULES = [
    (["svg", "vector", "digital", "download", "eps", "ai"], 2044),      # SVG Files
    (["laser", "cnc", "glowforge", "xtool", "sculpfun", "trotec"], 11549),  # Laser Cut Files
    (["stencil", "pochoir", "template", "pochoir mur"], 2048),             # Stencils
    (["dxf", "cad", "cao", "fraiseuse", "cnc"], 11549),                    # Laser Cut Files
    (["cricut", "silhouette", "cameo"], 2044),                             # SVG Files
]

def _suggest_taxonomy(tags_text: str) -> int:
    """
    Suggète le taxonomy_id Etsy le plus pertinent basé sur les tags.
    Fallback : 2043 (Digital Prints / Stencil Patterns - générique)
    """
    if not tags_text:
        return 2043
    tags_lower = tags_text.lower()
    for keywords, taxonomy_id in TAXONOMY_RULES:
        if any(kw in tags_lower for kw in keywords):
            return taxonomy_id
    return 2043

def publish_listing_to_etsy(settings, creation, db) -> Dict[str, Any]:
    """
    Publishes the creation on Etsy.
    If Etsy integration parameters are missing or set to a mock token,
    runs in Simulation Mode for local demo / sandbox validation.
    """
    # Auto-clean metadata to conform to Etsy guidelines
    auto_clean_metadata_for_etsy(creation)
    db.commit()

    # Guardrail Check - Simulation Mode trigger
    is_simulation = False
    if (not settings.etsy_client_id or 
        not settings.etsy_oauth_token or 
        settings.etsy_oauth_token == "mock_mode_active"):
        is_simulation = True
        
    if is_simulation:
        # Mock success response
        time.sleep(1.5)  # Simulate network latency
        mock_listing_id = f"sim-{int(time.time())}"
        
        creation.is_published_etsy = True
        creation.etsy_listing_id = mock_listing_id
        db.commit()
        
        return {
            "success": True,
            "is_simulation": True,
            "listing_id": mock_listing_id,
            "listing_url": f"https://www.etsy.com/your/shops/me/dashboard"
        }
        
    # --- REAL ETSY PUBLISHING API ---
    access_token, client_id = get_valid_token(settings, db)
    shop_id = get_etsy_shop_id(access_token, client_id)
    
    headers = {
        "x-api-key": client_id,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Auto-suggest taxonomy from tags
    tags_for_taxonomy = (creation.tags_en or "") + "," + (creation.tags_fr or "")
    suggested_taxonomy = _suggest_taxonomy(tags_for_taxonomy)

    # Build combined title: EN first, then FR, separated by " | " if both are present
    title_en = creation.title_en or ""
    title_fr = creation.title_fr or ""
    if title_en and title_fr and title_en.lower() != title_fr.lower():
        combined_title = f"{title_en} | {title_fr}"
    elif title_en:
        combined_title = title_en
    else:
        combined_title = title_fr
    combined_title = clean_text_for_title(combined_title)[:140]

    # Build bilingual description (EN first for Etsy default, then FR)
    description_en = creation.description_en or ""
    description_fr = creation.description or ""
    
    # Build combined description: English first (Etsy is 80% EN), then French section
    if description_en and description_fr:
        full_description = description_en + "\n\n---\n\n🇫🇷 **VERSION FRANÇAISE**\n\n" + description_fr
    elif description_en:
        full_description = description_en
    else:
        full_description = description_fr

    # Build tag list (merge EN first, then FR to fill remaining slots, max 13)
    tags_list = []
    seen_tags: set = set()
    en_tags = [t.strip() for t in (creation.tags_en or "").split(",") if t.strip()]
    fr_tags = [t.strip() for t in (creation.tags_fr or "").split(",") if t.strip()]
    for t in en_tags + fr_tags:
        if t not in seen_tags and len(tags_list) < 13:
            seen_tags.add(t)
            tags_list.append(t)

    # 1. Create digital listing shell
    listing_payload = {
        "title": combined_title,
        "description": full_description,
        "price": creation.price or settings.default_price,
        "quantity": creation.quantity or settings.default_quantity,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "is_supply": False,
        "taxonomy_id": suggested_taxonomy,
        "state": settings.default_status.lower(),  # draft or active
        "type": "download"    # Crucial for digital product
    }
    if tags_list:
        listing_payload["tags"] = tags_list
    
    create_url = f"{ETSY_API_URL}/shops/{shop_id}/listings"
    create_resp = requests.post(create_url, headers=headers, json=listing_payload, timeout=30)
    if create_resp.status_code not in (200, 201):
        raise Exception(f"Etsy listing creation failed: {create_resp.text}")
        
    listing_id = create_resp.json().get("listing_id")
    
    # 2. Upload Selected Images sequentially
    selected_assets = []
    if creation.selected_images_raw:
        selected_assets = [p.strip() for p in creation.selected_images_raw.split(",") if p.strip()]
    else:
        # Default fallback list in sensible order: plural/all mockups first, then design PNGs
        real_list = getattr(creation, "real_mockup_paths", [])
        if not real_list and creation.real_mockup_path:
            real_list = [creation.real_mockup_path]
            
        raw_list = getattr(creation, "mockup_paths", [])
        if not raw_list and creation.mockup_path:
            raw_list = [creation.mockup_path]
            
        for p in real_list:
            if p and p not in selected_assets:
                selected_assets.append(p)
        for p in raw_list:
            if p and p not in selected_assets:
                selected_assets.append(p)
        if creation.png_paths:
            for p in creation.png_paths:
                if p not in selected_assets:
                    selected_assets.append(p)

    # Exclude raw source png path from any upload
    source_png_url = creation.source_png_path
    selected_assets = [p for p in selected_assets if p != source_png_url]

    # Categorize assets
    images_to_upload = []
    digital_files_to_upload = []

    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    FILE_EXTS = {".zip", ".pdf", ".svg", ".ai", ".eps", ".dxf"}

    for asset in selected_assets:
        lower_asset = asset.lower()
        _, ext = os.path.splitext(lower_asset)
        if ext in IMAGE_EXTS:
            images_to_upload.append(asset)
        elif ext in FILE_EXTS:
            digital_files_to_upload.append(asset)

    # Filter out empty paths, blacklisted paths, and map to local filesystem
    ETSY_IMAGE_BLACKLIST = {"/assets/templates/condition_dl.png"}
    valid_image_paths = []
    for img_url in images_to_upload:
        if img_url in ETSY_IMAGE_BLACKLIST:
            continue
        local_path = storage_url_to_path(img_url)
        if local_path and os.path.exists(local_path) and local_path not in valid_image_paths:
            valid_image_paths.append(local_path)
            
    # Limit to 10 images (Etsy limit)
    valid_image_paths = valid_image_paths[:10]

    if valid_image_paths:
        img_upload_url = f"{ETSY_API_URL}/shops/{shop_id}/listings/{listing_id}/images"
        multipart_headers = {
            "x-api-key": client_id,
            "Authorization": f"Bearer {access_token}"
        }
        for rank_idx, img_file_path in enumerate(valid_image_paths):
            try:
                mime_type = "image/png" if img_file_path.lower().endswith(".png") else "image/jpeg"
                with open(img_file_path, "rb") as img_file:
                    files = {"image": (os.path.basename(img_file_path), img_file, mime_type)}
                    data = {"rank": rank_idx + 1}
                    img_resp = requests.post(img_upload_url, headers=multipart_headers, files=files, data=data, timeout=60)
                    if img_resp.status_code not in (200, 201):
                        print(f"Warning: Image upload failed for {img_file_path}: {img_resp.text}")
                    else:
                        print(f"Successfully uploaded listing image {img_file_path} at rank {rank_idx + 1}")
            except Exception as ie:
                print(f"Exception during image upload for {img_file_path}: {ie}")
                
    # Parse digital files
    valid_digital_files = []
    for f_url in digital_files_to_upload:
        local_path = storage_url_to_path(f_url)
        if local_path and os.path.exists(local_path) and local_path not in valid_digital_files:
            valid_digital_files.append(local_path)

    # Fallback to ZIP package if no files selected
    if not valid_digital_files:
        fallback_zip = storage_url_to_path(creation.zip_path)
        if fallback_zip and os.path.exists(fallback_zip):
            valid_digital_files.append(fallback_zip)

    # Limit to 5 digital files (Etsy limit)
    valid_digital_files = valid_digital_files[:5]

    # Upload digital files
    if valid_digital_files:
        file_upload_url = f"{ETSY_API_URL}/shops/{shop_id}/listings/{listing_id}/files"
        multipart_headers = {
            "x-api-key": client_id,
            "Authorization": f"Bearer {access_token}"
        }
        for f_path in valid_digital_files:
            try:
                mime_type = "application/zip" if f_path.lower().endswith(".zip") else "application/octet-stream"
                if f_path.lower().endswith(".pdf"):
                    mime_type = "application/pdf"
                
                with open(f_path, "rb") as digital_file:
                    files = {"file": (os.path.basename(f_path), digital_file, mime_type)}
                    file_resp = requests.post(file_upload_url, headers=multipart_headers, files=files, timeout=60)
                    if file_resp.status_code not in (200, 201):
                        raise Exception(f"Digital file attachment failed for {f_path}: {file_resp.text}")
                    else:
                        print(f"Successfully uploaded listing file {f_path}")
            except Exception as fe:
                raise Exception(f"Digital file upload failed for {f_path}: {str(fe)}")
                
    # Save publication info to database
    creation.is_published_etsy = True
    creation.etsy_listing_id = str(listing_id)
    db.commit()
    
    return {
        "success": True,
        "is_simulation": False,
        "listing_id": str(listing_id),
        "listing_url": f"https://www.etsy.com/listing/{listing_id}"
    }

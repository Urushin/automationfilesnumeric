"""
SVG Connectivity Analyzer & Auto-Bridging Engine
Analyse un fichier SVG ou PNG pour détecter les îles flottantes (pièces détachées)
qui tomberaient lors de la découpe laser et propose un pontage automatique (Auto-Bridge).
"""
import os
import re
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from xml.etree import ElementTree as ET
from typing import Dict, Any, List, Tuple


def analyze_svg_connectivity(svg_path: str) -> dict:
    """
    Parse le fichier SVG et compte le nombre de <path> éléments racines.
    """
    if not os.path.exists(svg_path):
        return {
            "island_count": 0,
            "severity": "unknown",
            "message": "Fichier SVG introuvable.",
            "safe_to_cut": False,
        }

    try:
        with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        content_clean = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', "", content)
        root = ET.fromstring(content_clean)

        path_count = 0

        def count_paths(node, depth=0):
            nonlocal path_count
            for child in node:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "path":
                    path_count += 1
                elif tag in ("g", "svg") and depth < 3:
                    count_paths(child, depth + 1)

        count_paths(root)

        if path_count <= 1:
            severity = "ok"
            message = "Design entièrement connecté — prêt pour la découpe laser."
            safe_to_cut = True
        elif path_count <= 3:
            severity = "warning"
            message = f"{path_count} sous-chemins détectés. Vérifiez visuellement que toutes les pièces sont connectées."
            safe_to_cut = True
        else:
            severity = "critical"
            message = f"⚠️ {path_count} îles indépendantes détectées ! Des pièces pourraient tomber lors de la découpe laser."
            safe_to_cut = False

        return {
            "island_count": path_count,
            "severity": severity,
            "message": message,
            "safe_to_cut": safe_to_cut,
        }

    except ET.ParseError as e:
        return {
            "island_count": -1,
            "severity": "error",
            "message": f"Impossible de parser le SVG : {e}",
            "safe_to_cut": False,
        }
    except Exception as e:
        return {
            "island_count": -1,
            "severity": "error",
            "message": f"Erreur d'analyse SVG : {e}",
            "safe_to_cut": False,
        }


def detect_floating_islands(image_path: str, min_island_area: int = 15) -> Dict[str, Any]:
    """
    Analyse précise par vision par ordinateur des pièces noires flottantes
    (îlots non reliés au corps principal du pochoir).

    Returns:
        dict: {
            "island_count": int,
            "islands": [
                {
                    "id": int,
                    "bbox": [x, y, w, h],
                    "centroid": [cx, cy],
                    "area": int
                }
            ],
            "main_body_area": int,
            "total_components": int
        }
    """
    if not os.path.exists(image_path):
        return {"island_count": 0, "islands": [], "main_body_area": 0, "total_components": 0}

    # Load in grayscale
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        return {"island_count": 0, "islands": [], "main_body_area": 0, "total_components": 0}

    # Binarize: black matter is foreground (255), white background is 0
    _, binary = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)

    # Connected components analysis (8-connectivity)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    if num_labels <= 1:
        return {"island_count": 0, "islands": [], "main_body_area": 0, "total_components": 0}

    # Label 0 is the background. Components are 1..num_labels-1
    # Find largest component as main connected structure
    areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
    main_body_idx = int(np.argmax(areas)) + 1
    main_body_area = int(stats[main_body_idx, cv2.CC_STAT_AREA])

    islands = []
    island_id = 1
    for label in range(1, num_labels):
        if label == main_body_idx:
            continue

        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < min_island_area:
            continue

        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        cx, cy = centroids[label]

        islands.append({
            "id": island_id,
            "label": label,
            "bbox": [x, y, w, h],
            "centroid": [round(float(cx), 1), round(float(cy), 1)],
            "area": area
        })
        island_id += 1

    return {
        "island_count": len(islands),
        "islands": islands,
        "main_body_area": main_body_area,
        "total_components": num_labels - 1
    }


def generate_islands_overlay(
    image_path: str,
    output_overlay_path: str,
    islands_data: List[Dict[str, Any]] = None
) -> str:
    """
    Génère une image de diagnostic visuel en surbrillance rouge clignotante/fluo
    avec pastilles numérotées sur chaque pièce flottante.
    """
    if not os.path.exists(image_path):
        return image_path

    if islands_data is None:
        analysis = detect_floating_islands(image_path)
        islands_data = analysis["islands"]

    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return image_path

    h, w = img_bgr.shape[:2]
    overlay = img_bgr.copy()

    # Load binary for contours
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)
    num_labels, labels, _, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    for item in islands_data:
        lbl = item.get("label")
        bx, by, bw, bh = item["bbox"]
        idx = item["id"]

        # Red mask on island
        if lbl and lbl < num_labels:
            island_mask = (labels == lbl).astype(np.uint8) * 255
            # Draw semi-transparent bright red
            overlay[island_mask > 0] = [68, 68, 239]  # BGR for #EF4444

        # Red bounding rectangle
        cv2.rectangle(overlay, (bx - 3, by - 3), (bx + bw + 3, by + bh + 3), (68, 68, 239), 2)

        # Numbered circle badge
        badge_x = max(10, bx - 10)
        badge_y = max(10, by - 10)
        cv2.circle(overlay, (badge_x, badge_y), 12, (68, 68, 239), -1)
        cv2.putText(overlay, str(idx), (badge_x - 4, badge_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # Blend overlay with original (70% overlay, 30% original)
    blended = cv2.addWeighted(overlay, 0.75, img_bgr, 0.25, 0)

    # Add top banner
    banner_text = f"DIAGNOSTIC LASER : {len(islands_data)} ILOT(S) FLOTTANT(S) DETECTE(S)" if islands_data else "DIAGNOSTIC LASER : 100% CONNECTE (ZERO ILOT)"
    banner_color = (68, 68, 239) if islands_data else (16, 185, 129)
    cv2.rectangle(blended, (0, 0), (w, 35), banner_color, -1)
    cv2.putText(blended, banner_text, (20, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

    out_dir = os.path.dirname(output_overlay_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    cv2.imwrite(output_overlay_path, blended)
    return output_overlay_path


def auto_bridge_stencil(
    image_path: str,
    output_bridged_path: str,
    bridge_width: int = 5,
    min_island_area: int = 15
) -> Dict[str, Any]:
    """
    Algorithme de Pontage Automatique (Auto-Bridging) :
    Calcule le chemin euclidien le plus court entre chaque îlot flottant et le corps
    connecté principal, et trace des ponts de matière solides (3 à 6px) pour solidariser
    l'ensemble du pochoir laser.
    """
    if not os.path.exists(image_path):
        return {"bridges_added": 0, "output_path": image_path, "success": False}

    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        return {"bridges_added": 0, "output_path": image_path, "success": False}

    _, binary = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    if num_labels <= 2:
        # Already 0 or 1 component
        out_dir = os.path.dirname(output_bridged_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        cv2.imwrite(output_bridged_path, img_gray)
        return {"bridges_added": 0, "output_path": output_bridged_path, "success": True}

    areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
    main_body_idx = int(np.argmax(areas)) + 1

    # Main body mask (will grow as bridges are added)
    main_mask = (labels == main_body_idx).astype(np.uint8) * 255

    # Result image in grayscale (255 white, 0 black)
    result_img = img_gray.copy()
    bridges_count = 0

    # Sort islands by area descending
    island_labels = [lbl for lbl in range(1, num_labels) if lbl != main_body_idx and stats[lbl, cv2.CC_STAT_AREA] >= min_island_area]

    for island_lbl in island_labels:
        island_mask = (labels == island_lbl).astype(np.uint8) * 255

        # Find contours of island and main body
        island_contours, _ = cv2.findContours(island_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        main_contours, _ = cv2.findContours(main_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        if not island_contours or not main_contours:
            continue

        # Extract all contour coordinate points
        pts_island = np.vstack([c.reshape(-1, 2) for c in island_contours])
        pts_main = np.vstack([c.reshape(-1, 2) for c in main_contours])

        if len(pts_island) == 0 or len(pts_main) == 0:
            continue

        # Compute pairwise distance efficiently
        # Subsample if too many points (> 2000 points) for instant computation
        if len(pts_island) > 1000:
            step_i = max(1, len(pts_island) // 500)
            pts_island_sub = pts_island[::step_i]
        else:
            pts_island_sub = pts_island

        if len(pts_main) > 1000:
            step_m = max(1, len(pts_main) // 500)
            pts_main_sub = pts_main[::step_m]
        else:
            pts_main_sub = pts_main

        # Euclidean distance matrix
        diff = pts_island_sub[:, np.newaxis, :] - pts_main_sub[np.newaxis, :, :]
        dists_sq = np.sum(diff ** 2, axis=2)
        min_idx = np.unravel_index(np.argmin(dists_sq), dists_sq.shape)

        p1 = tuple(pts_island_sub[min_idx[0]])
        p2 = tuple(pts_main_sub[min_idx[1]])

        # Draw solid black bridging line (0 = black laser material)
        cv2.line(result_img, p1, p2, color=0, thickness=bridge_width, lineType=cv2.LINE_AA)

        # Update main mask with the bridged island and bridge line
        cv2.line(main_mask, p1, p2, color=255, thickness=bridge_width)
        main_mask = cv2.bitwise_or(main_mask, island_mask)

        bridges_count += 1

    out_dir = os.path.dirname(output_bridged_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cv2.imwrite(output_bridged_path, result_img)

    return {
        "bridges_added": bridges_count,
        "output_path": output_bridged_path,
        "success": True
    }

"""
SVG Connectivity Analyzer
Analyse un fichier SVG généré par Potrace pour détecter les îles flottantes
(sous-chemins disconnectés) qui provoqueraient des pièces détachées lors de
la découpe laser.
"""
import os
import re
from xml.etree import ElementTree as ET


def analyze_svg_connectivity(svg_path: str) -> dict:
    """
    Parse le fichier SVG et compte le nombre de <path> éléments racines.
    Un SVG correctement connecté pour la découpe laser devrait idéalement
    avoir 1 ou 2 paths maximum (design + contour éventuel).

    Args:
        svg_path: Chemin absolu vers le fichier SVG généré par Potrace.

    Returns:
        dict avec:
            - island_count: int — nombre de paths racines indépendants
            - severity: "ok" | "warning" | "critical"
            - message: str — description lisible
            - safe_to_cut: bool
    """
    if not os.path.exists(svg_path):
        return {
            "island_count": 0,
            "severity": "unknown",
            "message": "Fichier SVG introuvable.",
            "safe_to_cut": False,
        }

    try:
        # Nettoyer les namespaces SVG pour un parsing plus simple
        with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Supprimer les namespaces xmlns pour simplifier le parsing ElementTree
        content_clean = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', "", content)

        root = ET.fromstring(content_clean)

        # Compter tous les <path> directs enfants du SVG ou d'un <g> racine
        # Potrace génère typiquement <svg><g><path .../><path .../></g></svg>
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

        # Interpréter le résultat
        if path_count <= 1:
            severity = "ok"
            message = "Design entièrement connecté — prêt pour la découpe laser."
            safe_to_cut = True
        elif path_count <= 3:
            severity = "warning"
            message = (
                f"{path_count} sous-paths détectés. "
                "Vérifiez visuellement que toutes les pièces sont connectées."
            )
            safe_to_cut = True
        else:
            severity = "critical"
            message = (
                f"⚠️ {path_count} îles indépendantes détectées ! "
                "Des pièces pourraient tomber lors de la découpe laser. "
                "Inspectez et corrigez le SVG avant publication."
            )
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

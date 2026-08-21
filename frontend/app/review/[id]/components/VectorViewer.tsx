"use client";

import React, { memo } from "react";
import { Download, FileCode, FolderArchive, Layers, CheckCircle, Eye, AlertTriangle } from "lucide-react";

interface VectorViewerProps {
  creation: any;
  activeBundleIdx: number;
  setActiveBundleIdx: (idx: number) => void;
  assetUrl: (path: string) => string;
  islandOverlayUrl?: string | null;
  showIslandOverlay?: boolean;
  onToggleIslandOverlay?: () => void;
}

export const VectorViewer = memo(function VectorViewer({
  creation,
  activeBundleIdx,
  setActiveBundleIdx,
  assetUrl,
  islandOverlayUrl,
  showIslandOverlay,
  onToggleIslandOverlay,
}: VectorViewerProps) {
  const svgPaths = creation.svg_paths && creation.svg_paths.length > 0 ? creation.svg_paths : creation.svg_path ? [creation.svg_path] : [];
  const dxfPaths = creation.dxf_paths && creation.dxf_paths.length > 0 ? creation.dxf_paths : creation.dxf_path ? [creation.dxf_path] : [];
  const aiPaths = creation.ai_paths && creation.ai_paths.length > 0 ? creation.ai_paths : creation.ai_path ? [creation.ai_path] : [];
  const epsPaths = creation.eps_paths && creation.eps_paths.length > 0 ? creation.eps_paths : creation.eps_path ? [creation.eps_path] : [];
  const pdfPaths = creation.pdf_paths && creation.pdf_paths.length > 0 ? creation.pdf_paths : creation.pdf_path ? [creation.pdf_path] : [];
  const pngPaths = creation.png_paths && creation.png_paths.length > 0 ? creation.png_paths : creation.upscale_png_path ? [creation.upscale_png_path] : [];

  const currentSvg = svgPaths[activeBundleIdx] || svgPaths[0];
  const currentDxf = dxfPaths[activeBundleIdx] || dxfPaths[0];
  const currentAi = aiPaths[activeBundleIdx] || aiPaths[0];
  const currentEps = epsPaths[activeBundleIdx] || epsPaths[0];
  const currentPdf = pdfPaths[activeBundleIdx] || pdfPaths[0];
  const currentPng = pngPaths[activeBundleIdx] || pngPaths[0];

  const hasMultipleElements = svgPaths.length > 1;

  const downloadFormats = [
    { label: "SVG", sub: "Vecteur Découpe Laser / Cricut", path: currentSvg, color: "text-indigo-400 border-indigo-500/40 bg-indigo-500/10" },
    { label: "DXF", sub: "AutoCAD & Silhouette Studio", path: currentDxf, color: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
    { label: "AI", sub: "Adobe Illustrator Vectoriel", path: currentAi, color: "text-amber-400 border-amber-500/40 bg-amber-500/10" },
    { label: "EPS", sub: "Traceurs PostScript Pro", path: currentEps, color: "text-pink-400 border-pink-500/40 bg-pink-500/10" },
    { label: "PDF", sub: "Document Vectoriel 300 DPI", path: currentPdf, color: "text-rose-400 border-rose-500/40 bg-rose-500/10" },
    { label: "PNG", sub: "Clipart Transparent 300 DPI", path: currentPng, color: "text-cyan-400 border-cyan-500/40 bg-cyan-500/10" },
  ];

  return (
    <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-6">
      {/* Header & Sub-element Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <FileCode className="h-5 w-5 text-indigo-400" />
            Fichiers Vectoriels & CAO
          </h3>
          <p className="text-xs text-slate-400">
            Fichiers prêts pour machines de découpe laser (LightBurn, Glowforge, xTool, Cricut, CNC)
          </p>
        </div>

        {/* View Mode Toggle: SVG vs Diagnostic Overlay */}
        <div className="flex items-center gap-2">
          {onToggleIslandOverlay && (
            <button
              type="button"
              onClick={onToggleIslandOverlay}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                showIslandOverlay
                  ? "bg-rose-600 text-white shadow"
                  : "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
              }`}
            >
              <Eye className="h-3.5 w-3.5 text-rose-400" />
              <span>{showIslandOverlay ? "Mode Standard SVG" : "Carte Îlots Flottants"}</span>
            </button>
          )}

          {/* Multi-element tabs if pack bundle */}
          {hasMultipleElements && (
            <div className="flex items-center gap-1.5 bg-slate-800 p-1 rounded-xl border border-slate-700">
              <span className="text-[11px] font-bold text-slate-400 px-2 flex items-center gap-1">
                <Layers className="h-3 w-3" /> Pack ({svgPaths.length}) :
              </span>
              {svgPaths.map((_: string, idx: number) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setActiveBundleIdx(idx)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                    activeBundleIdx === idx
                      ? "bg-indigo-600 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  #{idx + 1}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* SVG Vector or Island Diagnostic Preview Frame */}
      <div className="relative w-full aspect-square max-h-[400px] bg-white rounded-xl overflow-hidden border border-slate-700/80 flex items-center justify-center p-6 shadow-inner">
        {showIslandOverlay && islandOverlayUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`${assetUrl(islandOverlayUrl)}?t=${new Date().getTime()}`}
            alt="Island Diagnostic Overlay"
            className="w-full h-full object-contain select-none"
          />
        ) : currentSvg ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`${assetUrl(currentSvg)}?t=${new Date().getTime()}`}
            alt="Vector SVG Preview"
            className="w-full h-full object-contain select-none"
          />
        ) : (
          <div className="text-slate-400 text-sm">Aucun fichier SVG généré</div>
        )}
      </div>

      {/* Formats Download Grid */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Téléchargement individuel des formats
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {downloadFormats.map((fmt, i) => (
            <a
              key={i}
              href={fmt.path ? assetUrl(fmt.path) : "#"}
              download
              target="_blank"
              rel="noreferrer"
              className={`p-3.5 rounded-xl border flex items-center justify-between transition group ${
                fmt.path
                  ? `${fmt.color} hover:brightness-110 cursor-pointer`
                  : "opacity-40 border-slate-800 bg-slate-900 cursor-not-allowed"
              }`}
            >
              <div>
                <div className="font-bold text-sm text-slate-100 flex items-center gap-1.5">
                  <span>{fmt.label}</span>
                  {fmt.path && <CheckCircle className="h-3 w-3 text-emerald-400" />}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">{fmt.sub}</div>
              </div>
              <Download className="h-4 w-4 opacity-70 group-hover:opacity-100 transition" />
            </a>
          ))}
        </div>
      </div>

      {/* Client Deliverable ZIP Bundle Card */}
      {creation.zip_path && (
        <div className="p-4 bg-indigo-950/40 rounded-xl border border-indigo-500/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-md">
              <FolderArchive className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-100">Archive ZIP Client Prête</div>
              <div className="text-xs text-indigo-300/80">
                Contient tous les formats (SVG, DXF, AI, EPS, PDF, PNG) empaquetés pour l'acheteur Etsy
              </div>
            </div>
          </div>
          <a
            href={assetUrl(creation.zip_path)}
            download
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-lg transition flex items-center gap-1.5 shadow-md cursor-pointer"
          >
            <Download className="h-4 w-4" />
            Télécharger ZIP
          </a>
        </div>
      )}
    </div>
  );
});

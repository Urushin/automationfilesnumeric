"use client";

import React, { memo } from "react";
import {
  Sparkles,
  Loader2,
  Sliders,
  CheckCircle2,
  Square,
  CheckSquare,
  Shield,
  Eye,
} from "lucide-react";

interface MediaGalleryProps {
  creation: any;
  availableImages: string[];
  selectedImages: string[];
  toggleImageSelection: (path: string) => void;
  setAsPrimaryImage: (path: string) => void;
  previewTab: "mockup" | "commercial" | "transparent_png" | "source";
  setPreviewTab: (tab: "mockup" | "commercial" | "transparent_png" | "source") => void;
  activeMockupStyleIdx: number;
  setActiveMockupStyleIdx: (idx: number) => void;
  activeCommercialIdx: number;
  setActiveCommercialIdx: (idx: number) => void;
  onRegenerateMockup: () => void;
  regeneratingMockup: boolean;
  onOpenRetouch: (url: string) => void;
  assetUrl: (path: string) => string;
}

export const MediaGallery = memo(function MediaGallery({
  creation,
  availableImages,
  selectedImages,
  toggleImageSelection,
  setAsPrimaryImage,
  previewTab,
  setPreviewTab,
  activeMockupStyleIdx,
  setActiveMockupStyleIdx,
  activeCommercialIdx,
  setActiveCommercialIdx,
  onRegenerateMockup,
  regeneratingMockup,
  onOpenRetouch,
  assetUrl,
}: MediaGalleryProps) {
  // Determine current active preview image URL
  let currentPreviewUrl: string | null = null;
  if (previewTab === "mockup") {
    if (creation.mockup_paths && creation.mockup_paths.length > 0) {
      currentPreviewUrl = creation.mockup_paths[activeMockupStyleIdx] || creation.mockup_paths[0];
    } else {
      currentPreviewUrl = creation.mockup_path;
    }
  } else if (previewTab === "commercial") {
    const commPaths =
      creation.commercial_mockup_paths && creation.commercial_mockup_paths.length > 0
        ? creation.commercial_mockup_paths
        : creation.real_mockup_paths && creation.real_mockup_paths.length > 0
        ? creation.real_mockup_paths
        : creation.real_mockup_path
        ? [creation.real_mockup_path]
        : [];
    currentPreviewUrl = commPaths[activeCommercialIdx] || commPaths[0] || null;
  } else if (previewTab === "transparent_png") {
    currentPreviewUrl =
      creation.upscale_png_path ||
      (creation.png_paths && creation.png_paths.length > 0 ? creation.png_paths[0] : null);
  } else {
    currentPreviewUrl = creation.source_png_path;
  }

  const mockupLabels = ["1. Lifestyle", "2. Zoom Matière", "3. Formats Inclus", "4. Guide Technique"];

  return (
    <div className="space-y-6">
      {/* ── Main Preview Frame ────────────────────────────────────────────── */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          {/* Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
            {(creation.mockup_path || (creation.mockup_paths && creation.mockup_paths.length > 0)) && (
              <button
                type="button"
                onClick={() => setPreviewTab("mockup")}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                  previewTab === "mockup"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>Pack Etsy (4 Visuels)</span>
              </button>
            )}

            {creation.upscale_png_path && (
              <button
                type="button"
                onClick={() => setPreviewTab("transparent_png")}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  previewTab === "transparent_png"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                PNG Transparent
              </button>
            )}

            {creation.source_png_path && (
              <button
                type="button"
                onClick={() => setPreviewTab("source")}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  previewTab === "source"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Source
              </button>
            )}
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            {creation.source_png_path && (
              <button
                type="button"
                onClick={() => onOpenRetouch(creation.source_png_path)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-lg border border-slate-700 transition flex items-center gap-1.5"
              >
                <Sliders className="h-3.5 w-3.5 text-indigo-400" />
                Retoucher
              </button>
            )}
            <button
              type="button"
              onClick={onRegenerateMockup}
              disabled={regeneratingMockup}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition flex items-center gap-1.5 disabled:opacity-50"
            >
              {regeneratingMockup ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              {regeneratingMockup ? "Génération..." : "Régénérer Mockups"}
            </button>
          </div>
        </div>

        {/* Sub-selector for multi-mockups */}
        {previewTab === "mockup" && creation.mockup_paths && creation.mockup_paths.length > 1 && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {creation.mockup_paths.map((_: string, i: number) => (
              <button
                key={i}
                type="button"
                onClick={() => setActiveMockupStyleIdx(i)}
                className={`px-3 py-1 text-xs font-bold rounded-lg border transition ${
                  activeMockupStyleIdx === i
                    ? "bg-indigo-600/30 text-indigo-300 border-indigo-500"
                    : "bg-slate-800/60 text-slate-400 border-slate-700 hover:text-slate-200"
                }`}
              >
                {mockupLabels[i] || `Visuel #${i + 1}`}
              </button>
            ))}
          </div>
        )}

        {/* Large Canvas / Image Viewer */}
        <div className="relative w-full aspect-square max-h-[500px] bg-slate-950 rounded-xl overflow-hidden border border-slate-800/80 flex items-center justify-center">
          {currentPreviewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`${assetUrl(currentPreviewUrl)}?t=${new Date().getTime()}`}
              alt="Preview"
              className="w-full h-full object-contain select-none"
            />
          ) : (
            <div className="text-slate-500 text-sm flex items-center gap-2">
              <Eye className="h-4 w-4" /> Aucun aperçu disponible
            </div>
          )}
        </div>
      </div>

      {/* ── Etsy Photos Gallery (10 Slots) ────────────────────────────────── */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>Photos Publiées sur Etsy ({selectedImages.length}/10)</span>
            </h4>
            <p className="text-xs text-slate-400">
              Cochez les images à envoyer sur la fiche produit Etsy. La 1ère sera l'image principale.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {availableImages.map((imgPath, idx) => {
            const isSelected = selectedImages.includes(imgPath);
            const isPrimary = selectedImages[0] === imgPath;
            return (
              <div
                key={idx}
                className={`relative group rounded-xl overflow-hidden border transition aspect-square bg-slate-950 ${
                  isPrimary
                    ? "border-amber-400 ring-2 ring-amber-400/20"
                    : isSelected
                    ? "border-indigo-500"
                    : "border-slate-800 opacity-60 hover:opacity-100"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={assetUrl(imgPath)}
                  alt={`Mockup ${idx + 1}`}
                  className="w-full h-full object-cover"
                />

                {/* Primary Tag */}
                {isPrimary && (
                  <div className="absolute top-2 left-2 bg-amber-500 text-slate-950 font-black text-[10px] px-2 py-0.5 rounded-md shadow-md z-10">
                    ★ Principale
                  </div>
                )}

                {/* Selection Toggle Button */}
                <button
                  type="button"
                  onClick={() => toggleImageSelection(imgPath)}
                  className="absolute top-2 right-2 p-1 bg-slate-900/80 rounded-md text-white z-10 hover:bg-slate-900 transition"
                >
                  {isSelected ? (
                    <CheckSquare className="h-4 w-4 text-indigo-400" />
                  ) : (
                    <Square className="h-4 w-4 text-slate-400" />
                  )}
                </button>

                {/* Set as primary hover action */}
                {isSelected && !isPrimary && (
                  <button
                    type="button"
                    onClick={() => setAsPrimaryImage(imgPath)}
                    className="absolute inset-x-2 bottom-2 py-1 bg-slate-900/90 text-amber-300 font-bold text-[10px] rounded-lg opacity-0 group-hover:opacity-100 transition z-10 text-center"
                  >
                    Définir en principale
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});

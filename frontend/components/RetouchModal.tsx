"use client";

import React, { useState, useRef } from "react";
import CanvasEditor from "./CanvasEditor";
import { X, Sparkles, AlertCircle, CheckCircle, RefreshCw } from "lucide-react";
import { apiUrl } from "@/lib/api";

interface RetouchModalProps {
  isOpen: boolean;
  creationId: number;
  imageUrl: string;
  assetPath?: string;
  assetType?: string;
  onClose: () => void;
  onValidate: (updatedCreation?: any) => void;
}

export default function RetouchModal({
  isOpen,
  creationId,
  imageUrl,
  assetPath,
  assetType,
  onClose,
  onValidate,
}: RetouchModalProps) {
  const [cacheBust, setCacheBust] = useState(Date.now());
  const [hasEdited, setHasEdited] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const editorRef = useRef<any>(null);

  if (!isOpen) return null;

  const handleSavedImage = (newUrl: string) => {
    setCacheBust(Date.now());
    setHasEdited(true);
  };

  const handleValidateWorkspace = async () => {
    try {
      setIsSaving(true);
      // 1. Force the file to overwrite on the disk and wait for 200 OK
      const canvasData = await editorRef.current?.getMergedCanvasDataUrl();
      if (!canvasData) {
        alert("Impossible de récupérer l'image.");
        setIsSaving(false);
        return;
      }

      const res = await fetch(apiUrl("/api/pipeline/save-workspace"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          creation_id: creationId,
          canvasData,
          asset_path: assetPath,
          asset_type: assetType,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Le fichier n'a pas pu être enregistré.");
      }

      // 2. Immediate UI Release
      onValidate();
    } catch (error) {
      console.error("Validation failed to block:", error);
      alert("Erreur lors de l'enregistrement final : " + (error as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col my-8">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-950/30">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Sparkles className="text-indigo-400 h-5 w-5 animate-pulse" />
              <span>Contrôle Qualité & Retouches</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Le motif est-il correct ou souhaitez-vous le retoucher avant de continuer ?
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white bg-slate-800/50 hover:bg-slate-800 rounded-xl transition cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content - strictly the canvas and retoucher */}
        <div className="p-6 overflow-y-auto flex-1 max-h-[70vh]">
          <CanvasEditor
            ref={editorRef}
            imageUrl={`${imageUrl}?t=${cacheBust}`}
            creationId={creationId}
            onSaved={handleSavedImage}
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-800 bg-slate-950/30">
          <div className="flex items-center gap-2 text-xs">
            {hasEdited ? (
              <span className="text-indigo-400 flex items-center gap-1.5 font-semibold">
                <CheckCircle className="h-4 w-4" /> Modifications enregistrées localement
              </span>
            ) : (
              <span className="text-slate-500 flex items-center gap-1.5">
                <AlertCircle className="h-4 w-4" /> Aucun changement effectué
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              disabled={isSaving}
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 hover:text-white font-semibold rounded-xl text-xs transition cursor-pointer"
            >
              Annuler
            </button>
            <button
              onClick={handleValidateWorkspace}
              disabled={isSaving}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition flex items-center gap-2 shadow-lg shadow-indigo-500/20 cursor-pointer"
            >
              {isSaving && <RefreshCw className="h-3 w-3 animate-spin" />}
              <span>Valider & Confirmer</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

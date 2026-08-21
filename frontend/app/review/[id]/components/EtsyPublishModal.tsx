"use client";

import React, { memo } from "react";
import { ShoppingBag, Loader2, CheckCircle2, AlertCircle, ExternalLink, X } from "lucide-react";

interface EtsyPublishModalProps {
  isOpen: boolean;
  onClose: () => void;
  creation: any;
  onPublish: () => void;
  publishing: boolean;
  publishError: string | null;
  publishSuccess: { listing_id: string; url?: string } | null;
  price: number;
  quantity: number;
  publishStatus: "draft" | "active";
  setPublishStatus: (status: "draft" | "active") => void;
  selectedImagesCount: number;
}

export const EtsyPublishModal = memo(function EtsyPublishModal({
  isOpen,
  onClose,
  creation,
  onPublish,
  publishing,
  publishError,
  publishSuccess,
  price,
  quantity,
  publishStatus,
  setPublishStatus,
  selectedImagesCount,
}: EtsyPublishModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6 relative">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={publishing}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
            <ShoppingBag className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Publication sur Etsy</h3>
            <p className="text-xs text-slate-400">Boutique : digitalfilesbymop</p>
          </div>
        </div>

        {/* Success State */}
        {publishSuccess ? (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl space-y-3">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <CheckCircle2 className="h-5 w-5" />
              <span>Fiche produit créée avec succès sur Etsy !</span>
            </div>
            <p className="text-xs text-slate-300">
              ID de la fiche : <span className="font-mono text-emerald-300 font-bold">{publishSuccess.listing_id}</span>
            </p>
            {publishSuccess.url && (
              <a
                href={publishSuccess.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition"
              >
                <span>Voir sur Etsy</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        ) : (
          /* Publish Configuration Form */
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1 block">Statut initial</label>
                <select
                  value={publishStatus}
                  onChange={(e) => setPublishStatus(e.target.value as "draft" | "active")}
                  className="w-full p-2.5 bg-slate-800 text-white rounded-xl border border-slate-700 outline-none text-xs focus:border-indigo-500 font-bold"
                >
                  <option value="draft">Brouillon (Draft) - Recommandé</option>
                  <option value="active">Actif (Active) - En ligne direct</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1 block">Prix de vente (€)</label>
                <div className="p-2.5 bg-slate-800 text-slate-200 rounded-xl border border-slate-700 text-xs font-mono font-bold">
                  {price.toFixed(2)} €
                </div>
              </div>
            </div>

            <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60 text-xs text-slate-300 space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Photos sélectionnées :</span>
                <span className="font-bold text-white">{selectedImagesCount} / 10</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Fichier ZIP numérique :</span>
                <span className="font-bold text-emerald-400">Prêt (Attaché auto)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Tags SEO :</span>
                <span className="font-bold text-white">13 tags validés</span>
              </div>
            </div>

            {publishError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{publishError}</span>
              </div>
            )}

            <button
              type="button"
              onClick={onPublish}
              disabled={publishing}
              className="w-full py-3.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-bold text-sm rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-amber-600/20"
            >
              {publishing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Publication en cours sur Etsy...</span>
                </>
              ) : (
                <>
                  <ShoppingBag className="h-4 w-4" />
                  <span>Confirmer et Publier sur Etsy</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
});

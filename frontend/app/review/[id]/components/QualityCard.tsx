"use client";

import React, { memo } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Zap,
  RefreshCw,
  Eye,
  Wand2,
  Loader2,
} from "lucide-react";

interface QualityCardProps {
  connectivityWarnings: number;
  complianceWarnings: any[];
  onRerunCompliance?: () => void;
  runningCompliance?: boolean;
  onToggleIslandOverlay?: () => void;
  showIslandOverlay?: boolean;
  onAutoBridge?: () => void;
  autoBridging?: boolean;
}

export const QualityCard = memo(function QualityCard({
  connectivityWarnings,
  complianceWarnings,
  onRerunCompliance,
  runningCompliance,
  onToggleIslandOverlay,
  showIslandOverlay,
  onAutoBridge,
  autoBridging,
}: QualityCardProps) {
  const isCutReady = connectivityWarnings === 0;

  return (
    <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-indigo-400" />
          Contrôle Qualité & Découpe Laser
        </h3>
        {onRerunCompliance && (
          <button
            type="button"
            onClick={onRerunCompliance}
            disabled={runningCompliance}
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className={`h-3 w-3 ${runningCompliance ? "animate-spin" : ""}`} />
            Re-vérifier
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Laser Cutability Status */}
        <div
          className={`p-4 rounded-xl border flex flex-col justify-between gap-3 ${
            isCutReady
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-amber-500/10 border-amber-500/30 text-amber-300"
          }`}
        >
          <div className="flex items-start gap-3">
            {isCutReady ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="font-bold text-sm text-slate-100">
                {isCutReady ? "Prêt pour Découpe Laser (100% Connecté)" : "Îlots flottants détectés"}
              </div>
              <div className="text-xs text-slate-400 mt-1 leading-relaxed">
                {isCutReady
                  ? "Tous les chemins noirs sont reliés d'un seul tenant. Aucune pièce flottante ne tombera lors de la découpe laser."
                  : `${connectivityWarnings} îlot(s) non connecté(s) détecté(s). Des pièces détachées risquent de tomber lors de la découpe.`}
              </div>
            </div>
          </div>

          {/* Quick Actions for Islands */}
          {!isCutReady && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-amber-500/20">
              {onToggleIslandOverlay && (
                <button
                  type="button"
                  onClick={onToggleIslandOverlay}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                    showIslandOverlay
                      ? "bg-rose-600 text-white shadow"
                      : "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                  }`}
                >
                  <Eye className="h-3.5 w-3.5 text-rose-400" />
                  <span>{showIslandOverlay ? "Masquer la carte" : "👁️ Carte des îlots"}</span>
                </button>
              )}

              {onAutoBridge && (
                <button
                  type="button"
                  onClick={onAutoBridge}
                  disabled={autoBridging}
                  className="px-3 py-1.5 bg-gradient-to-r from-amber-600 to-indigo-600 hover:from-amber-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition flex items-center gap-1.5 shadow-md cursor-pointer"
                >
                  {autoBridging ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Wand2 className="h-3.5 w-3.5" />
                  )}
                  <span>{autoBridging ? "Pontage..." : "⚡ Auto-Bridge (1-Clic)"}</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Node Optimization & Smoothness */}
        <div className="p-4 rounded-xl border bg-slate-800/40 border-slate-700/60 flex items-start gap-3">
          <Zap className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-sm text-slate-100">Lissage de Courbes & Nœuds (Douglas-Peucker)</div>
            <div className="text-xs text-slate-400 mt-1 leading-relaxed">
              Optimisation active : 60-80% de points superflus éliminés pour une découpe fluide et rapide sans saccades laser.
            </div>
          </div>
        </div>
      </div>

      {/* Trademark / Compliance Check Warnings */}
      {complianceWarnings && complianceWarnings.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/30 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-rose-400">
            <AlertTriangle className="h-4 w-4" />
            <span>Mots-clés sensibles ou marques déposées détectées</span>
          </div>
          <div className="space-y-1">
            {complianceWarnings.map((warn, i) => (
              <div key={i} className="text-xs text-rose-200/90 pl-6">
                • {warn.message || warn}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

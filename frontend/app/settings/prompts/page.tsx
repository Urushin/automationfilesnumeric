"use client";

import React, { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api";
import { Copy, Check, ChevronLeft, Sparkles, Terminal, BookOpen } from "lucide-react";
import Link from "next/link";

interface PromptItem {
  id: string;
  title: string;
  description: string;
  prompt: string;
}

const categories = [
  { id: "all", label: "Tous" },
  { id: "seo_content", label: "SEO & Contenu" },
  { id: "stencils", label: "Pochoirs & Tracé" },
  { id: "mockups", label: "Mises en situation" },
  { id: "legacy", label: "Ancien Moteur" }
];

const promptCategoryMap: Record<string, string> = {
  seo: "seo_content",
  trend_scraping: "seo_content",
  
  stencil_single: "stencils",
  stencil_multiple: "stencils",
  stencil_framed_filigree: "stencils",
  vision_description: "stencils",
  imagen3_negative_suffix: "stencils",
  inpainting: "stencils",
  
  image_generation: "mockups",
  mockup_banana: "mockups",
  mockup_dalle3: "mockups",
  mockup_degraded: "mockups",
  
  legacy_framed_filigree: "legacy",
  legacy_classic: "legacy",
  legacy_image_to_image: "legacy",
  legacy_grad_cap: "legacy"
};

const keyMap: Record<string, string> = {
  seo: "prompt_seo",
  image_generation: "prompt_image_generation",
  inpainting: "prompt_inpainting",
  trend_scraping: "prompt_trend_scraping",
  stencil_single: "prompt_stencil_single",
  stencil_multiple: "prompt_stencil_multiple",
  stencil_framed_filigree: "prompt_stencil_framed_filigree",
  vision_description: "prompt_vision_description",
  imagen3_negative_suffix: "prompt_imagen3_negative_suffix",
  legacy_framed_filigree: "prompt_legacy_framed_filigree",
  legacy_classic: "prompt_legacy_classic",
  legacy_image_to_image: "prompt_legacy_image_to_image",
  legacy_grad_cap: "prompt_legacy_grad_cap",
  mockup_banana: "prompt_mockup_banana",
  mockup_dalle3: "prompt_mockup_dalle3",
  mockup_degraded: "prompt_mockup_degraded"
};

export default function PromptsDashboard() {
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [localPrompts, setLocalPrompts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("all");

  useEffect(() => {
    fetch(apiUrl("/api/settings/prompts"))
      .then((res) => res.json())
      .then((data) => {
        setPrompts(data);
        const initialEdits: Record<string, string> = {};
        data.forEach((p: PromptItem) => {
          initialEdits[p.id] = p.prompt;
        });
        setLocalPrompts(initialEdits);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch prompts:", err);
        setLoading(false);
      });
  }, []);

  const handleCopy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  const handleSave = async (id: string) => {
    setSavingId(id);
    setNotification(null);
    try {
      const payload: Record<string, string> = {};
      const backendKey = keyMap[id];
      if (backendKey) {
        payload[backendKey] = localPrompts[id];
      } else {
        throw new Error("Clé de prompt inconnue");
      }

      const res = await fetch(apiUrl("/api/settings/prompts"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Erreur de sauvegarde");
      
      setPrompts(prev => prev.map(p => p.id === id ? { ...p, prompt: localPrompts[id] } : p));
      setNotification({ type: "success", message: "Prompt système mis à jour avec succès !" });
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "La sauvegarde a échoué." });
    } finally {
      setSavingId(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12 flex flex-col items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mb-4"></div>
        <p className="text-slate-400 font-medium">Chargement des prompts système...</p>
      </div>
    );
  }

  const filteredPrompts = prompts.filter(p => selectedCategory === "all" || promptCategoryMap[p.id] === selectedCategory);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Navigation Header */}
      <div className="mb-8 flex items-center justify-between">
        <Link
          href="/settings"
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors duration-200 group"
        >
          <ChevronLeft className="h-4 w-4 transform group-hover:-translate-x-0.5 transition-transform" />
          Retour aux paramètres
        </Link>
        <span className="text-xs font-mono text-indigo-400 bg-indigo-950/40 px-3 py-1 rounded-full border border-indigo-900/50">
          Système Prompts v2.0
        </span>
      </div>

      <div className="mb-6 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-extrabold text-white mb-3 tracking-tight flex items-center gap-3 bg-gradient-to-r from-white via-slate-100 to-indigo-200 bg-clip-text text-transparent">
            <Terminal className="text-indigo-400 h-9 w-9" />
            Configuration des Prompts
          </h1>
          <p className="text-slate-400 max-w-2xl text-base leading-relaxed">
            Visualisez et modifiez l'intégralité des invites système (prompts) envoyées aux intelligences artificielles (SEO, génération de pochoirs, mises en situation et modèles hérités).
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-8 border-b border-slate-800/80 pb-4">
        {categories.map((cat) => {
          const count = cat.id === "all" 
            ? prompts.length 
            : prompts.filter(p => promptCategoryMap[p.id] === cat.id).length;

          return (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer border ${
                selectedCategory === cat.id
                  ? "bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-500/20"
                  : "bg-slate-900/40 border-slate-800/60 text-slate-400 hover:text-slate-200 hover:border-slate-700/60"
              }`}
            >
              {cat.label} ({count})
            </button>
          );
        })}
      </div>

      {notification && (
        <div className={`p-4 rounded-xl border mb-6 text-sm ${
          notification.type === "success" 
            ? "bg-emerald-950/40 border-emerald-500/20 text-emerald-300"
            : "bg-rose-950/40 border-rose-500/20 text-rose-300"
        }`}>
          {notification.message}
        </div>
      )}

      {filteredPrompts.length === 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12 text-center">
          <BookOpen className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">Aucun prompt configuré dans cette catégorie.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8">
          {filteredPrompts.map((item) => {
            const hasChanges = localPrompts[item.id] !== item.prompt;
            return (
              <div
                key={item.id}
                className="group bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 hover:border-slate-700/80 rounded-2xl p-6 transition-all duration-300 shadow-xl hover:shadow-2xl hover:shadow-indigo-500/5 flex flex-col gap-4 relative overflow-hidden"
              >
                {/* Decorative side border */}
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-500 to-purple-600 opacity-50 group-hover:opacity-100 transition-opacity" />

                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-900/50">
                        {categories.find(c => c.id === promptCategoryMap[item.id])?.label || "Système"}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        ID: {item.id}
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
                      <Sparkles className="h-4.5 w-4.5 text-indigo-400 inline" />
                      {item.title}
                    </h2>
                    <p className="text-sm text-slate-400 max-w-4xl leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  <button
                    onClick={() => handleCopy(item.id, localPrompts[item.id] || "")}
                    className={`self-start md:self-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 shadow-sm cursor-pointer ${
                      copiedId === item.id
                        ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                        : "bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700"
                    }`}
                  >
                    {copiedId === item.id ? (
                      <>
                        <Check className="h-4 w-4" />
                        Copié !
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        Copier
                      </>
                    )}
                  </button>
                </div>

                {/* Prompt Text Edit Area */}
                <div className="flex flex-col gap-2">
                  <textarea
                    value={localPrompts[item.id] ?? ""}
                    onChange={(e) => setLocalPrompts(prev => ({ ...prev, [item.id]: e.target.value }))}
                    rows={6}
                    className="w-full text-xs bg-slate-950/80 border border-slate-800 rounded-xl p-4 font-mono text-slate-300 leading-relaxed focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                  
                  <div className="flex justify-end gap-3 mt-1">
                    {hasChanges && (
                      <button
                        onClick={() => setLocalPrompts(prev => ({ ...prev, [item.id]: item.prompt }))}
                        className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold transition cursor-pointer"
                      >
                        Réinitialiser
                      </button>
                    )}
                    <button
                      onClick={() => handleSave(item.id)}
                      disabled={savingId === item.id || !hasChanges}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl text-xs transition cursor-pointer"
                    >
                      {savingId === item.id ? "Sauvegarde..." : "Enregistrer"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

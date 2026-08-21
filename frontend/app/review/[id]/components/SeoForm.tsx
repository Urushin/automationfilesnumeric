"use client";

import React, { memo } from "react";
import { Copy, Check, Languages, Tag as TagIcon, FileText } from "lucide-react";

interface SeoFormProps {
  theme: string;
  titleFr: string;
  titleEn: string;
  descriptionFr: string;
  descriptionEn: string;
  tagsFr: string;
  tagsEn: string;
  price: number;
  quantity: number;
  seoLangTab: "fr" | "en";
  setSeoLangTab: (tab: "fr" | "en") => void;
  onFieldChange: (field: string, value: any) => void;
  onTranslate: (field: "title" | "description" | "tags", fromText: string) => void;
  translatingField: string | null;
}

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
      <span className="font-semibold">{label}</span>
      <button
        type="button"
        onClick={handleCopy}
        className="flex items-center gap-1 hover:text-indigo-400 transition"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
        <span>{copied ? "Copié" : "Copier"}</span>
      </button>
    </div>
  );
}

export const SeoForm = memo(function SeoForm({
  theme,
  titleFr,
  titleEn,
  descriptionFr,
  descriptionEn,
  tagsFr,
  tagsEn,
  price,
  quantity,
  seoLangTab,
  setSeoLangTab,
  onFieldChange,
  onTranslate,
  translatingField,
}: SeoFormProps) {
  const currentTitle = seoLangTab === "fr" ? titleFr : titleEn;
  const currentDesc = seoLangTab === "fr" ? descriptionFr : descriptionEn;
  const currentTags = seoLangTab === "fr" ? tagsFr : tagsEn;

  const tagList = (currentTags || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  return (
    <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-6">
      {/* Header with Bilingual Tab Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-400" />
            Rédaction & SEO E-Commerce
          </h3>
          <p className="text-xs text-slate-400">Titres, descriptions et tags optimisés pour la conversion</p>
        </div>

        <div className="flex items-center bg-slate-800 p-1 rounded-xl border border-slate-700">
          <button
            type="button"
            onClick={() => setSeoLangTab("fr")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              seoLangTab === "fr" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            🇫🇷 Français
          </button>
          <button
            type="button"
            onClick={() => setSeoLangTab("en")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              seoLangTab === "en" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            🇬🇧 Anglais
          </button>
        </div>
      </div>

      {/* Title Field */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <CopyField
            label={seoLangTab === "fr" ? "Titre Etsy (Français)" : "Titre Etsy (Anglais)"}
            value={currentTitle || ""}
          />
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                (currentTitle || "").length > 140
                  ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                  : "bg-slate-800 text-slate-400"
              }`}
            >
              {(currentTitle || "").length} / 140 car.
            </span>
            <button
              type="button"
              onClick={() => onTranslate("title", seoLangTab === "fr" ? titleFr : titleEn)}
              disabled={translatingField === "title"}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 underline"
            >
              <Languages className="h-3 w-3" />
              {translatingField === "title" ? "Traduction..." : "Traduire"}
            </button>
          </div>
        </div>
        <input
          type="text"
          value={currentTitle || ""}
          onChange={(e) =>
            onFieldChange(seoLangTab === "fr" ? "title_fr" : "title_en", e.target.value)
          }
          placeholder="Titre accrocheur avec mots-clés séparés par des barres..."
          className="w-full p-3 bg-slate-800 text-white rounded-xl border border-slate-700 focus:border-indigo-500 outline-none text-sm transition"
        />
      </div>

      {/* Description Field */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <CopyField
            label={seoLangTab === "fr" ? "Description complète (Français)" : "Description complète (Anglais)"}
            value={currentDesc || ""}
          />
          <button
            type="button"
            onClick={() => onTranslate("description", seoLangTab === "fr" ? descriptionFr : descriptionEn)}
            disabled={translatingField === "description"}
            className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 underline"
          >
            <Languages className="h-3 w-3" />
            {translatingField === "description" ? "Traduction..." : "Traduire"}
          </button>
        </div>
        <textarea
          rows={7}
          value={currentDesc || ""}
          onChange={(e) =>
            onFieldChange(seoLangTab === "fr" ? "description" : "description_en", e.target.value)
          }
          placeholder="Description détaillée : formats inclus, instructions machines, licence commerciale..."
          className="w-full p-3 bg-slate-800 text-white rounded-xl border border-slate-700 focus:border-indigo-500 outline-none text-sm transition font-mono text-xs leading-relaxed"
        />
      </div>

      {/* Tags Field with Pills */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <CopyField
            label={seoLangTab === "fr" ? "13 Tags Etsy (Français)" : "13 Tags Etsy (Anglais)"}
            value={currentTags || ""}
          />
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                tagList.length === 13
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : tagList.length > 13
                  ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                  : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              }`}
            >
              {tagList.length} / 13 tags
            </span>
            <button
              type="button"
              onClick={() => onTranslate("tags", seoLangTab === "fr" ? tagsFr : tagsEn)}
              disabled={translatingField === "tags"}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 underline"
            >
              <Languages className="h-3 w-3" />
              {translatingField === "tags" ? "Traduction..." : "Traduire"}
            </button>
          </div>
        </div>

        <input
          type="text"
          value={currentTags || ""}
          onChange={(e) =>
            onFieldChange(seoLangTab === "fr" ? "tags_fr" : "tags_en", e.target.value)
          }
          placeholder="tag1, tag2, tag3... (séparés par des virgules)"
          className="w-full p-3 bg-slate-800 text-white rounded-xl border border-slate-700 focus:border-indigo-500 outline-none text-xs transition font-mono"
        />

        {/* Rendered Tag Badges */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {tagList.map((tag, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 text-[11px]"
            >
              <TagIcon className="h-3 w-3 text-indigo-400" />
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Pricing & Stock Settings */}
      <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800">
        <div>
          <label className="text-xs text-slate-400 font-semibold mb-1 block">Prix de vente (€)</label>
          <input
            type="number"
            step="0.10"
            min="0.5"
            value={price ?? 3.0}
            onChange={(e) => onFieldChange("price", parseFloat(e.target.value) || 3.0)}
            className="w-full p-2.5 bg-slate-800 text-white rounded-xl border border-slate-700 outline-none text-sm font-bold"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400 font-semibold mb-1 block">Quantité / Stock</label>
          <input
            type="number"
            min="1"
            value={quantity ?? 999}
            onChange={(e) => onFieldChange("quantity", parseInt(e.target.value, 10) || 999)}
            className="w-full p-2.5 bg-slate-800 text-white rounded-xl border border-slate-700 outline-none text-sm font-bold"
          />
        </div>
      </div>
    </div>
  );
});

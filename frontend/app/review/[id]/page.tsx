"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
  Download, 
  ShoppingBag, 
  RefreshCw, 
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  FolderArchive, 
  FileCode, 
  Eye, 
  Heart,
  Tag as TagIcon,
  HelpCircle
} from "lucide-react";
import { apiUrl, assetUrl } from "@/lib/api";

interface ComplianceWarning {
  level: string;
  code: string;
  message: string;
  matched_term: string | null;
}

interface Creation {
  id: number;
  timestamp: string;
  theme: string;
  title_fr: string | null;
  title_en: string | null;
  description: string | null;
  description_en: string | null;
  tags_fr: string | null;
  tags_en: string | null;
  source_png_path: string | null;
  svg_path: string | null;
  dxf_path: string | null;
  ai_path: string | null;
  eps_path: string | null;
  pdf_path: string | null;
  upscale_png_path: string | null;
  mockup_path: string | null;
  zip_path: string | null;
  is_published_etsy: boolean;
  etsy_listing_id: string | null;
  status: string | null;
  connectivity_warnings: number | null;
  compliance_warnings: string | null;
  price: number | null;
  quantity: number | null;
}

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const creationId = params.id;
  
  const [creation, setCreation] = useState<Creation | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regeneratingSeo, setRegeneratingSeo] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [previewTab, setPreviewTab] = useState<"mockup" | "svg" | "png">("mockup");
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form editable states
  const [titleFr, setTitleFr] = useState("");
  const [titleEn, setTitleEn] = useState("");
  const [description, setDescription] = useState("");
  const [descriptionEn, setDescriptionEn] = useState("");
  const [tagsFrInput, setTagsFrInput] = useState("");
  const [tagsEnInput, setTagsEnInput] = useState("");
  const [price, setPrice] = useState<number>(3.0);
  const [quantity, setQuantity] = useState<number>(999);

  useEffect(() => {
    fetchCreation();
  }, [creationId]);

  // Parse compliance warnings from JSON
  const complianceWarnings: ComplianceWarning[] = (() => {
    if (!creation?.compliance_warnings) return [];
    try {
      const parsed = JSON.parse(creation.compliance_warnings);
      return parsed.warnings || parsed || [];
    } catch {
      return [];
    }
  })();

  const hasCriticalCompliance = complianceWarnings.some(w => w.level === "CRITICAL");
  const hasErrorCompliance = complianceWarnings.some(w => w.level === "ERROR");
  const hasWarningCompliance = complianceWarnings.some(w => w.level === "WARNING");

  const openLocalFolder = async () => {
    try {
      const res = await fetch(apiUrl(`/api/creations/${creationId}/open-folder`), {
        method: "POST"
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible d'ouvrir le dossier.");
      }
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    }
  };

  const fetchCreation = async () => {
    try {
      setLoading(true);
      const res = await fetch(apiUrl(`/api/creations/${creationId}`));
      if (!res.ok) throw new Error("Creation non trouvée.");
      const data = await res.json();
      setCreation(data);
      
      setTitleFr(data.title_fr || "");
      setTitleEn(data.title_en || "");
      setDescription(data.description || "");
      setDescriptionEn(data.description_en || "");
      setTagsFrInput(data.tags_fr || "");
      setTagsEnInput(data.tags_en || "");
      setPrice(data.price ?? 3.0);
      setQuantity(data.quantity ?? 999);
      
      // Select best preview fallback
      if (data.mockup_path) setPreviewTab("mockup");
      else if (data.svg_path) setPreviewTab("svg");
      else setPreviewTab("png");
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Erreur de chargement" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (silent: boolean = false) => {
    try {
      if (!silent) setSaving(true);
      const res = await fetch(apiUrl(`/api/creations/${creationId}`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title_fr: titleFr,
          title_en: titleEn,
          description,
          description_en: descriptionEn,
          tags_fr: tagsFrInput,
          tags_en: tagsEnInput,
          price,
          quantity,
        })
      });

      if (!res.ok) throw new Error("Impossible de sauvegarder les modifications.");
      const updated = await res.json();
      setCreation(updated);
      
      if (!silent) {
        setNotification({ type: "success", message: "Modifications enregistrées avec succès !" });
      }
      return updated;
    } catch (err: any) {
      if (!silent) {
        setNotification({ type: "error", message: err.message });
      }
      throw err;
    } finally {
      if (!silent) setSaving(false);
    }
  };

  const handleRegenerateSeo = async () => {
    try {
      setRegeneratingSeo(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-seo`), {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de régénérer le SEO.");
      }
      const data = await res.json();
      setCreation(data);
      setTitleFr(data.title_fr || "");
      setTitleEn(data.title_en || "");
      setDescription(data.description || "");
      setDescriptionEn(data.description_en || "");
      setTagsFrInput(data.tags_fr || "");
      setTagsEnInput(data.tags_en || "");
      setNotification({ type: "success", message: "SEO bilingue régénéré avec succès." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingSeo(false);
    }
  };

  const handlePublish = async () => {
    try {
      setPublishing(true);
      setNotification(null);
      
      // 1. Silent save current inputs first
      const updatedCreation = await handleSave(true);
      
      // 2. Publish
      const res = await fetch(apiUrl(`/api/creations/${creationId}/publish`), {
        method: "POST"
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Échec de la publication.");
      }

      const data = await res.json();
      
      setNotification({
        type: "success",
        message: data.is_simulation
          ? `[Mode Simulé] Publié avec succès ! ID Listing: ${data.listing_id}`
          : "Fiche produit créée avec succès sur Etsy !"
      });

      if (data.listing_url) {
        window.open(data.listing_url, "_blank");
      }
      
      // Refresh state
      fetchCreation();
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setPublishing(false);
    }
  };

  // Helper to parse comma-separated tags and return cleaned list
  const getCleanTags = (inputString: string): string[] => {
    return inputString
      .split(",")
      .map(t => t.trim())
      .filter(t => t.length > 0);
  };

  // Validation Guardrails
  const tagsFrArray = getCleanTags(tagsFrInput);
  const tagsEnArray = getCleanTags(tagsEnInput);
  
  const isTitleFrOver = titleFr.length > 140;
  const isTitleEnOver = titleEn.length > 140;
  
  const tooManyTagsFr = tagsFrArray.length > 13;
  const tooManyTagsEn = tagsEnArray.length > 13;
  
  const tagsFrTooLong = tagsFrArray.some(t => t.length > 20);
  const tagsEnTooLong = tagsEnArray.some(t => t.length > 20);

  // Listing requirement checks
  const missingRequirements: string[] = [];
  if (!titleFr.trim()) missingRequirements.push("Titre FR requis");
  if (!titleEn.trim()) missingRequirements.push("Titre EN requis");
  if (isTitleFrOver) missingRequirements.push("Titre FR dépasse 140 caractères");
  if (isTitleEnOver) missingRequirements.push("Titre EN dépasse 140 caractères");
  if (!description.trim()) missingRequirements.push("Description FR requise");
  if (!descriptionEn.trim()) missingRequirements.push("Description EN requise");
  if (tagsFrArray.length === 0) missingRequirements.push("Tags FR requis");
  if (tagsEnArray.length === 0) missingRequirements.push("Tags EN requis");
  if (!creation?.mockup_path) missingRequirements.push("Image Mockup (.PNG/.JPG) manquante");
  if (!creation?.zip_path) missingRequirements.push("Fichier Client ZIP manquant");
  if (tooManyTagsFr) missingRequirements.push("Max 13 tags en Français (actuellement " + tagsFrArray.length + ")");
  if (tooManyTagsEn) missingRequirements.push("Max 13 tags en Anglais (actuellement " + tagsEnArray.length + ")");
  if (tagsFrTooLong) missingRequirements.push("Certains tags FR dépassent 20 caractères");
  if (tagsEnTooLong) missingRequirements.push("Certains tags EN dépassent 20 caractères");

  const isPublishDisabled = missingRequirements.length > 0 || publishing || loading;

  if (loading && !creation) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center space-y-4">
        <RefreshCw className="h-10 w-10 text-indigo-500 animate-spin" />
        <p className="text-slate-400">Chargement du projet...</p>
      </div>
    );
  }

  if (!creation) {
    return (
      <div className="text-center p-8">
        <AlertTriangle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
        <p className="text-slate-200">Projet introuvable.</p>
        <button onClick={() => router.push("/")} className="text-indigo-400 font-semibold mt-2">
          Retourner à la création
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top action header */}
      <div className="flex items-center space-x-4">
        <button
          onClick={() => router.push("/dashboard")}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold line-clamp-1">{creation.theme || "Revue du Design"}</h1>
          <p className="text-xs text-slate-500">Créé le {new Date(creation.timestamp).toLocaleString("fr-FR")}</p>
        </div>
        {/* Status Badges */}
        <div className="flex flex-wrap gap-2">
          {/* Connectivity badge */}
          {(creation.connectivity_warnings ?? 0) > 2 ? (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-rose-950/80 text-rose-400 border border-rose-500/30 text-[10px] font-bold" title="Des îles flottantes ont été détectées">
              <AlertTriangle className="h-3 w-3" />
              <span>{creation.connectivity_warnings} îles SVG</span>
            </span>
          ) : (creation.connectivity_warnings ?? 0) > 0 ? (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-amber-950/80 text-amber-400 border border-amber-500/30 text-[10px] font-bold" title="Quelques sous-chemins détectés">
              <AlertTriangle className="h-3 w-3" />
              <span>{creation.connectivity_warnings} sous-paths</span>
            </span>
          ) : null}

          {/* Compliance badge */}
          {hasCriticalCompliance && (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-rose-950/80 text-rose-400 border border-rose-500/30 text-[10px] font-bold" title="Marques protégées détectées">
              <AlertTriangle className="h-3 w-3" />
              <span>⚠ Conformité</span>
            </span>
          )}
          {!hasCriticalCompliance && hasWarningCompliance && (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-amber-950/80 text-amber-400 border border-amber-500/30 text-[10px] font-bold">
              <AlertTriangle className="h-3 w-3" />
              <span>Avertissements</span>
            </span>
          )}
          {!hasCriticalCompliance && !hasErrorCompliance && !hasWarningCompliance && creation.compliance_warnings && (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold">
              <CheckCircle2 className="h-3 w-3" />
              <span>Conforme</span>
            </span>
          )}
        </div>
      </div>

      {notification && (
        <div className={`p-4 rounded-xl flex items-start space-x-3 border ${
          notification.type === "success" 
            ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/20" 
            : "bg-rose-950/40 text-rose-300 border-rose-500/20"
        }`}>
          {notification.type === "success" ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1 text-sm font-medium">{notification.message}</div>
          <button onClick={() => setNotification(null)} className="text-xs font-bold hover:underline opacity-80">
            Fermer
          </button>
        </div>
      )}

      {/* Main split grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN: VISUALIZATIONS & DOWNLOADS */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            {/* Visual preview tabs */}
            <div className="flex bg-slate-950/50 border-b border-slate-900 p-1">
              {creation.mockup_path && (
                <button
                  onClick={() => setPreviewTab("mockup")}
                  className={`flex-1 text-xs font-bold py-2 rounded-lg transition ${
                    previewTab === "mockup" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Mockup (Mise en situation)
                </button>
              )}
              {creation.svg_path && (
                <button
                  onClick={() => setPreviewTab("svg")}
                  className={`flex-1 text-xs font-bold py-2 rounded-lg transition ${
                    previewTab === "svg" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Vectoriel (SVG)
                </button>
              )}
              {creation.source_png_path && (
                <button
                  onClick={() => setPreviewTab("png")}
                  className={`flex-1 text-xs font-bold py-2 rounded-lg transition ${
                    previewTab === "png" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Original (PNG)
                </button>
              )}
            </div>

            {/* Visual panel display */}
            <div className="relative aspect-square w-full bg-slate-950/20 flex items-center justify-center p-4">
              {previewTab === "mockup" && creation.mockup_path && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`${assetUrl(creation.mockup_path)}?t=${new Date().getTime()}`}
                  alt="Mockup representation"
                  className="object-cover w-full h-full"
                />
              )}
              {previewTab === "svg" && creation.svg_path && (
                // SVG renders natively in img tag
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={assetUrl(creation.svg_path)}
                  alt="Crisp SVG paths representation"
                  className="object-contain max-h-full max-w-full bg-white/5 p-4 rounded"
                />
              )}
              {previewTab === "png" && creation.source_png_path && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={assetUrl(creation.source_png_path)}
                  alt="Source PNG stencil representation"
                  className="object-contain max-h-full max-w-full"
                />
              )}
            </div>
          </div>

          {/* Downloads Block panel */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
                Fichiers et livrables
              </h3>
              <button
                onClick={openLocalFolder}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 hover:underline transition cursor-pointer"
              >
                Ouvrir le dossier local
              </button>
            </div>

            <div className="space-y-2.5">
              {creation.zip_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/zip`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/25 text-indigo-300 text-sm font-semibold transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FolderArchive className="h-5 w-5 text-indigo-400" />
                    <span>Package Client (.ZIP)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}

              {creation.svg_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/svg`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-slate-300 text-xs font-medium transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FileCode className="h-4.5 w-4.5 text-slate-400" />
                    <span>Fichier Vectoriel (SVG)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}

              {creation.dxf_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/dxf`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-slate-300 text-xs font-medium transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FileCode className="h-4.5 w-4.5 text-slate-400" />
                    <span>Fichier CAO Découpe (DXF)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}

              {creation.pdf_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/pdf`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-slate-300 text-xs font-medium transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FileText className="h-4.5 w-4.5 text-slate-400" />
                    <span>Format Impression (PDF)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}

              {creation.upscale_png_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/png`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-slate-300 text-xs font-medium transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FileText className="h-4.5 w-4.5 text-slate-400" />
                    <span>Format Transparent x3 (PNG)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: SEO & METADATA FORM */}
        <div className="lg:col-span-7 space-y-6">
          <div className="glass-panel rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-bold border-b border-slate-900 pb-3">Optimisation SEO & Fiche Produit</h2>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleRegenerateSeo}
                disabled={regeneratingSeo}
                className="inline-flex items-center space-x-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${regeneratingSeo ? "animate-spin" : ""}`} />
                <span>{regeneratingSeo ? "Régénération..." : "Régénérer SEO bilingue"}</span>
              </button>
            </div>
            
            {/* French Title */}
            <div className="space-y-1.5 text-left">
              <div className="flex justify-between items-center text-xs">
                <label className="font-bold text-slate-300">Titre de la fiche en Français (Etsy FR)</label>
                <span className={`font-semibold ${isTitleFrOver ? "text-rose-400 font-bold" : "text-slate-500"}`}>
                  {titleFr.length} / 140
                </span>
              </div>
              <input
                type="text"
                value={titleFr}
                onChange={(e) => setTitleFr(e.target.value)}
                className={`w-full rounded-lg px-4 py-2.5 text-sm glass-input ${
                  isTitleFrOver ? "border-rose-500 focus:border-rose-500 focus:ring-rose-500/20" : ""
                }`}
              />
              {isTitleFrOver && (
                <p className="text-[10px] font-semibold text-rose-400 flex items-center space-x-1">
                  <AlertTriangle className="h-3 w-3" />
                  <span>Alerte : Le titre dépasse la limite réglementaire d&apos;Etsy de 140 caractères.</span>
                </p>
              )}
            </div>

            {/* English Title */}
            <div className="space-y-1.5 text-left">
              <div className="flex justify-between items-center text-xs">
                <label className="font-bold text-slate-300">Titre de la fiche en Anglais (Etsy EN)</label>
                <span className={`font-semibold ${isTitleEnOver ? "text-rose-400 font-bold" : "text-slate-500"}`}>
                  {titleEn.length} / 140
                </span>
              </div>
              <input
                type="text"
                value={titleEn}
                onChange={(e) => setTitleEn(e.target.value)}
                className={`w-full rounded-lg px-4 py-2.5 text-sm glass-input ${
                  isTitleEnOver ? "border-rose-500 focus:border-rose-500 focus:ring-rose-500/20" : ""
                }`}
              />
              {isTitleEnOver && (
                <p className="text-[10px] font-semibold text-rose-400 flex items-center space-x-1">
                  <AlertTriangle className="h-3 w-3" />
                  <span>Alerte : Le titre dépasse la limite réglementaire d&apos;Etsy de 140 caractères.</span>
                </p>
              )}
            </div>

            {/* Description Textarea FR */}
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-bold text-slate-300">Description FR (Etsy France)</label>
              <textarea
                rows={8}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 text-xs glass-input font-mono leading-relaxed"
              />
            </div>

            {/* Description Textarea EN */}
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-bold text-slate-300">Description EN (Etsy International — 80% du trafic)</label>
              <textarea
                rows={8}
                value={descriptionEn}
                onChange={(e) => setDescriptionEn(e.target.value)}
                placeholder="English description generated by Gemini. Edit to customize for international audience."
                className="w-full rounded-lg px-4 py-2.5 text-xs glass-input font-mono leading-relaxed"
              />
            </div>

            {/* Tags French */}
            <div className="space-y-2 text-left">
              <div className="flex justify-between items-center text-xs">
                <label className="font-bold text-slate-300">Tags en Français (Séparés par des virgules)</label>
                <span className={`font-semibold ${tooManyTagsFr ? "text-rose-400 font-bold" : "text-slate-500"}`}>
                  {tagsFrArray.length} / 13 tags
                </span>
              </div>
              <input
                type="text"
                placeholder="laser, svg deco, cnc bois..."
                value={tagsFrInput}
                onChange={(e) => setTagsFrInput(e.target.value)}
                className={`w-full rounded-lg px-4 py-2 text-xs glass-input ${tooManyTagsFr ? "border-rose-500" : ""}`}
              />
              <div className="flex flex-wrap gap-1.5 mt-1">
                {tagsFrArray.map((tag, idx) => {
                  const isTooLong = tag.length > 20;
                  return (
                    <span 
                      key={idx} 
                      className={`inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-md ${
                        isTooLong 
                          ? "bg-rose-950/60 text-rose-400 border border-rose-500/20" 
                          : "bg-slate-900 text-slate-300 border border-slate-800"
                      }`}
                    >
                      <TagIcon className="h-2.5 w-2.5 opacity-60" />
                      <span>{tag}</span>
                      {isTooLong && <span className="font-bold text-[8px] text-rose-400">(&gt;20ch)</span>}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Tags English */}
            <div className="space-y-2 text-left">
              <div className="flex justify-between items-center text-xs">
                <label className="font-bold text-slate-300">Tags en Anglais (Séparés par des virgules)</label>
                <span className={`font-semibold ${tooManyTagsEn ? "text-rose-400 font-bold" : "text-slate-500"}`}>
                  {tagsEnArray.length} / 13 tags
                </span>
              </div>
              <input
                type="text"
                placeholder="laser cut svg, wood dxf, wall art vector..."
                value={tagsEnInput}
                onChange={(e) => setTagsEnInput(e.target.value)}
                className={`w-full rounded-lg px-4 py-2 text-xs glass-input ${tooManyTagsEn ? "border-rose-500" : ""}`}
              />
              <div className="flex flex-wrap gap-1.5 mt-1">
                {tagsEnArray.map((tag, idx) => {
                  const isTooLong = tag.length > 20;
                  return (
                    <span 
                      key={idx} 
                      className={`inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-md ${
                        isTooLong 
                          ? "bg-rose-950/60 text-rose-400 border border-rose-500/20" 
                          : "bg-slate-900 text-slate-300 border border-slate-800"
                      }`}
                    >
                      <TagIcon className="h-2.5 w-2.5 opacity-60" />
                      <span>{tag}</span>
                      {isTooLong && <span className="font-bold text-[8px] text-rose-400">(&gt;20ch)</span>}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Control & Publishing actions */}
            <div className="pt-4 border-t border-slate-900 space-y-4">

              {/* Price & Quantity */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5 text-left">
                  <label className="text-xs font-bold text-slate-300 flex items-center space-x-1.5">
                    <span>💶 Prix (€)</span>
                  </label>
                  <input
                    type="number"
                    min="0.50"
                    max="999"
                    step="0.50"
                    value={price}
                    onChange={(e) => setPrice(parseFloat(e.target.value) || 3.0)}
                    className="w-full rounded-lg px-4 py-2.5 text-sm glass-input text-emerald-300 font-bold"
                  />
                  <p className="text-[10px] text-slate-600">Prix affiché sur Etsy</p>
                </div>
                <div className="space-y-1.5 text-left">
                  <label className="text-xs font-bold text-slate-300 flex items-center space-x-1.5">
                    <span>📦 Quantité</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="999"
                    step="1"
                    value={quantity}
                    onChange={(e) => setQuantity(parseInt(e.target.value) || 999)}
                    className="w-full rounded-lg px-4 py-2.5 text-sm glass-input font-bold"
                  />
                  <p className="text-[10px] text-slate-600">Stock disponible (max 999)</p>
                </div>
              </div>

              <div className="flex items-center justify-between gap-4">
                <button
                  onClick={() => handleSave()}
                  disabled={saving}
                  className="flex-shrink-0 bg-slate-800 hover:bg-slate-750 text-slate-300 px-5 py-3 rounded-xl text-sm font-semibold transition disabled:opacity-50"
                >
                  {saving ? "Enregistrement..." : "Enregistrer"}
                </button>

                {/* Publish to Etsy button */}
                <div className="flex-1 relative group">
                  <button
                    onClick={handlePublish}
                    disabled={isPublishDisabled}
                    className={`w-full glow-btn flex items-center justify-center space-x-2 rounded-xl bg-gradient-to-tr from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 disabled:shadow-none disabled:border disabled:border-slate-800 disabled:cursor-not-allowed text-white py-3 font-bold transition`}
                  >
                    {publishing ? (
                      <RefreshCw className="h-5 w-5 animate-spin" />
                    ) : (
                      <ShoppingBag className="h-5 w-5" />
                    )}
                    <span>{creation.is_published_etsy ? "Republier sur Etsy" : "Publier sur Etsy"}</span>
                  </button>
                  
                  {/* Tooltip detail listing blocker requirements */}
                  {isPublishDisabled && (
                    <div className="absolute bottom-full right-0 mb-2 w-80 scale-0 group-hover:scale-100 transition-all duration-200 z-50 origin-bottom-right">
                      <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl shadow-2xl text-left space-y-2">
                        <div className="text-xs font-bold text-rose-400 flex items-center space-x-1.5">
                          <AlertTriangle className="h-4 w-4" />
                          <span>Conditions obligatoires manquantes :</span>
                        </div>
                        <ul className="text-[10px] text-slate-400 space-y-1 list-disc pl-4 font-medium">
                          {missingRequirements.map((req, idx) => (
                            <li key={idx}>{req}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

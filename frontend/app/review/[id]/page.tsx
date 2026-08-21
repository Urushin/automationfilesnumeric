"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Save,
  ShoppingBag,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  FolderOpen,
  Sparkles,
} from "lucide-react";
import { apiUrl, assetUrl } from "@/lib/api";
import RetouchModal from "@/components/RetouchModal";
import { SeoForm } from "./components/SeoForm";
import { MediaGallery } from "./components/MediaGallery";
import { VectorViewer } from "./components/VectorViewer";
import { QualityCard } from "./components/QualityCard";
import { EtsyPublishModal } from "./components/EtsyPublishModal";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const creationId = params?.id ? String(params.id) : null;

  const [creation, setCreation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);

  // SEO Form state
  const [seoLangTab, setSeoLangTab] = useState<"fr" | "en">("fr");
  const [translatingField, setTranslatingField] = useState<string | null>(null);

  // Media Gallery state
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [previewTab, setPreviewTab] = useState<"mockup" | "commercial" | "transparent_png" | "source">("mockup");
  const [activeMockupStyleIdx, setActiveMockupStyleIdx] = useState(0);
  const [activeCommercialIdx, setActiveCommercialIdx] = useState(0);
  const [regeneratingMockup, setRegeneratingMockup] = useState(false);

  // Vector viewer state
  const [activeBundleIdx, setActiveBundleIdx] = useState(0);

  // Retouch modal state
  const [retouchUrl, setRetouchUrl] = useState<string | null>(null);

  // Etsy publish modal state
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState<"draft" | "active">("draft");
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishSuccess, setPublishSuccess] = useState<{ listing_id: string; url?: string } | null>(null);

  // Island diagnostic & Auto-bridge state
  const [islandOverlayUrl, setIslandOverlayUrl] = useState<string | null>(null);
  const [showIslandOverlay, setShowIslandOverlay] = useState(false);
  const [autoBridging, setAutoBridging] = useState(false);


  // Fetch Creation
  const fetchCreation = useCallback(async () => {
    if (!creationId) return;
    try {
      const res = await fetch(apiUrl(`/api/creations/${creationId}`));
      if (!res.ok) throw new Error("Fichier introuvable.");
      const data = await res.json();
      setCreation(data);

      // Parse initial selected images
      if (data.selected_images_raw) {
        const parsed = data.selected_images_raw.split(",").map((s: string) => s.trim()).filter(Boolean);
        setSelectedImages(parsed);
      } else {
        const defaults: string[] = [];
        if (data.mockup_paths && data.mockup_paths.length > 0) {
          defaults.push(...data.mockup_paths);
        } else if (data.mockup_path) {
          defaults.push(data.mockup_path);
        }
        if (data.upscale_png_path && !defaults.includes(data.upscale_png_path)) {
          defaults.push(data.upscale_png_path);
        }
        setSelectedImages(defaults.slice(0, 10));
      }
    } catch (e: any) {
      setNotification({ type: "error", message: e.message || "Erreur de chargement." });
    } finally {
      setLoading(false);
    }
  }, [creationId]);

  useEffect(() => {
    fetchCreation();
  }, [fetchCreation]);

  // Compute available images for Etsy gallery
  const availableImages = useMemo(() => {
    if (!creation) return [];
    const set = new Set<string>();
    if (creation.mockup_paths) creation.mockup_paths.forEach((p: string) => set.add(p));
    if (creation.mockup_path) set.add(creation.mockup_path);
    if (creation.commercial_mockup_paths) creation.commercial_mockup_paths.forEach((p: string) => set.add(p));
    if (creation.real_mockup_paths) creation.real_mockup_paths.forEach((p: string) => set.add(p));
    if (creation.real_mockup_path) set.add(creation.real_mockup_path);
    if (creation.upscale_png_path) set.add(creation.upscale_png_path);
    if (creation.png_paths) creation.png_paths.forEach((p: string) => set.add(p));
    if (creation.source_png_path) set.add(creation.source_png_path);
    return Array.from(set);
  }, [creation]);

  // Handle field change in SEO form
  const handleFieldChange = useCallback((field: string, value: any) => {
    setCreation((prev: any) => {
      if (!prev) return null;
      return { ...prev, [field]: value };
    });
  }, []);

  // Save all modifications
  const handleSave = async () => {
    if (!creation) return;
    setSaving(true);
    try {
      const payload = {
        title_fr: creation.title_fr,
        title_en: creation.title_en,
        description: creation.description,
        description_en: creation.description_en,
        tags_fr: creation.tags_fr,
        tags_en: creation.tags_en,
        price: creation.price,
        quantity: creation.quantity,
        selected_images_raw: selectedImages.join(","),
      };
      const res = await fetch(apiUrl(`/api/creations/${creation.id}`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Erreur de sauvegarde.");
      setNotification({ type: "success", message: "Modifications enregistrées avec succès ! ✔" });
      setTimeout(() => setNotification(null), 3000);
    } catch (e: any) {
      setNotification({ type: "error", message: e.message || "Erreur de sauvegarde." });
    } finally {
      setSaving(false);
    }
  };

  // Translate field handler
  const handleTranslate = async (field: "title" | "description" | "tags", text: string) => {
    if (!text) return;
    setTranslatingField(field);
    try {
      const res = await fetch(apiUrl("/api/creations/translate-seo"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.translated) {
          const targetKey =
            field === "title" ? "title_en" : field === "description" ? "description_en" : "tags_en";
          handleFieldChange(targetKey, data.translated);
          setNotification({ type: "success", message: `Traduction en anglais effectuée !` });
          setTimeout(() => setNotification(null), 3000);
        }
      }
    } catch {
      setNotification({ type: "error", message: "Erreur lors de la traduction." });
    } finally {
      setTranslatingField(null);
    }
  };

  // Gallery toggle handlers
  const toggleImageSelection = useCallback((path: string) => {
    setSelectedImages((prev) => {
      if (prev.includes(path)) {
        return prev.filter((p) => p !== path);
      } else {
        if (prev.length >= 10) return prev;
        return [...prev, path];
      }
    });
  }, []);

  const setAsPrimaryImage = useCallback((path: string) => {
    setSelectedImages((prev) => {
      const filtered = prev.filter((p) => p !== path);
      return [path, ...filtered];
    });
  }, []);

  // Regenerate Mockup handler
  const handleRegenerateMockup = async () => {
    if (!creation) return;
    setRegeneratingMockup(true);
    try {
      const res = await fetch(apiUrl(`/api/creations/${creation.id}/regenerate-mockup`), {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setCreation((prev: any) => ({
          ...prev,
          mockup_paths: data.mockup_paths || prev.mockup_paths,
          mockup_path: data.mockup_path || prev.mockup_path,
        }));
        setNotification({ type: "success", message: "Pack Etsy régénéré avec succès !" });
        setTimeout(() => setNotification(null), 3000);
      }
    } catch {
      setNotification({ type: "error", message: "Erreur lors de la régénération des mockups." });
    } finally {
      setRegeneratingMockup(false);
    }
  };

  // Publish to Etsy handler
  const handlePublishToEtsy = async () => {
    if (!creation) return;
    setPublishing(true);
    setPublishError(null);
    try {
      const payload = {
        title_fr: creation.title_fr,
        title_en: creation.title_en,
        description: creation.description,
        description_en: creation.description_en,
        tags_fr: creation.tags_fr,
        tags_en: creation.tags_en,
        price: creation.price ?? 3.0,
        quantity: creation.quantity ?? 999,
        state: publishStatus,
        selected_images: selectedImages,
      };

      const res = await fetch(apiUrl(`/api/creations/${creation.id}/publish`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Erreur lors de la publication Etsy.");
      }

      setPublishSuccess({
        listing_id: data.listing_id || "OK",
        url: data.url,
      });
      setCreation((prev: any) => ({ ...prev, is_published_etsy: true, etsy_listing_id: data.listing_id }));
    } catch (e: any) {
      setPublishError(e.message || "Erreur de publication.");
    } finally {
      setPublishing(false);
    }
  };

  // Island diagnostic & Auto-bridge handlers
  const handleToggleIslandOverlay = async () => {
    if (!showIslandOverlay && !islandOverlayUrl) {
      try {
        const res = await fetch(apiUrl(`/api/creations/${creation.id}/islands-analysis`));
        if (res.ok) {
          const data = await res.json();
          setIslandOverlayUrl(data.overlay_url);
          setShowIslandOverlay(true);
        }
      } catch {
        setNotification({ type: "error", message: "Impossible de charger la carte des îlots." });
      }
    } else {
      setShowIslandOverlay(!showIslandOverlay);
    }
  };

  const handleAutoBridge = async () => {
    if (!creation) return;
    setAutoBridging(true);
    try {
      const res = await fetch(apiUrl(`/api/creations/${creation.id}/auto-bridge`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bridge_width: 5 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur lors du pontage automatique.");

      setShowIslandOverlay(false);
      setIslandOverlayUrl(null);
      setNotification({ type: "success", message: `⚡ ${data.message || "Auto-Bridging appliqué avec succès !"} ✔` });
      fetchCreation();
    } catch (e: any) {
      setNotification({ type: "error", message: e.message || "Erreur d'auto-bridging." });
    } finally {
      setAutoBridging(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-4 text-slate-400">
        <Loader2 className="h-10 w-10 animate-spin text-indigo-500" />
        <p className="text-sm font-semibold">Chargement de la création...</p>
      </div>
    );
  }

  if (!creation) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center space-y-4">
        <AlertTriangle className="h-12 w-12 text-amber-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Création introuvable</h2>
        <Link href="/" className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 font-bold">
          <ArrowLeft className="h-4 w-4" /> Retour au tableau de bord
        </Link>
      </div>
    );
  }

  // Parse compliance warnings
  let complianceList: any[] = [];
  if (creation.compliance_warnings) {
    try {
      const parsed = JSON.parse(creation.compliance_warnings);
      complianceList = Array.isArray(parsed) ? parsed : parsed.warnings || [];
    } catch {
      complianceList = [];
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8 animate-in fade-in duration-200">
      {/* ── Top Bar ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="space-y-1">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition font-semibold"
          >
            <ArrowLeft className="h-4 w-4" /> Retour aux créations
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-white tracking-tight">
              {creation.theme || "Design sans titre"}
            </h1>
            {creation.is_published_etsy && (
              <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Publié sur Etsy
              </span>
            )}
          </div>
        </div>

        {/* Global Actions */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl border border-slate-700 transition flex items-center gap-2"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            <span>Sauvegarder</span>
          </button>

          <button
            type="button"
            onClick={() => setIsPublishModalOpen(true)}
            className="px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-amber-600/20 transition flex items-center gap-2"
          >
            <ShoppingBag className="h-4 w-4" />
            <span>Publier sur Etsy</span>
          </button>
        </div>
      </div>

      {/* Toast Notification */}
      {notification && (
        <div
          className={`p-4 rounded-xl border flex items-center gap-3 text-xs font-semibold animate-in fade-in duration-150 ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : notification.type === "error"
              ? "bg-rose-500/10 border-rose-500/30 text-rose-300"
              : "bg-indigo-500/10 border-indigo-500/30 text-indigo-300"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-rose-400" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* ── Two-Column Layout ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Visuals & Vector Inspection (6 cols) */}
        <div className="lg:col-span-6 space-y-8">
          <MediaGallery
            creation={creation}
            availableImages={availableImages}
            selectedImages={selectedImages}
            toggleImageSelection={toggleImageSelection}
            setAsPrimaryImage={setAsPrimaryImage}
            previewTab={previewTab}
            setPreviewTab={setPreviewTab}
            activeMockupStyleIdx={activeMockupStyleIdx}
            setActiveMockupStyleIdx={setActiveMockupStyleIdx}
            activeCommercialIdx={activeCommercialIdx}
            setActiveCommercialIdx={setActiveCommercialIdx}
            onRegenerateMockup={handleRegenerateMockup}
            regeneratingMockup={regeneratingMockup}
            onOpenRetouch={(url) => setRetouchUrl(url)}
            assetUrl={assetUrl}
          />

          <VectorViewer
            creation={creation}
            activeBundleIdx={activeBundleIdx}
            setActiveBundleIdx={setActiveBundleIdx}
            assetUrl={assetUrl}
            islandOverlayUrl={islandOverlayUrl}
            showIslandOverlay={showIslandOverlay}
            onToggleIslandOverlay={handleToggleIslandOverlay}
          />
        </div>

        {/* Right Column: SEO Copywriting, Quality & Publishing (6 cols) */}
        <div className="lg:col-span-6 space-y-8">
          <QualityCard
            connectivityWarnings={creation.connectivity_warnings || 0}
            complianceWarnings={complianceList}
            onToggleIslandOverlay={handleToggleIslandOverlay}
            showIslandOverlay={showIslandOverlay}
            onAutoBridge={handleAutoBridge}
            autoBridging={autoBridging}
          />


          <SeoForm
            theme={creation.theme}
            titleFr={creation.title_fr || ""}
            titleEn={creation.title_en || ""}
            descriptionFr={creation.description || ""}
            descriptionEn={creation.description_en || ""}
            tagsFr={creation.tags_fr || ""}
            tagsEn={creation.tags_en || ""}
            price={creation.price ?? 3.0}
            quantity={creation.quantity ?? 999}
            seoLangTab={seoLangTab}
            setSeoLangTab={setSeoLangTab}
            onFieldChange={handleFieldChange}
            onTranslate={handleTranslate}
            translatingField={translatingField}
          />
        </div>
      </div>

      {/* ── Retouch Canvas Modal ───────────────────────────────────────────── */}
      {retouchUrl && (
        <RetouchModal
          isOpen={Boolean(retouchUrl)}
          imageUrl={retouchUrl}
          creationId={creation.id}
          onClose={() => setRetouchUrl(null)}
          onValidate={() => {
            setRetouchUrl(null);
            fetchCreation();
          }}
        />
      )}


      {/* ── Etsy Publish Modal ─────────────────────────────────────────────── */}
      <EtsyPublishModal
        isOpen={isPublishModalOpen}
        onClose={() => {
          setIsPublishModalOpen(false);
          setPublishSuccess(null);
          setPublishError(null);
        }}
        creation={creation}
        onPublish={handlePublishToEtsy}
        publishing={publishing}
        publishError={publishError}
        publishSuccess={publishSuccess}
        price={creation.price ?? 3.0}
        quantity={creation.quantity ?? 999}
        publishStatus={publishStatus}
        setPublishStatus={setPublishStatus}
        selectedImagesCount={selectedImages.length}
      />
    </div>
  );
}

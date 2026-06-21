"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Download, 
  ShoppingBag, 
  RefreshCw, 
  Languages,
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  FolderArchive, 
  FileCode, 
  Eye, 
  Heart,
  Tag as TagIcon,
  HelpCircle,
  Compass,
  ChevronUp,
  ChevronDown,
  Check,
  Copy,
  Trash,
  Lock,
  Sparkles,
  Loader2
} from "lucide-react";
import { apiUrl, assetUrl } from "@/lib/api";
import RetouchModal from "@/components/RetouchModal";

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
  real_mockup_path: string | null;
  zip_path: string | null;
  is_published_etsy: boolean;
  etsy_listing_id: string | null;
  status: string | null;
  connectivity_warnings: number | null;
  compliance_warnings: string | null;
  price: number | null;
  quantity: number | null;
  png_paths?: string[];
  svg_paths?: string[];
  pdf_paths?: string[];
  selected_images_raw?: string | null;
  pipeline_status?: any;
  source_png_variants?: string[];
  source_png_variants_raw?: string | null;
}

interface CopyFieldProps {
  label: string;
  value: string;
}

function CopyField({ label, value }: CopyFieldProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col gap-1.5 p-3 rounded-xl bg-slate-900/50 border border-slate-800/40">
      <div className="flex justify-between items-center">
        <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">{label}</span>
        <button
          onClick={handleCopy}
          disabled={!value}
          className="text-xs text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              <span>Copié</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copier</span>
            </>
          )}
        </button>
      </div>
      <textarea
        readOnly
        value={value || "En attente..."}
        rows={Math.min(5, Math.max(1, value ? value.split("\n").length : 1))}
        className="w-full text-xs bg-transparent border-0 outline-none text-slate-300 resize-none leading-relaxed p-0 focus:ring-0"
      />
    </div>
  );
}

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const creationId = params.id;
  
  const [creation, setCreation] = useState<Creation | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regeneratingSeo, setRegeneratingSeo] = useState(false);
  const [translatingSeo, setTranslatingSeo] = useState(false);
  const [regeneratingImage, setRegeneratingImage] = useState(false);
  const [regeneratingVector, setRegeneratingVector] = useState(false);
  const [regeneratingCad, setRegeneratingCad] = useState(false);
  const [regeneratingUpscale, setRegeneratingUpscale] = useState(false);
  const [regeneratingPdf, setRegeneratingPdf] = useState(false);
  const [regeneratingMockup, setRegeneratingMockup] = useState(false);
  const [regeneratingZip, setRegeneratingZip] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleCopyText = (text: string, fieldId: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(fieldId);
    setTimeout(() => setCopiedField(null), 2000);
  };

  // Instructions states
  const [imageInstructions, setImageInstructions] = useState("");
  const [mockupInstructions, setMockupInstructions] = useState("");
  const [applyTpOverlay, setApplyTpOverlay] = useState(false);
  const [bundleSize, setBundleSize] = useState(1);
  const [accordionOpen, setAccordionOpen] = useState(false);
  const [shouldVectorize, setShouldVectorize] = useState(false);
  const [nImages, setNImages] = useState(1);

  const [publishing, setPublishing] = useState(false);
  const [previewTab, setPreviewTab] = useState<"mockup" | "real_mockup" | "svg" | "png">("mockup");
  const [activeElementIdx, setActiveElementIdx] = useState(0);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form editable states
  const [theme, setTheme] = useState("");
  const [titleFr, setTitleFr] = useState("");
  const [titleEn, setTitleEn] = useState("");
  const [description, setDescription] = useState("");
  const [descriptionEn, setDescriptionEn] = useState("");
  const [tagsFrInput, setTagsFrInput] = useState("");
  const [tagsEnInput, setTagsEnInput] = useState("");
  const [price, setPrice] = useState<number>(3.0);
  const [quantity, setQuantity] = useState<number>(999);
  const [selectedImages, setSelectedImages] = useState<string[]>([]);

  const setSelectedImagesSafely = (updaterOrValue: string[] | ((prev: string[]) => string[])) => {
    setSelectedImages(prev => {
      let next: string[];
      if (typeof updaterOrValue === "function") {
        next = updaterOrValue(prev);
      } else {
        next = updaterOrValue;
      }
      const clean = next.filter(p => p !== "/assets/templates/condition_dl.png");
      return [...clean, "/assets/templates/condition_dl.png"];
    });
  };

  const [isRetouchModalOpen, setIsRetouchModalOpen] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [selectingVariant, setSelectingVariant] = useState(false);
  const [activeAssetPath, setActiveAssetPath] = useState<string | null>(null);
  const [activeAssetType, setActiveAssetType] = useState<string | null>(null);

  const handleSelectVariant = async (path: string) => {
    try {
      setSelectingVariant(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/select-variant`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variant_path: path })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de sélectionner cette variante.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Variante sélectionnée. Régénération en cours..." });
      
      setReprocessing(true);
      const pollInterval = setInterval(async () => {
        try {
          const pollRes = await fetch(apiUrl(`/api/creations/${creationId}`));
          if (pollRes.ok) {
            const pollData = await pollRes.json();
            if (pollData.status === "completed" || pollData.status === "completed ✓") {
              clearInterval(pollInterval);
              setCreation(pollData);
              setReprocessing(false);
              setNotification({ type: "success", message: "Régénération terminée !" });
              setTitleFr(pollData.title_fr || "");
              setTitleEn(pollData.title_en || "");
              setDescription(pollData.description || "");
              setDescriptionEn(pollData.description_en || "");
              setTagsFrInput(pollData.tags_fr || "");
              setTagsEnInput(pollData.tags_en || "");
            } else if (pollData.status === "failed") {
              clearInterval(pollInterval);
              setCreation(pollData);
              setReprocessing(false);
              setNotification({ type: "error", message: `La régénération a échoué: ${pollData.failed_reason}` });
            }
          }
        } catch (pollErr) {
          console.error("Polling error:", pollErr);
        }
      }, 3000);

    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setSelectingVariant(false);
    }
  };

  const handleOpenWorkspace = (path: string, type: string) => {
    setActiveAssetPath(path);
    setActiveAssetType(type);
    setIsRetouchModalOpen(true);
  };

  const handleRetouchValidate = async (updated?: any) => {
    try {
      setIsRetouchModalOpen(false);
      setReprocessing(true);
      setNotification(null);
      
      const pollInterval = setInterval(async () => {
        try {
          const res = await fetch(apiUrl(`/api/creations/${creationId}`));
          if (res.ok) {
            const data = await res.json();
            if (data.status === "completed" || data.status === "completed ✓") {
              clearInterval(pollInterval);
              setCreation(data);
              setReprocessing(false);
              setNotification({ type: "success", message: "Design et mockups régénérés avec succès après retouche." });
              setTitleFr(data.title_fr || "");
              setTitleEn(data.title_en || "");
              setDescription(data.description || "");
              setDescriptionEn(data.description_en || "");
              setTagsFrInput(data.tags_fr || "");
              setTagsEnInput(data.tags_en || "");
              setPrice(data.price ?? 3.0);
              setQuantity(data.quantity ?? 999);
              setBundleSize(data.bundle_size || 1);
              if (data.selected_images_raw) {
                setSelectedImagesSafely(data.selected_images_raw.split(",").filter(Boolean));
              }
              setActiveAssetPath(null);
              setActiveAssetType(null);
            } else if (data.status === "failed") {
              clearInterval(pollInterval);
              setReprocessing(false);
              setNotification({ type: "error", message: "La régénération après retouche a échoué : " + data.failed_reason });
              setActiveAssetPath(null);
              setActiveAssetType(null);
            }
          }
        } catch (pollErr) {
          console.error("Polling error:", pollErr);
        }
      }, 3000);
    } catch (error) {
      console.error("Failed to reprocess:", error);
      setNotification({ type: "error", message: (error as Error).message });
      setReprocessing(false);
      setActiveAssetPath(null);
      setActiveAssetType(null);
    }
  };

  const handleDeleteImage = async (path: string, type: string) => {
    try {
      setSaving(true);
      const payload: any = {};
      if (type === "mockup" && path === creation?.mockup_path) {
        payload.mockup_path = null;
      } else if (type === "mockup" && path === creation?.real_mockup_path) {
        payload.real_mockup_path = null;
      } else if (type === "split_element") {
        const remaining = (creation?.png_paths || []).filter(p => p !== path);
        payload.png_paths_raw = remaining.join(",");
      }

      // Also filter out of selectedImages
      const newSelected = selectedImages.filter(p => p !== path);
      payload.selected_images_raw = newSelected.join(",");

      const res = await fetch(apiUrl(`/api/creations/${creationId}`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Impossible de supprimer l'image.");
      const updated = await res.json();
      setCreation(updated);
      setSelectedImagesSafely(newSelected);
      setNotification({ type: "success", message: "Image supprimée avec succès." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setSaving(false);
    }
  };

  // SSE Streaming progress states
  const [streamProgress, setStreamProgress] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStepNum, setCurrentStepNum] = useState(0);
  const [activeModules, setActiveModules] = useState({
    generate_ai_stencil: true,
    vectorize: true,
    convert_cad: true,
    format_pdf: true,
    upscale: true,
    generate_real_mockup: true,
    package: true,
    generate_seo: true,
  });

  useEffect(() => {
    fetchCreation();
  }, [creationId]);

  useEffect(() => {
    if (typeof window === "undefined" || !creationId) return;

    const params = new URLSearchParams(window.location.search);
    const streamType = params.get("stream");
    const themeParam = params.get("theme") || "";

    if (!streamType) return;

    setIsStreaming(true);
    setStreamProgress("Initialisation du canal de streaming...");

    // Parse options from URL to filter active modules UI
    const opts = { ...activeModules };
    let hasCustomOptions = false;
    params.forEach((val, key) => {
      if (key in opts) {
        (opts as any)[key] = val === "true";
        hasCustomOptions = true;
      }
    });
    if (hasCustomOptions) {
      setActiveModules(opts);
    }

    let url = "";
    if (streamType === "global") {
      const query = window.location.search.replace("stream=global", "").replace("?&", "?");
      url = apiUrl(`/api/pipeline/stream/global${query}&creation_id=${creationId}`);
    } else if (streamType === "modular") {
      // Re-use current search query with creation_id
      const query = window.location.search.replace("stream=modular", "").replace("?&", "?");
      url = apiUrl(`/api/pipeline/stream/modular${query}&creation_id=${creationId}`);
    }

    const eventSource = new EventSource(url);

    eventSource.addEventListener("status", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        if (data.msg) setStreamProgress(data.msg);
        if (data.step) setCurrentStepNum(data.step);
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("image_ready", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setCreation(prev => prev ? { ...prev, source_png_path: data.source_png_path } : null);
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("assets_ready", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setCreation(prev => {
          if (!prev) return null;
          const updated = { ...prev };
          if (data.upscale_png_path) updated.upscale_png_path = data.upscale_png_path;
          if (data.dxf_path) updated.dxf_path = data.dxf_path;
          if (data.ai_path) updated.ai_path = data.ai_path;
          if (data.eps_path) updated.eps_path = data.eps_path;
          if (data.pdf_path) updated.pdf_path = data.pdf_path;
          if (data.zip_path) updated.zip_path = data.zip_path;
          if (data.png_paths) updated.png_paths = data.png_paths;
          if (data.pdf_paths) updated.pdf_paths = data.pdf_paths;
          return updated;
        });
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("vector_ready", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setCreation(prev => {
          if (!prev) return null;
          const updated = { ...prev, svg_path: data.svg_path };
          if (data.svg_paths) updated.svg_paths = data.svg_paths;
          if (data.connectivity) {
            updated.connectivity_warnings = Math.max(0, (data.connectivity.island_count || 1) - 1);
          }
          return updated;
        });
        if (data.svg_path) {
          setPreviewTab("svg");
        }
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("mockup_ready", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setCreation(prev => prev ? { ...prev, mockup_path: data.mockup_path } : null);
        setPreviewTab("mockup");
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("real_mockup_ready", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setCreation(prev => prev ? { ...prev, real_mockup_path: data.real_mockup_path } : null);
        setPreviewTab("real_mockup");
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("seo_ready", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setTitleFr(data.title_fr || "");
        setTitleEn(data.title_en || "");
        setDescription(data.description || data.description_fr || "");
        setDescriptionEn(data.description_en || "");
        
        const formatTags = (tags: any) => {
          if (Array.isArray(tags)) return tags.join(", ");
          return tags || "";
        };
        setTagsFrInput(formatTags(data.tags_fr));
        setTagsEnInput(formatTags(data.tags_en));
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("compliance_result", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setCreation(prev => prev ? { ...prev, compliance_warnings: JSON.stringify(data) } : null);
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener("done", () => {
      setIsStreaming(false);
      setStreamProgress("Traitement terminé avec succès !");
      eventSource.close();
      
      // Clean query parameters to avoid restreaming on refresh
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, "", cleanUrl);
      
      fetchCreation();
    });

    eventSource.addEventListener("error", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setNotification({ type: "error", message: `Erreur du pipeline : ${data.msg}` });
      } catch {
        setNotification({ type: "error", message: "Une erreur réseau est survenue lors de la synchronisation SSE." });
      }
      setIsStreaming(false);
      eventSource.close();
    });

    return () => {
      eventSource.close();
    };
  }, [creationId]);

  // Sync available PNG images to selected list
  useEffect(() => {
    if (!creation) return;
    const available: string[] = [];
    if (creation.mockup_path) available.push(creation.mockup_path);
    if (creation.real_mockup_path) available.push(creation.real_mockup_path);
    if (creation.png_paths) {
      creation.png_paths.forEach(p => {
        if (!available.includes(p)) available.push(p);
      });
    }

        setSelectedImages(prev => {
          // Keep only images that are still available, excluding condition_dl.png  
          let updated = prev.filter(p => available.includes(p) && p !== "/assets/templates/condition_dl.png");
          available.forEach(p => {
            if (!updated.includes(p)) {
              updated.push(p);
            }
          });
          return [...updated, "/assets/templates/condition_dl.png"];
        });
  }, [creation?.mockup_path, creation?.real_mockup_path, creation?.png_paths?.join(","), creation?.source_png_path]);

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

  const getPipelineStatus = () => {
    if (!creation?.pipeline_status) return null;
    try {
      return typeof creation.pipeline_status === "string" 
        ? JSON.parse(creation.pipeline_status) 
        : creation.pipeline_status;
    } catch {
      return null;
    }
  };
  const pipelineStatus = getPipelineStatus();
  const visionDescription = pipelineStatus?.stencil?.vision_description || "";
  const dallePrompt = pipelineStatus?.stencil?.prompt || "";
  
  const accordionTagsFr = creation?.tags_fr ? (typeof creation.tags_fr === 'string' ? (creation.tags_fr as string).split(',') : creation.tags_fr) : [];
  const accordionTagsEn = creation?.tags_en ? (typeof creation.tags_en === 'string' ? (creation.tags_en as string).split(',') : creation.tags_en) : [];
  const tagsValue = accordionTagsFr.length > 0 || accordionTagsEn.length > 0 
    ? `Tags FR: ${accordionTagsFr.join(", ")}\n\nTags EN: ${accordionTagsEn.join(", ")}`
    : "";

  const sourcePath = creation?.source_png_path || "";
  const transparentPath = creation?.upscale_png_path || creation?.svg_path || "";

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
      
      setTheme(data.theme || "");
      setTitleFr(data.title_fr || "");
      setTitleEn(data.title_en || "");
      setDescription(data.description || "");
      setDescriptionEn(data.description_en || "");
      setTagsFrInput(data.tags_fr || "");
      setTagsEnInput(data.tags_en || "");
      setPrice(data.price ?? 3.0);
      setQuantity(data.quantity ?? 999);
      setBundleSize(data.bundle_size || 1);

      if (data.selected_images_raw) {
        const rawList = data.selected_images_raw.split(",").filter(Boolean);
        const clean = rawList.filter((p: string) => p !== data.source_png_path && p !== "/assets/templates/condition_dl.png");
        setSelectedImages([...clean, "/assets/templates/condition_dl.png"]);
      } else {
        const defaults: string[] = [];
        if (data.mockup_path) defaults.push(data.mockup_path);
        if (data.real_mockup_path) defaults.push(data.real_mockup_path);
        if (data.png_paths) {
          data.png_paths.forEach((p: string) => {
            if (!defaults.includes(p)) defaults.push(p);
          });
        }
        const clean = defaults.filter((p: string) => p !== data.source_png_path && p !== "/assets/templates/condition_dl.png");
        setSelectedImages([...clean, "/assets/templates/condition_dl.png"]);
      }
      
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
          selected_images_raw: selectedImages.join(","),
          bundle_size: bundleSize,
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

  const handleTranslateSeo = async () => {
    try {
      setTranslatingSeo(true);
      setNotification(null);
      const res = await fetch(apiUrl("/api/creations/translate-seo"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title_fr: titleFr,
          description_fr: description,
          tags_fr: getCleanTags(tagsFrInput),
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Échec de la traduction.");
      }
      const data = await res.json();
      setTitleEn(data.title_en || "");
      setDescriptionEn(data.description_en || "");
      setTagsEnInput(data.tags_en ? data.tags_en.join(", ") : "");
      setNotification({ type: "success", message: "Traduction et optimisation en anglais réussies !" });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setTranslatingSeo(false);
    }
  };

  const handleRegenerateImage = async () => {
    try {
      setRegeneratingImage(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-image`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instructions: imageInstructions,
          bundle_size: bundleSize,
          vectorize: shouldVectorize,
          theme: theme,
          n_images: nImages
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de régénérer l'image.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Image source régénérée avec succès." });
      setImageInstructions("");
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingImage(false);
    }
  };

  const handleRegenerateVector = async () => {
    try {
      setRegeneratingVector(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-vector`), {
        method: "POST"
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de régénérer le vecteur.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Vectorisation (SVG) relancée avec succès." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingVector(false);
    }
  };

  const handleRegenerateCad = async () => {
    try {
      setRegeneratingCad(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-cad`), {
        method: "POST"
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de régénérer les fichiers CAO.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Fichiers CAO (DXF, AI, EPS) régénérés avec succès." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingCad(false);
    }
  };

  const handleRegenerateUpscale = async () => {
    try {
      setRegeneratingUpscale(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-upscale`), {
        method: "POST"
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible d'upscaler l'image.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Image PNG Haute Résolution x3 régénérée." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingUpscale(false);
    }
  };

  const handleRegeneratePdf = async () => {
    try {
      setRegeneratingPdf(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-pdf`), {
        method: "POST"
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de régénérer le PDF.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Format PDF client régénéré." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingPdf(false);
    }
  };

  const handleRegenerateMockup = async () => {
    try {
      setRegeneratingMockup(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-mockup`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          instructions: mockupInstructions,
          apply_tp_overlay: applyTpOverlay
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de régénérer le mockup.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Mockup e-commerce régénéré avec succès." });
      setMockupInstructions("");
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingMockup(false);
    }
  };

  const handleRegenerateZip = async () => {
    try {
      setRegeneratingZip(true);
      setNotification(null);
      const res = await fetch(apiUrl(`/api/creations/${creationId}/regenerate-zip`), {
        method: "POST"
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Impossible de reconstruire le ZIP.");
      }
      const updated = await res.json();
      setCreation(updated);
      setNotification({ type: "success", message: "Package ZIP reconstruit avec succès." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setRegeneratingZip(false);
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
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_assets: selectedImages,
        }),
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
  if (activeModules.generate_real_mockup && !creation?.mockup_path) missingRequirements.push("Image Mockup (.PNG/.JPG) manquante");
  if (activeModules.package && !creation?.zip_path) missingRequirements.push("Fichier Client ZIP manquant");
  if (tooManyTagsFr) missingRequirements.push("Max 13 tags en Français (actuellement " + tagsFrArray.length + ")");
  if (tooManyTagsEn) missingRequirements.push("Max 13 tags en Anglais (actuellement " + tagsEnArray.length + ")");
  if (tagsFrTooLong) missingRequirements.push("Certains tags FR dépassent 20 caractères");
  if (tagsEnTooLong) missingRequirements.push("Certains tags EN dépassent 20 caractères");
  if (hasCriticalCompliance) missingRequirements.push("DANGER COPYRIGHT : Présence de marques déposées protégées (Disney, Marvel, Star Wars, Pokémon, Harry Potter, etc.)");

  const isPublishDisabled = missingRequirements.length > 0 || publishing || loading || isStreaming;

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

      {/* Bandeau de Progression SSE en Temps Réel */}
      {isStreaming && (
        <div className="bg-indigo-950/40 border border-indigo-500/20 p-5 rounded-2xl space-y-3 shadow-xl backdrop-blur-sm">
          <div className="flex justify-between items-center text-sm">
            <span className="font-bold text-indigo-300 flex items-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-indigo-400" />
              <span>Traitement en cours...</span>
            </span>
            <span className="font-semibold text-slate-500">{currentStepNum || 1} / 11 étapes</span>
          </div>
          <div className="w-full bg-slate-900 rounded-full h-2 border border-slate-800 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-full rounded-full transition-all duration-300 animate-pulse" 
              style={{ width: `${Math.min(100, Math.max(5, ((currentStepNum || 1) / 11) * 100))}%` }}
            ></div>
          </div>
          <p className="text-xs text-indigo-200/90 font-medium italic">{streamProgress}</p>
        </div>
      )}

      {/* Alerte rouge bloquante de copyright (Violation de propriété intellectuelle) */}
      {hasCriticalCompliance && (
        <div className="bg-rose-950/50 border border-rose-500/30 p-4 rounded-xl flex items-start space-x-3 text-rose-300 shadow-md">
          <AlertTriangle className="h-5.5 w-5.5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-extrabold uppercase tracking-wider">Publication Bloquée - Risque Majeur</h4>
            <p className="text-xs text-rose-200/90 leading-relaxed">
              Une marque commerciale protégée (ex: Disney, Marvel, Star Wars, Pokémon, Harry Potter, etc.) a été détectée dans le titre, la description ou les tags de cette création. Pour éviter la suspension définitive de votre boutique Etsy, vous devez impérativement retirer ces termes avant de pouvoir publier.
            </p>
            <div className="text-[10px] bg-rose-950/80 px-2.5 py-1 rounded border border-rose-500/10 font-mono inline-block mt-2">
              Termes interdits matchés : {complianceWarnings.filter(w => w.level === "CRITICAL").map(w => w.matched_term).filter(Boolean).join(", ") || "Marque Déposée"}
            </div>
          </div>
        </div>
      )}

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

      {reprocessing && (
        <div className="bg-indigo-950/40 border border-indigo-500/20 p-5 rounded-2xl space-y-3 shadow-xl backdrop-blur-sm">
          <div className="flex justify-between items-center text-sm">
            <span className="font-bold text-indigo-300 flex items-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-indigo-400" />
              <span>Régénération en cours (Mockups, ZIP, CAO)...</span>
            </span>
          </div>
        </div>
      )}

      {/* Variant Selection Gallery (Interactive) */}
      {creation && creation.source_png_variants && creation.source_png_variants.length > 1 && (
        <div className="glass-panel rounded-2xl p-5 border border-slate-800/60 text-left mb-6">
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-400" /> Variantes générées par l'IA (Sélectionnez la meilleure)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {creation.source_png_variants.map((variantPath, idx) => {
              const isSelected = creation.source_png_path === variantPath;
              return (
                <div
                  key={idx}
                  onClick={() => !isSelected && handleSelectVariant(variantPath)}
                  className={`relative rounded-xl overflow-hidden cursor-pointer border-2 transition group ${
                    isSelected
                      ? "border-indigo-500 shadow-lg shadow-indigo-500/10"
                      : "border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <img
                    src={assetUrl(variantPath)}
                    alt={`Variante ${idx + 1}`}
                    className="w-full aspect-square object-cover"
                  />
                  <div className="absolute top-1.5 left-1.5 bg-slate-950/80 px-2 py-0.5 rounded text-[10px] font-bold text-slate-300">
                    #{idx + 1}
                  </div>
                  {isSelected && (
                    <div className="absolute inset-0 bg-indigo-600/10 flex items-center justify-center">
                      <div className="bg-indigo-600 text-white p-1 rounded-full">
                        <Check className="h-4 w-4" />
                      </div>
                    </div>
                  )}
                  {!isSelected && selectingVariant && (
                    <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center">
                      <Loader2 className="h-5 w-5 text-white animate-spin" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Main split grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN: VISUALIZATIONS & DOWNLOADS */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            {/* Visual preview tabs */}
            <div className="flex bg-slate-950/50 border-b border-slate-900 p-1">
              {(creation.mockup_path || creation.real_mockup_path) && (
                <button
                  onClick={() => setPreviewTab("mockup")}
                  className={`flex-1 text-xs font-bold py-2 rounded-lg transition ${
                    previewTab === "mockup" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Mockups (Bois)
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
            <div className={`relative aspect-square w-full flex items-center justify-center p-4 transition-colors ${
              previewTab === "svg" || previewTab === "png" ? "bg-white rounded-2xl border border-slate-200" : "bg-slate-950/20"
            }`}>
              {previewTab === "mockup" && (creation.mockup_path || creation.real_mockup_path) && (
                <div className="grid grid-cols-2 gap-4 w-full h-full p-2">
                  {creation.mockup_path && (
                    <div className="flex flex-col items-center justify-between h-full bg-slate-900/10 p-2 rounded-xl border border-slate-800/40">
                      <div className="relative flex-1 w-full bg-slate-950/30 rounded-lg overflow-hidden flex items-center justify-center">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`${assetUrl(creation.mockup_path)}?t=${new Date().getTime()}`}
                          alt="Aperçu Brut"
                          className="object-contain max-h-full max-w-full"
                        />
                      </div>
                      <span className="text-[10px] sm:text-xs font-semibold text-slate-300 mt-2">Aperçu Brut</span>
                    </div>
                  )}
                  {creation.real_mockup_path && (
                    <div className="flex flex-col items-center justify-between h-full bg-slate-900/10 p-2 rounded-xl border border-slate-800/40">
                      <div className="relative flex-1 w-full bg-slate-950/30 rounded-lg overflow-hidden flex items-center justify-center">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`${assetUrl(creation.real_mockup_path)}?t=${new Date().getTime()}`}
                          alt="Aperçu Commercial"
                          className="object-contain max-h-full max-w-full"
                        />
                      </div>
                      <span className="text-[10px] sm:text-xs font-semibold text-slate-300 mt-2">Aperçu Commercial avec Cadre</span>
                    </div>
                  )}
                </div>
              )}
              {previewTab === "svg" && (creation.svg_paths && creation.svg_paths.length > 1 ? creation.svg_paths[activeElementIdx] : creation.svg_path) && (
                // SVG renders natively in img tag
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`${assetUrl(creation.svg_paths && creation.svg_paths.length > 1 ? creation.svg_paths[activeElementIdx] : creation.svg_path)}?t=${new Date().getTime()}`}
                  alt="SVG representation"
                  className="object-contain w-full h-full bg-white"
                />
              )}
              {previewTab === "png" && (creation.png_paths && creation.png_paths.length > 1 ? creation.png_paths[activeElementIdx] : creation.source_png_path) && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`${assetUrl(creation.png_paths && creation.png_paths.length > 1 ? creation.png_paths[activeElementIdx] : creation.source_png_path!)}?t=${new Date().getTime()}`}
                  alt="Original PNG"
                  className="object-contain w-full h-full bg-white"
                />
              )}
              
              {/* Element selector overlay */}
              {(previewTab === "svg" || previewTab === "png") && creation.svg_paths && creation.svg_paths.length > 1 && (
                <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center bg-slate-900/90 border border-slate-800 rounded-full px-3 py-1.5 shadow-lg max-w-[90%] overflow-x-auto space-x-1 scrollbar-none z-10">
                  {creation.svg_paths.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setActiveElementIdx(i)}
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-full transition whitespace-nowrap cursor-pointer ${
                        activeElementIdx === i
                          ? "bg-indigo-600 text-white"
                          : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                      }`}
                    >
                      Élément {i + 1}
                    </button>
                  ))}
                </div>
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
              {activeModules.package && creation.zip_path && (
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

              {creation.svg_paths && creation.svg_paths.length > 1 ? (
                <div className="space-y-4 pt-2">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Éléments individuels ({creation.svg_paths.length})
                  </h4>
                  {creation.svg_paths.map((svgPath, idx) => {
                    const svgFilename = svgPath.substring(svgPath.lastIndexOf("/") + 1);
                    const baseName = svgFilename.replace(".svg", "");
                    
                    return (
                      <div key={idx} className="border border-slate-800 rounded-xl p-3 bg-slate-950/40 space-y-2">
                        <div className="text-xs font-semibold text-indigo-400">
                          Élément #{idx + 1}: {baseName}
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          {activeModules.vectorize && (
                            <a
                              href={apiUrl(`/api/creations/${creation.id}/download/svg?filename=${baseName}.svg`)}
                              className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-800 text-slate-300 text-xs transition"
                            >
                              <span className="truncate">Vectoriel (SVG)</span>
                              <Download className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                            </a>
                          )}
                          {activeModules.convert_cad && (
                            <a
                              href={apiUrl(`/api/creations/${creation.id}/download/dxf?filename=${baseName}.dxf`)}
                              className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-805 text-slate-300 text-xs transition"
                            >
                              <span className="truncate">Découpe (DXF)</span>
                              <Download className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                            </a>
                          )}
                          {activeModules.format_pdf && (
                            <a
                              href={apiUrl(`/api/creations/${creation.id}/download/pdf?filename=${baseName}.pdf`)}
                              className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-805 text-slate-300 text-xs transition"
                            >
                              <span className="truncate">Impression (PDF)</span>
                              <Download className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                            </a>
                          )}
                          {activeModules.upscale && (
                            <a
                              href={apiUrl(`/api/creations/${creation.id}/download/png?filename=${baseName}.png`)}
                              className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-855 text-slate-300 text-xs transition"
                            >
                              <span className="truncate">Transparent (PNG)</span>
                              <Download className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <>
                  {activeModules.vectorize && creation.svg_path && (
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

                  {activeModules.convert_cad && creation.dxf_path && (
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

                  {activeModules.format_pdf && creation.pdf_path && (
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

                  {activeModules.upscale && creation.upscale_png_path && (
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
                </>
              )}

              {activeModules.generate_real_mockup && creation.mockup_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/mockup`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-slate-300 text-xs font-medium transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FileText className="h-4.5 w-4.5 text-slate-400" />
                    <span>Aperçu Mockup Brut (.JPG)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}

              {activeModules.generate_real_mockup && creation.real_mockup_path && (
                <a
                  href={apiUrl(`/api/creations/${creation.id}/download/real_mockup`)}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-slate-300 text-xs font-medium transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <FileText className="h-4.5 w-4.5 text-slate-400" />
                    <span>Aperçu Mockup Commercial avec Cadre (.JPG)</span>
                  </div>
                  <Download className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>

          {/* Regeneration Control Panel */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold border-b border-slate-800 pb-3 mb-2 text-indigo-300">
              Panneau de contrôle de régénération
            </h3>

            <div className="space-y-4 text-left">
              {/* Section 1 : Image Source */}
              <div className="space-y-3 p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    1. Image Source (IA)
                  </h4>
                  <button
                    onClick={handleRegenerateImage}
                    disabled={regeneratingImage}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-[11px] font-bold text-white transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <RefreshCw className={`h-3 w-3 ${regeneratingImage ? "animate-spin" : ""}`} />
                    <span>{regeneratingImage ? "Régénération..." : "Régénérer l'Image"}</span>
                  </button>
                </div>
                 <div className="space-y-1">
                  <label className="text-[10px] text-slate-400 font-semibold">
                    Thème du design (Prompt)
                  </label>
                  <input
                    type="text"
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                    placeholder="Thème ou sujet du motif..."
                    className="w-full text-xs glass-input px-3 py-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500/30"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] text-slate-400 font-semibold">
                    Consignes de retouche / correction (Facultatif)
                  </label>
                  <textarea
                    value={imageInstructions}
                    onChange={(e) => setImageInstructions(e.target.value)}
                    placeholder="Ex: Rendre les traits plus épais, enlever les petits points isolés, ajouter des étoiles..."
                    className="w-full text-xs glass-input px-3 py-2 rounded-lg h-16 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500/30"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-slate-400 font-semibold">
                      Nombre d'éléments
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={bundleSize}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        setBundleSize(val > 0 ? val : 1);
                      }}
                      className="w-full text-xs glass-input px-2 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500/30 text-center"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-slate-400 font-semibold">
                      Nombre d'images à générer
                    </label>
                    <select
                      value={nImages}
                      onChange={(e) => setNImages(parseInt(e.target.value, 10))}
                      className="w-full text-xs glass-input px-2 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500/30 text-center cursor-pointer"
                    >
                      <option value={1}>1 image</option>
                      <option value={2}>2 images</option>
                      <option value={3}>3 images</option>
                      <option value={4}>4 images</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center space-x-2 mt-3 pt-2.5 border-t border-slate-800/40">
                  <input
                    type="checkbox"
                    id="vectorize-toggle"
                    checked={shouldVectorize}
                    onChange={(e) => setShouldVectorize(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  />
                  <label htmlFor="vectorize-toggle" className="text-[10px] font-semibold text-slate-300 cursor-pointer select-none">
                    Vider le fond blanc (Rendre l'image transparente)
                  </label>
                </div>
              </div>

              {/* Section 2 : Vectorisation */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    2. Vectorisation (SVG)
                  </h4>
                  <p className="text-[10px] text-slate-400">Reconvertir l'image PNG en tracé vectoriel (Potrace).</p>
                </div>
                <button
                  onClick={handleRegenerateVector}
                  disabled={regeneratingVector}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-300 border border-slate-700/60 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <RefreshCw className={`h-3 w-3 ${regeneratingVector ? "animate-spin" : ""}`} />
                  <span>{regeneratingVector ? "Relancer..." : "Relancer"}</span>
                </button>
              </div>

              {/* Section 3 : Formats CAO */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    3. Formats CAO (DXF, AI, EPS)
                  </h4>
                  <p className="text-[10px] text-slate-400">Régénérer les fichiers industriels via Inkscape.</p>
                </div>
                <button
                  onClick={handleRegenerateCad}
                  disabled={regeneratingCad}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-300 border border-slate-700/60 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <RefreshCw className={`h-3 w-3 ${regeneratingCad ? "animate-spin" : ""}`} />
                  <span>{regeneratingCad ? "Relancer..." : "Relancer"}</span>
                </button>
              </div>

              {/* Section 4 : PNG Transparent HD */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    4. PNG Transparent (x3)
                  </h4>
                  <p className="text-[10px] text-slate-400">Régénérer le fichier PNG haute définition transparent.</p>
                </div>
                <button
                  onClick={handleRegenerateUpscale}
                  disabled={regeneratingUpscale}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-300 border border-slate-700/60 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <RefreshCw className={`h-3 w-3 ${regeneratingUpscale ? "animate-spin" : ""}`} />
                  <span>{regeneratingUpscale ? "Relancer..." : "Relancer"}</span>
                </button>
              </div>

              {/* Section 5 : PDF haute qualité */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    5. Format PDF client
                  </h4>
                  <p className="text-[10px] text-slate-400">Générer le PDF haute qualité pour l'impression.</p>
                </div>
                <button
                  onClick={handleRegeneratePdf}
                  disabled={regeneratingPdf}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-300 border border-slate-700/60 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <RefreshCw className={`h-3 w-3 ${regeneratingPdf ? "animate-spin" : ""}`} />
                  <span>{regeneratingPdf ? "Relancer..." : "Relancer"}</span>
                </button>
              </div>

              {/* Section 6 : Mockup E-Commerce */}
              <div className="space-y-2 p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    6. Mockup e-commerce
                  </h4>
                  <button
                    onClick={handleRegenerateMockup}
                    disabled={regeneratingMockup}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-[11px] font-bold text-white transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <RefreshCw className={`h-3 w-3 ${regeneratingMockup ? "animate-spin" : ""}`} />
                    <span>{regeneratingMockup ? "Régénération..." : "Régénérer"}</span>
                  </button>
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] text-slate-400 font-semibold">
                    Consignes d'arrière-plan / style (Si mockup IA activé)
                  </label>
                  <textarea
                    value={mockupInstructions}
                    onChange={(e) => setMockupInstructions(e.target.value)}
                    placeholder="Ex: Placer sur une étagère en bois foncé avec des plantes..."
                    className="w-full text-xs glass-input px-3 py-2 rounded-lg h-12 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500/30"
                  />
                </div>
                <div className="flex items-center space-x-2 pt-1">
                  <input
                    type="checkbox"
                    id="apply-tp-overlay-toggle"
                    checked={applyTpOverlay}
                    onChange={(e) => setApplyTpOverlay(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  />
                  <label htmlFor="apply-tp-overlay-toggle" className="text-[10px] font-semibold text-slate-300 cursor-pointer select-none">
                    Appliquer le template tp.png au premier plan (devant le design et l'arrière-plan)
                  </label>
                </div>
              </div>

              {/* Section 7 : Package ZIP */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                    7. Package client (.ZIP)
                  </h4>
                  <p className="text-[10px] text-slate-400">Reconstruire le fichier compressé avec tous les livrables.</p>
                </div>
                <button
                  onClick={handleRegenerateZip}
                  disabled={regeneratingZip}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 text-[11px] font-bold text-indigo-300 border border-indigo-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <RefreshCw className={`h-3 w-3 ${regeneratingZip ? "animate-spin" : ""}`} />
                  <span>{regeneratingZip ? "Reconstruire..." : "Reconstruire"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Collapsible Accordion section "📋 Mode Manuel & Balises de Fichiers" */}
          <div className="glass-panel rounded-2xl p-4 border border-slate-800/40 text-left mt-6">
            <button
              onClick={() => setAccordionOpen(!accordionOpen)}
              className="w-full flex items-center justify-between text-slate-300 hover:text-white font-bold text-sm transition py-1 cursor-pointer"
            >
              <span className="flex items-center gap-2">📋 Mode Manuel & Balises de Fichiers</span>
              {accordionOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            
            {accordionOpen && (
              <div className="space-y-3 mt-3 animate-in fade-in slide-in-from-top-2 duration-200">
                <CopyField
                  label="Texte Prompt Vision / Description"
                  value={visionDescription}
                />
                <CopyField
                  label="Prompt Final DALL-E"
                  value={dallePrompt}
                />
                <CopyField
                  label="Balises Tags Etsy Générées (FR/EN)"
                  value={tagsValue}
                />
                <CopyField
                  label="Chemin d'accès Stockage Asset Source"
                  value={sourcePath}
                />
                <CopyField
                  label="Chemin d'accès Stockage Asset Transparent"
                  value={transparentPath}
                />
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: SEO & METADATA FORM */}
        <div className="lg:col-span-7 space-y-6">
          <div className="glass-panel rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-bold border-b border-slate-900 pb-3">Optimisation SEO & Fiche Produit</h2>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleTranslateSeo}
                disabled={translatingSeo || regeneratingSeo}
                className="inline-flex items-center space-x-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Languages className={`h-3.5 w-3.5 ${translatingSeo ? "animate-spin" : ""}`} />
                <span>{translatingSeo ? "Traduction..." : "Traduire & Optimiser en Anglais"}</span>
              </button>
              <button
                type="button"
                onClick={handleRegenerateSeo}
                disabled={regeneratingSeo || translatingSeo}
                className="inline-flex items-center space-x-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${regeneratingSeo ? "animate-spin" : ""}`} />
                <span>{regeneratingSeo ? "Régénération..." : "Régénérer SEO bilingue"}</span>
              </button>
            </div>
            
            {/* French Title */}
            <div className="space-y-1.5 text-left">
              <div className="flex justify-between items-center text-xs">
                <div className="flex items-center space-x-2">
                  <label className="font-bold text-slate-300">Titre de la fiche en Français (Etsy FR)</label>
                  <button
                    type="button"
                    onClick={() => handleCopyText(titleFr, "titleFr")}
                    className="text-slate-500 hover:text-indigo-400 transition flex items-center cursor-pointer"
                    title="Copier le titre FR"
                  >
                    {copiedField === "titleFr" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  </button>
                </div>
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
                <div className="flex items-center space-x-2">
                  <label className="font-bold text-slate-300">Titre de la fiche en Anglais (Etsy EN)</label>
                  <button
                    type="button"
                    onClick={() => handleCopyText(titleEn, "titleEn")}
                    className="text-slate-500 hover:text-indigo-400 transition flex items-center cursor-pointer"
                    title="Copier le titre EN"
                  >
                    {copiedField === "titleEn" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  </button>
                </div>
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
              <div className="flex items-center space-x-2 text-xs">
                <label className="font-bold text-slate-300">Description FR (Etsy France)</label>
                <button
                  type="button"
                  onClick={() => handleCopyText(description, "description")}
                  className="text-slate-500 hover:text-indigo-400 transition flex items-center cursor-pointer"
                  title="Copier la description FR"
                >
                  {copiedField === "description" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                </button>
              </div>
              <textarea
                rows={8}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 text-xs glass-input font-mono leading-relaxed"
              />
            </div>

            {/* Description Textarea EN */}
            <div className="space-y-1.5 text-left">
              <div className="flex items-center space-x-2 text-xs">
                <label className="font-bold text-slate-300">Description EN (Etsy International — 80% du trafic)</label>
                <button
                  type="button"
                  onClick={() => handleCopyText(descriptionEn, "descriptionEn")}
                  className="text-slate-500 hover:text-indigo-400 transition flex items-center cursor-pointer"
                  title="Copier la description EN"
                >
                  {copiedField === "descriptionEn" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                </button>
              </div>
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
                <div className="flex items-center space-x-2">
                  <label className="font-bold text-slate-300">Tags en Français (Séparés par des virgules)</label>
                  <button
                    type="button"
                    onClick={() => handleCopyText(tagsFrInput, "tagsFrInput")}
                    className="text-slate-500 hover:text-indigo-400 transition flex items-center cursor-pointer"
                    title="Copier les tags FR"
                  >
                    {copiedField === "tagsFrInput" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  </button>
                </div>
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
                <div className="flex items-center space-x-2">
                  <label className="font-bold text-slate-300">Tags en Anglais (Séparés par des virgules)</label>
                  <button
                    type="button"
                    onClick={() => handleCopyText(tagsEnInput, "tagsEnInput")}
                    className="text-slate-500 hover:text-indigo-400 transition flex items-center cursor-pointer"
                    title="Copier les tags EN"
                  >
                    {copiedField === "tagsEnInput" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  </button>
                </div>
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

            {/* Rubrique Spéciale : Sélection des Photos Etsy */}
            <div className="pt-4 border-t border-slate-900 space-y-3 text-left">
              {(() => {
                // Exclude Stencil Master (source_png_path) from available images
                const available: { path: string; label: string; type: string }[] = [];
                if (creation.mockup_path) available.push({ path: creation.mockup_path, label: "Aperçu Brut", type: "mockup" });
                if (creation.real_mockup_path) available.push({ path: creation.real_mockup_path, label: "Aperçu Commercial avec Cadre", type: "mockup" });
                if (creation.png_paths) {
                  creation.png_paths.forEach((p, idx) => {
                    available.push({ path: p, label: `Élément PNG ${idx + 1}`, type: "split_element" });
                  });
                }

                const allSelected = available.length > 0 && available.every(img => selectedImages.includes(img.path));

                const handleToggleAll = () => {
                  if (allSelected) {
                    // Deselect all available
                    setSelectedImages(prev => prev.filter(p => !available.some(a => a.path === p)));
                  } else {
                    // Select all available while keeping others
                    setSelectedImages(prev => {
                      const existing = prev.filter(p => !available.some(a => a.path === p));
                      const toAdd = available.map(a => a.path);
                      return [...existing, ...toAdd];
                    });
                  }
                };

                return (
                  <>
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                          Photos de Présentation Etsy
                        </label>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          Sélectionnez les images à inclure dans la fiche Etsy et organisez-les dans l&apos;ordre souhaité.
                        </p>
                      </div>
                      {available.length > 0 && (
                        <button
                          type="button"
                          onClick={handleToggleAll}
                          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[10px] font-extrabold text-slate-300 hover:text-white border border-slate-700 transition cursor-pointer select-none"
                        >
                          {allSelected ? "Tout désélectionner" : "Tout sélectionner"}
                        </button>
                      )}
                    </div>

                    {available.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">Aucune image disponible.</p>
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2">
                        {available.map(({ path, label, type }) => {
                          const isSelected = selectedImages.includes(path);
                          const selectedIdx = selectedImages.indexOf(path);
                          
                          const handleToggleSelect = () => {
                            setSelectedImages(prev => {
                              if (prev.includes(path)) {
                                return prev.filter(p => p !== path);
                              } else {
                                return [...prev, path];
                              }
                            });
                          };

                          const handleMoveLeft = (e: React.MouseEvent) => {
                            e.stopPropagation();
                            if (selectedIdx <= 0) return;
                            setSelectedImages(prev => {
                              const next = [...prev];
                              const temp = next[selectedIdx - 1];
                              next[selectedIdx - 1] = next[selectedIdx];
                              next[selectedIdx] = temp;
                              return next;
                            });
                          };

                          const handleMoveRight = (e: React.MouseEvent) => {
                            e.stopPropagation();
                            if (selectedIdx === -1 || selectedIdx >= selectedImages.length - 1) return;
                            setSelectedImages(prev => {
                              const next = [...prev];
                              const temp = next[selectedIdx + 1];
                              next[selectedIdx + 1] = next[selectedIdx];
                              next[selectedIdx] = temp;
                              return next;
                            });
                          };

                          return (
                            <div
                              key={path}
                              onClick={handleToggleSelect}
                              className={`relative rounded-xl overflow-hidden border p-2.5 bg-slate-900/50 flex flex-col justify-between transition-all duration-300 cursor-pointer select-none ${
                                isSelected
                                  ? "border-indigo-500 ring-2 ring-indigo-500/20 bg-indigo-950/10"
                                  : "border-slate-800 hover:border-slate-700"
                              }`}
                            >
                              <div className={`relative aspect-square w-full rounded-lg overflow-hidden ${
                                  type === "split_element"
                                    ? "bg-white p-2 rounded-lg shadow-sm flex items-center justify-center border border-gray-100"
                                    : "bg-slate-950"
                                }`}>
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={`${assetUrl(path)}?t=${new Date().getTime()}`}
                                  alt={label}
                                  className={`${type === "split_element" ? "object-contain" : "object-cover"} w-full h-full`}
                                />
                                
                                {/* Visible aesthetic checkbox overlay */}
                                <div className={`absolute top-2 right-2 h-5 w-5 rounded-md border flex items-center justify-center transition-all duration-200 shadow-md ${
                                  isSelected 
                                    ? "bg-indigo-600 border-indigo-400 text-white" 
                                    : "bg-black/60 border-slate-500 text-transparent"
                                }`}>
                                  <Check className="h-3.5 w-3.5 stroke-[3]" />
                                </div>

                                {isSelected && (
                                  <div className="absolute top-2 left-2 h-5.5 w-5.5 rounded-full bg-indigo-650 border border-indigo-400 text-white flex items-center justify-center text-[10px] font-black shadow-md">
                                    {selectedIdx + 1}
                                  </div>
                                )}
                              </div>
                              <div className="mt-2.5 flex flex-col gap-1.5">
                                <div className="text-[10px] font-bold text-slate-300 truncate">{label}</div>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleOpenWorkspace(path, type);
                                  }}
                                  className="w-full py-1.5 bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 hover:text-white font-extrabold text-[9px] uppercase tracking-wider rounded transition cursor-pointer"
                                >
                                  Retoucher
                                </button>
                                {isSelected && (
                                  <div className="flex items-center justify-between mt-1 pt-1 border-t border-slate-800">
                                    <button
                                      type="button"
                                      disabled={selectedIdx === 0}
                                      onClick={handleMoveLeft}
                                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[10px] font-bold cursor-pointer"
                                    >
                                      ◀
                                    </button>
                                    <span className="text-[9px] text-slate-500 font-bold">Ordre</span>
                                    <button
                                      type="button"
                                      disabled={selectedIdx === selectedImages.length - 1}
                                      onClick={handleMoveRight}
                                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[10px] font-bold cursor-pointer"
                                    >
                                      ▶
                                    </button>
                                  </div>
                                )}
                                {/* Delete button for all deletable images */}
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteImage(path, type);
                                  }}
                                  className="w-full py-1 bg-rose-600/20 hover:bg-rose-600 text-rose-200 hover:text-white font-extrabold text-[9px] uppercase tracking-wider rounded transition cursor-pointer flex items-center justify-center gap-1"
                                >
                                  <Trash className="h-3 w-3" />
                                  <span>Supprimer</span>
                                </button>
                              </div>
                            </div>
                          );
                        })}
                        
                        {/* condition_dl.png - always shown as last image, always selected, not deletable */}
                        <div
                          className="relative rounded-xl overflow-hidden border p-2.5 bg-slate-900/50 flex flex-col justify-between border-indigo-500 ring-2 ring-indigo-500/20 cursor-default select-none"
                        >
                          <div className="relative aspect-square w-full rounded-lg overflow-hidden bg-slate-950">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={`${assetUrl("/assets/templates/condition_dl.png")}?t=${new Date().getTime()}`}
                              alt="Condition de téléchargement"
                              className="object-cover w-full h-full"
                            />
                            
                            <div className="absolute top-2 right-2 h-5 w-5 rounded-md bg-indigo-650 border border-indigo-400 text-white flex items-center justify-center shadow-md">
                              <Check className="h-3.5 w-3.5 stroke-[3]" />
                            </div>

                            <div className="absolute top-2 left-2 h-5.5 w-5.5 rounded-full bg-indigo-650 border border-indigo-400 text-white flex items-center justify-center text-[10px] font-black shadow-md">
                              {selectedImages.length + 1}
                            </div>
                          </div>
                          <div className="mt-2.5 flex flex-col gap-1.5">
                            <div className="text-[10px] font-bold text-slate-300 truncate">Condition de téléchargement</div>
                            <div className="w-full py-1.5 bg-emerald-600/30 text-emerald-200 font-extrabold text-[9px] uppercase tracking-wider rounded flex items-center justify-center gap-1">
                              <Lock className="h-3 w-3" />
                              <span>Obligatoire</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                );
              })()}
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

      {isRetouchModalOpen && activeAssetPath && (
        <RetouchModal
          isOpen={isRetouchModalOpen}
          creationId={Number(creationId)}
          imageUrl={assetUrl(activeAssetPath)}
          assetPath={activeAssetPath}
          assetType={activeAssetType || "master_stencil"}
          onClose={() => {
            setIsRetouchModalOpen(false);
            setActiveAssetPath(null);
            setActiveAssetType(null);
          }}
          onValidate={handleRetouchValidate}
        />
      )}
      </div>
    </div>
  );
}

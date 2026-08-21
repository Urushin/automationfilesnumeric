"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Layers,
  ArrowRight,
  Play,
  CheckSquare,
  Square,
  AlertCircle,
  CheckCircle2,
  Image as ImageIcon,
  FileCode,
  FileText,
  FolderArchive,
  Tag as TagIcon,
  Wand2,
  Loader2,
  ChevronRight,
  X,
  ChevronDown,
  ChevronUp,
  Check,
} from "lucide-react";
import FileUpload from "@/components/FileUpload";
import PipelineForm from "@/components/PipelineForm";
import RetouchModal from "@/components/RetouchModal";
import LiveStreamPanel from "@/components/LiveStreamPanel";
import { apiUrl, assetUrl } from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────
interface PipelineStep {
  id: number;
  msg: string;
  status: "pending" | "active" | "complete" | "error";
}

interface LiveData {
  creation_id:      number | null;
  source_png_path:  string | null;
  svg_path:         string | null;
  dxf_path:         string | null;
  ai_path:          string | null;
  eps_path:         string | null;
  pdf_path:         string | null;
  upscale_png_path: string | null;
  mockup_path:      string | null;
  zip_path:         string | null;
  title_fr:         string | null;
  title_en:         string | null;
  description:      string | null;
  description_en:   string | null;
  tags_fr:          string[];
  tags_en:          string[];
  vision_description?: string | null;
  dalle_prompt?:       string | null;
}

const EMPTY_DATA: LiveData = {
  creation_id:      null,
  source_png_path:  null,
  svg_path:         null,
  dxf_path:         null,
  ai_path:          null,
  eps_path:         null,
  pdf_path:         null,
  upscale_png_path: null,
  mockup_path:      null,
  zip_path:         null,
  title_fr:         null,
  title_en:         null,
  description:      null,
  description_en:   null,
  tags_fr:          [],
  tags_en:          [],
  vision_description: null,
  dalle_prompt:       null,
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────────────
export default function CreationPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"global" | "modular">("global");
  const [mounted, setMounted] = useState(false);

  // ── Global Mode state ──────────────────────────────────────────────────────
  const [globalTheme, setGlobalTheme] = useState("");
  const [accordionOpen, setAccordionOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Read ?theme= query param (client-side only — avoids useSearchParams/Suspense issues)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("theme");
    if (t) {
      setGlobalTheme(decodeURIComponent(t));
      setActiveTab("global");
    }
  }, []);

  // ── Modular Mode state ─────────────────────────────────────────────────────
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [modularTheme, setModularTheme] = useState("");
  const [tasks, setTasks] = useState({
    vectorize:      true,
    convert_cad:    true,
    format_pdf:     true,
    upscale:        true,
    generate_real_mockup: true,
    package:        true,
    generate_seo:   true,
  });

  // ── Streaming state ────────────────────────────────────────────────────────
  const [streaming, setStreaming] = useState(false);
  const [done, setDone]           = useState(false);
  const [error, setError]         = useState<string | null>(null);
  // Steps are dynamically populated from SSE events (only active tasks shown)
  const [steps, setSteps]         = useState<PipelineStep[]>([]);
  const [liveData, setLiveData]   = useState<LiveData>(EMPTY_DATA);
  const stepCounterRef             = useRef(0);
  const esRef = useRef<EventSource | null>(null);
  const isSubmittingRef = useRef(false);

  // ── Quality Gate states ───────────────────────────────────────────────────
  const [pipelineStep, setPipelineStep] = useState<"idle" | "stencil_gen" | "quality_gate" | "downstream">("idle");
  const [isRetouchModalOpen, setIsRetouchModalOpen] = useState(false);
  const [pendingDownstreamParams, setPendingDownstreamParams] = useState<any>(null);
  const [activeStreamUrl, setActiveStreamUrl] = useState<string | null>(null);

  // Recovery SSE: check localStorage for pending creation at mount
  useEffect(() => {
    const pendingId = localStorage.getItem("pending_creation_id");
    if (pendingId) {
      // A creation was left pending — show banner
      // The user can click to go to review page
    }
  }, []);

  // Close EventSource on unmount
  useEffect(() => () => esRef.current?.close(), []);

  const toggleTask = (key: keyof typeof tasks) =>
    setTasks(prev => ({ ...prev, [key]: !prev[key] }));

  // ── SSE handler ────────────────────────────────────────────────────────────
  // Refs to avoid stale closures in onerror callback
  const doneRef = useRef(false);
  const errorRef = useRef<string | null>(null);

  const connectSSE = useCallback((url: string, isStep1: boolean = false) => {
    esRef.current?.close();
    setStreaming(true);
    setDone(false);
    doneRef.current = false;
    setError(null);
    errorRef.current = null;
    setLiveData(EMPTY_DATA);
    setSteps([]);           // Start empty — steps appear dynamically as SSE events fire
    stepCounterRef.current = 0;

    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener("status", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setSteps(prev => {
        // Check if step already exists (update) or add new
        const exists = prev.find(s => s.id === d.step);
        if (exists) {
          return prev.map(s =>
            s.id === d.step
              ? { ...s, msg: d.msg, status: d.status === "complete" ? "complete" : "active" }
              : s.id < d.step
              ? { ...s, status: "complete" }
              : s
          );
        }
        // New step: add it
        const newStep: PipelineStep = {
          id: d.step,
          msg: d.msg,
          status: d.status === "complete" ? "complete" : "active",
        };
        return [...prev, newStep];
      });
    });

    es.addEventListener("created", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({ ...prev, creation_id: d.creation_id }));
      // Store creation_id in localStorage for recovery if page is refreshed
      localStorage.setItem("pending_creation_id", String(d.creation_id));
      localStorage.setItem("pending_creation_time", new Date().toISOString());
    });

    es.addEventListener("image_ready", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({
        ...prev,
        source_png_path: d.source_png_path,
        vision_description: d.vision_description || prev.vision_description,
        dalle_prompt: d.prompt || prev.dalle_prompt
      }));
      setActiveStreamUrl(null);
    });

    es.addEventListener("vector_ready", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({ ...prev, svg_path: d.svg_path }));
    });

    es.addEventListener("assets_ready", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({
        ...prev,
        ...(d.dxf_path         && { dxf_path: d.dxf_path }),
        ...(d.ai_path          && { ai_path: d.ai_path }),
        ...(d.eps_path         && { eps_path: d.eps_path }),
        ...(d.pdf_path         && { pdf_path: d.pdf_path }),
        ...(d.upscale_png_path && { upscale_png_path: d.upscale_png_path }),
        ...(d.zip_path         && { zip_path: d.zip_path }),
      }));
    });

    es.addEventListener("mockup_ready", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({
        ...prev,
        mockup_path: d.mockup_path,
        mockup_paths: d.mockup_paths,
        real_mockup_path: d.real_mockup_path,
        real_mockup_paths: d.real_mockup_paths,
      }));
    });

    es.addEventListener("seo_ready", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({
        ...prev,
        title_fr:       d.title_fr    || prev.title_fr,
        title_en:       d.title_en    || prev.title_en,
        description:    d.description || prev.description,
        description_en: d.description_en || prev.description_en,
        tags_fr:        Array.isArray(d.tags_fr) ? d.tags_fr : prev.tags_fr,
        tags_en:        Array.isArray(d.tags_en) ? d.tags_en : prev.tags_en,
      }));
    });

    es.addEventListener("done", (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setLiveData(prev => ({ ...prev, creation_id: d.creation_id ?? prev.creation_id }));
      es.close();
      setActiveStreamUrl(null);
      if (isStep1) {
        setStreaming(false);
        setPipelineStep("quality_gate");
        setIsRetouchModalOpen(true);
        doneRef.current = true;
      } else {
        setDone(true);
        doneRef.current = true;
        setStreaming(false);
        setSteps(prev => prev.map(s => ({ ...s, status: "complete" })));
      }
    });

    es.addEventListener("error", (e: MessageEvent) => {
      let msg = "Erreur inconnue du pipeline.";
      try {
        const d = JSON.parse((e as any).data);
        msg = d.msg || msg;
        setError(msg);
      } catch {
        setError("Connexion SSE interrompue.");
      }
      setStreaming(false);
      setActiveStreamUrl(null);
      errorRef.current = msg;
      es.close();
    });

    // Handle EventSource errors with a small delay to avoid false positives
    es.onerror = () => {
      // Use refs to read current values (avoids stale closure)
      if (!doneRef.current && !errorRef.current) {
        setTimeout(() => {
          if (!doneRef.current && !errorRef.current && esRef.current?.readyState !== EventSource.OPEN) {
            setError("Connexion au backend perdue. Vérifiez que le serveur est démarré.");
            setStreaming(false);
            setActiveStreamUrl(null);
            es.close();
          }
        }, 2000);
      }
    };
  }, []);  // No deps — refs are always current

  // ── Backend health check helper ────────────────────────────────────────────
  const checkBackendHealth = async (): Promise<boolean> => {
    try {
      const res = await fetch(apiUrl("/"), { signal: AbortSignal.timeout(5000) });
      return res.ok;
    } catch {
      return false;
    }
  };

  // ── Global submit ──────────────────────────────────────────────────────────
  const handleGlobalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!globalTheme.trim() || isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    
    // Check backend health first
    const backendUp = await checkBackendHealth();
    if (!backendUp) {
      setError("Impossible de contacter le backend. Vérifiez que le serveur est démarré (python run.py dans le dossier backend/).");
      isSubmittingRef.current = false;
      return;
    }
    
    setError(null);
    setStreaming(true);
    setDone(false);
    setLiveData(EMPTY_DATA);
    setPipelineStep("stencil_gen");

    const fd = new FormData();
    fd.append("theme", globalTheme);
    fd.append("bundle_size", "4");
    fd.append("design_style", "classic");
    fd.append("source_type", "text_prompt");
    fd.append("output_assembled", "true");
    fd.append("output_split", "false");
    fd.append("strict_fidelity", "true");

    let creationId: number;
    try {
      const res = await fetch(apiUrl("/api/pipeline/upload"), { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload échoué.");
      const data = await res.json();
      creationId = data.id;
      setLiveData(prev => ({
        ...prev,
        creation_id: creationId,
        source_png_path: data.source_png_path,
      }));
    } catch (err: any) {
      setError(err.message);
      setStreaming(false);
      isSubmittingRef.current = false;
      return;
    }

    setPendingDownstreamParams({
      theme:                globalTheme,
      vectorize:            true,
      convert_cad:          true,
      format_pdf:           true,
      upscale:              true,
      generate_real_mockup: true,
      use_ai_mockup:        true,
      apply_tp_overlay:     true,
      package:              true,
      generate_seo:         true,
      design_style:         "classic",
      source_type:          "text_prompt",
      output_assembled:     true,
      output_split:         false,
      strict_fidelity:      true,
      n_images:             1,
      mockup_styles:        ["classic_living_room"]
    });

    const params = new URLSearchParams({
      creation_id:          String(creationId),
      theme:                globalTheme,
      generate_ai_stencil:  "true",
      vectorize:            "false",
      convert_cad:          "false",
      format_pdf:           "false",
      upscale:              "false",
      generate_real_mockup: "false",
      use_ai_mockup:        "false",
      package:              "false",
      generate_seo:         "false",
      design_style:         "classic",
      source_type:          "text_prompt",
      output_assembled:     "true",
      output_split:         "false",
      strict_fidelity:      "true"
    });

    setActiveStreamUrl(apiUrl(`/api/pipeline/stream/image?prompt=${encodeURIComponent(globalTheme)}`));
    connectSSE(apiUrl(`/api/pipeline/stream/modular?${params.toString()}&_t=${Date.now()}`), true);
    isSubmittingRef.current = false;
  };

  // ── Modular submit ─────────────────────────────────────────────────────────
  const handleModularSubmit = async (formPayload: any) => {
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;

    const {
      files: formFiles,
      theme: formTheme,
      bundleSize: formBundleSize,
      designStyle: formDesignStyle,
      sourceType: formSourceType,
      sourceIsMultiElement: formSourceIsMultiElement,
      outputAssembled: formOutputAssembled,
      outputSplit: formOutputSplit,
      strictFidelity: formStrictFidelity,
      nImages: formNImages,
      options: formOptions,
    } = formPayload;

    setError(null);
    setStreaming(true);
    setDone(false);
    setLiveData(EMPTY_DATA);
    setPipelineStep("stencil_gen");

    // Check backend health first
    const backendUp = await checkBackendHealth();
    if (!backendUp) {
      setError("Impossible de contacter le backend. Vérifiez que le serveur est démarré (python run.py dans le dossier backend/).");
      setStreaming(false);
      isSubmittingRef.current = false;
      return;
    }

    // 1. Upload files first
    const fd = new FormData();
    formFiles.forEach((f: File) => fd.append("files", f));
    fd.append("theme", formTheme || "Fichier Importé");
    fd.append("bundle_size", formBundleSize.toString());
    fd.append("design_style", formDesignStyle);
    fd.append("source_type", formSourceType);
    fd.append("source_is_multi_element", formSourceIsMultiElement);
    fd.append("output_assembled", formOutputAssembled ? "true" : "false");
    fd.append("output_split", formOutputSplit ? "true" : "false");
    fd.append("strict_fidelity", formStrictFidelity ? "true" : "false");

    let creationId: number;
    try {
      const res = await fetch(apiUrl("/api/pipeline/upload"), { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload échoué.");
      const data = await res.json();
      creationId = data.id;
      setLiveData(prev => ({
        ...prev,
        creation_id: creationId,
        source_png_path: data.source_png_path,
      }));
    } catch (err: any) {
      setError(err.message);
      setStreaming(false);
      isSubmittingRef.current = false;
      return;
    }

     // 2. Save pending modular parameters
    setPendingDownstreamParams({
      theme:                formTheme || "",
      vectorize:            formOptions.removeWhiteBackground || formOptions.vectorize,
      convert_cad:          formOptions.convert_cad,
      format_pdf:           formOptions.format_pdf,
      upscale:              formOptions.upscale,
      generate_real_mockup: formOptions.generate_real_mockup,
      use_ai_mockup:        formOptions.generate_real_mockup,
      apply_tp_overlay:     formOptions.apply_tp_overlay,
      package:              formOptions.package,
      generate_seo:         formOptions.generate_seo,
      design_style:         formDesignStyle,
      source_type:          formSourceType,
      output_assembled:     formOutputAssembled,
      output_split:         formOutputSplit,
      strict_fidelity:      formStrictFidelity,
      n_images:             formNImages || 1,
      mockup_styles:        formPayload.mockupStyles || ["classic_living_room"],
      apply_binarization:   formOptions.apply_binarization !== false,
    });

    // 3. Connect to modular SSE stream for Step 1
    const isAiGen = formSourceType === "text_prompt" || formSourceType === "raw_image";
    const params = new URLSearchParams({
      creation_id:          String(creationId),
      theme:                formTheme || "",
      generate_ai_stencil:  isAiGen ? "true" : "false",
      vectorize:            "false",
      convert_cad:          "false",
      format_pdf:           "false",
      upscale:              "false",
      generate_real_mockup: "false",
      use_ai_mockup:        "false",
      apply_tp_overlay:     "false",
      package:              "false",
      generate_seo:         "false",
      design_style:         formDesignStyle,
      source_type:          formSourceType,
      output_assembled:     String(formOutputAssembled),
      output_split:         String(formOutputSplit),
      strict_fidelity:      String(formStrictFidelity),
      n_images:             String(formNImages || 1),
      mockup_styles:        JSON.stringify(formPayload.mockupStyles || ["classic_living_room"]),
      apply_binarization:   String(formOptions.apply_binarization !== false)
    });

    if (isAiGen) {
      setActiveStreamUrl(apiUrl(`/api/pipeline/stream/image?prompt=${encodeURIComponent(formTheme || "Fichier Importé")}`));
    }
    connectSSE(apiUrl(`/api/pipeline/stream/modular?${params.toString()}&_t=${Date.now()}`), true);
    isSubmittingRef.current = false;
  };

  const resumePipelineAfterValidation = async () => {
    if (!liveData.creation_id || !pendingDownstreamParams) return;
    
    setIsRetouchModalOpen(false);
    setPipelineStep("downstream");
    setStreaming(true);

    const params = new URLSearchParams({
      creation_id:          String(liveData.creation_id),
      theme:                pendingDownstreamParams.theme || "",
      generate_ai_stencil:  "false",
      vectorize:            String(pendingDownstreamParams.vectorize),
      convert_cad:          String(pendingDownstreamParams.convert_cad),
      format_pdf:           String(pendingDownstreamParams.format_pdf),
      upscale:              String(pendingDownstreamParams.upscale),
      generate_real_mockup: String(pendingDownstreamParams.generate_real_mockup),
      use_ai_mockup:        String(pendingDownstreamParams.use_ai_mockup),
      apply_tp_overlay:     String(pendingDownstreamParams.apply_tp_overlay),
      package:              String(pendingDownstreamParams.package),
      generate_seo:         String(pendingDownstreamParams.generate_seo),
      design_style:         pendingDownstreamParams.design_style || "classic",
      source_type:          pendingDownstreamParams.source_type || "text_prompt",
      output_assembled:     String(pendingDownstreamParams.output_assembled),
      output_split:         String(pendingDownstreamParams.output_split),
      strict_fidelity:      String(pendingDownstreamParams.strict_fidelity),
      n_images:             String(pendingDownstreamParams.n_images || 1),
      mockup_styles:        JSON.stringify(pendingDownstreamParams.mockup_styles || ["classic_living_room"]),
      apply_binarization:   String(pendingDownstreamParams.apply_binarization !== false)
    });

    connectSSE(apiUrl(`/api/pipeline/stream/modular?${params.toString()}&_t=${Date.now()}`), false);
  };

  const isGlobalDisabled  = !globalTheme.trim() || streaming;

  // ── Etsy publish guardrail ─────────────────────────────────────────────────
  const canPublish = !!(
    liveData.title_fr?.trim() && liveData.title_fr.length <= 140 &&
    liveData.title_en?.trim() && liveData.title_en.length <= 140 &&
    liveData.description?.trim() &&
    liveData.description_en?.trim() &&
    liveData.tags_fr.length > 0 &&
    liveData.tags_en.length > 0 &&
    liveData.mockup_path &&
    liveData.zip_path
  );

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-6xl space-y-8 py-6">

      {/* ── Header ────────────────────────────────────────────────────────── */}

      <div className="text-center space-y-3">
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 via-indigo-200 to-rose-200 bg-clip-text text-transparent sm:text-5xl">
          Générateur Fichier Laser
        </h1>
        <p className="mx-auto max-w-2xl text-slate-400 text-sm leading-relaxed">
          Vectorisation, copywriting SEO & publication Etsy automatisée.
          Chaque étape s&apos;affiche en temps réel dès qu&apos;elle est prête.
        </p>
      </div>

      {/* ── Tab switcher ──────────────────────────────────────────────────── */}
      {!streaming && !done && (
        <div className="flex justify-center">
          <div className="glass-panel flex rounded-xl p-1 bg-slate-900/60 border border-slate-800">
            {(["global", "modular"] as const).map(tab => (
              <button
                key={tab}
                onClick={() => { setActiveTab(tab); setError(null); }}
                className={`flex items-center space-x-2 rounded-lg px-6 py-2.5 text-sm font-semibold transition-all duration-200 ${
                  activeTab === tab
                    ? "bg-indigo-600 text-white shadow-md"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab === "global" ? <Sparkles className="h-4 w-4" /> : <Layers className="h-4 w-4" />}
                <span>{tab === "global" ? "Mode Automatique (Global)" : "Mode Modulaire (À la carte)"}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Error Banner ──────────────────────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 text-rose-300 border border-rose-500/20 flex items-start space-x-3 max-w-3xl mx-auto">
          <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <span className="font-bold">Erreur pipeline : </span>{error}
          </div>
          <button onClick={() => { setError(null); setStreaming(false); setDone(false); }} className="text-xs font-bold hover:underline">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          FORMS (visible only when not streaming/done)
      ══════════════════════════════════════════════════════════════════════ */}
      {!streaming && !done && (
        <div className="mx-auto max-w-xl">

          {activeTab === "global" ? (
            /* MODE A */
            <form onSubmit={handleGlobalSubmit} className="glass-panel rounded-2xl p-6 space-y-6">
              <div className="space-y-2 text-left">
                <label className="text-sm font-bold text-slate-200">Thème / Idée du motif</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Silhouette de tête de cerf géométrique style mandala"
                  value={globalTheme}
                  onChange={e => setGlobalTheme(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-sm glass-input placeholder:text-slate-600"
                />
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Notre système injecte des contraintes strictes à DALL-E 3 HD pour un pochoir sans îles flottantes,
                  optimal pour la découpe laser bois ou acrylique.
                </p>
              </div>
              <button
                type="submit"
                disabled={!mounted ? false : isGlobalDisabled}
                className="glow-btn w-full flex items-center justify-center space-x-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white py-3.5 font-bold transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Wand2 className="h-4 w-4" />
                <span>Lancer la création complète</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </form>
          ) : (
            <div className="w-full text-left">
              <PipelineForm
                onGenerate={handleModularSubmit}
                loading={streaming}
                initialTheme={modularTheme}
              />
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          STREAMING LIVE VIEW
      ══════════════════════════════════════════════════════════════════════ */}
      {(streaming || done) && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-in fade-in duration-500">

          {/* LEFT: Step progress sidebar */}
          <div className="lg:col-span-4 space-y-4">
            <div className="glass-panel rounded-2xl p-5 space-y-3">
              <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                {streaming
                  ? <><Loader2 className="h-4 w-4 text-indigo-400 animate-spin" /><span>Pipeline en cours...</span></>
                  : <><CheckCircle2 className="h-4 w-4 text-emerald-400" /><span>Pipeline terminé !</span></>}
              </h2>

              <div className="space-y-2">
                {steps.map(step => (
                  <div
                    key={step.id}
                    className={`flex items-center space-x-3 p-2.5 rounded-xl text-xs font-medium transition-all duration-300 ${
                      step.status === "complete" ? "bg-emerald-950/30 border border-emerald-500/20 text-emerald-300" :
                      step.status === "active"   ? "bg-indigo-950/50 border border-indigo-500/30 text-indigo-200" :
                      step.status === "error"    ? "bg-rose-950/30 border border-rose-500/20 text-rose-300" :
                      "bg-slate-900/30 border border-slate-800/40 text-slate-600"
                    }`}
                  >
                    <span className="flex-shrink-0">
                      {step.status === "complete" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                      {step.status === "active"   && <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />}
                      {step.status === "pending"  && <div className="h-4 w-4 rounded-full border-2 border-slate-700" />}
                      {step.status === "error"    && <AlertCircle className="h-4 w-4 text-rose-400" />}
                    </span>
                    <span className="truncate">{step.msg}</span>
                  </div>
                ))}
              </div>

              {/* Navigate to review */}
              {done && liveData.creation_id && (
                <button
                  onClick={() => router.push(`/review/${liveData.creation_id}`)}
                  className="glow-btn mt-2 w-full flex items-center justify-center space-x-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white py-3 font-bold text-sm transition"
                >
                  <span>Réviser & Publier sur Etsy</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}

              {/* Reset */}
              {(done || error) && (
                <button
                  onClick={() => { setStreaming(false); setDone(false); setError(null); setLiveData(EMPTY_DATA); }}
                  className="w-full text-xs text-slate-500 hover:text-slate-300 pt-1 transition"
                >
                  ← Nouvelle création
                </button>
              )}
            </div>

            {/* Etsy publish readiness */}
            {done && (
              <div className={`glass-panel rounded-2xl p-4 border ${canPublish ? "border-emerald-500/20 bg-emerald-950/20" : "border-slate-800/40"}`}>
                <p className={`text-xs font-bold uppercase tracking-wider mb-2 ${canPublish ? "text-emerald-400" : "text-slate-500"}`}>
                  {canPublish ? "✓ Prêt à publier sur Etsy" : "Conditions manquantes"}
                </p>
                <ul className="space-y-1 text-[11px]">
                  {[
                    { label: "Titre FR (≤140)", ok: !!(liveData.title_fr && liveData.title_fr.length <= 140) },
                    { label: "Titre EN (≤140)", ok: !!(liveData.title_en && liveData.title_en.length <= 140) },
                    { label: "Description FR",  ok: !!liveData.description },
                    { label: "Description EN",  ok: !!liveData.description_en },
                    { label: "Tags FR",         ok: liveData.tags_fr.length > 0 },
                    { label: "Tags EN",         ok: liveData.tags_en.length > 0 },
                    { label: "Image Mockup",    ok: !!liveData.mockup_path },
                    { label: "Package ZIP",     ok: !!liveData.zip_path },
                  ].map(({ label, ok }) => (
                    <li key={label} className={`flex items-center space-x-1.5 ${ok ? "text-emerald-400" : "text-slate-600"}`}>
                      {ok ? <CheckCircle2 className="h-3 w-3" /> : <div className="h-3 w-3 rounded-full border border-slate-700" />}
                      <span>{label}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Collapsible Accordion section "📋 Mode Manuel & Balises de Fichiers" */}
            <div className="glass-panel rounded-2xl p-4 border border-slate-800/40 text-left">
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
                    value={liveData.vision_description || ''}
                  />
                  <CopyField
                    label="Prompt Final DALL-E 3"
                    value={liveData.dalle_prompt || ''}
                  />
                  <CopyField
                    label="Balises Tags Etsy Générées (FR/EN)"
                    value={liveData.tags_fr.length > 0 || liveData.tags_en.length > 0 
                      ? `Tags FR: ${liveData.tags_fr.join(", ")}\n\nTags EN: ${liveData.tags_en.join(", ")}`
                      : ''
                    }
                  />
                  <CopyField
                    label="Chemin d'accès Stockage Asset Source"
                    value={liveData.source_png_path || ''}
                  />
                  <CopyField
                    label="Chemin d'accès Stockage Asset Transparent"
                    value={liveData.upscale_png_path || liveData.svg_path || ''}
                  />
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Live result panels */}
          <div className="lg:col-span-8 space-y-4">

            {/* Source image & mockup (side by side when both exist) */}
            {(liveData.source_png_path || liveData.mockup_path) && (
              <div className={`grid gap-4 ${liveData.source_png_path && liveData.mockup_path ? "grid-cols-2" : "grid-cols-1"}`}>
                {liveData.source_png_path && (
                  <ResultPanel
                    icon={<ImageIcon className="h-4 w-4 text-slate-400" />}
                    title="Motif Stencil (DALL-E 3)"
                    badge="PNG"
                    badgeColor="slate"
                    fresh={!liveData.mockup_path}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`${assetUrl(liveData.source_png_path)}?t=${Date.now()}`}
                      alt="Source stencil"
                      className="w-full h-full object-contain rounded-lg"
                    />
                  </ResultPanel>
                )}

                {liveData.mockup_path && (
                  <ResultPanel
                    icon={<ImageIcon className="h-4 w-4 text-indigo-400" />}
                    title="Mockup E-commerce"
                    badge="JPEG"
                    badgeColor="indigo"
                    fresh={true}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`${assetUrl(liveData.mockup_path)}?t=${Date.now()}`}
                      alt="Mockup e-commerce"
                      className="w-full h-full object-cover rounded-lg"
                    />
                  </ResultPanel>
                )}
              </div>
            )}

            {/* SVG preview */}
            {liveData.svg_path && (
              <ResultPanel
                icon={<FileCode className="h-4 w-4 text-amber-400" />}
                title="Vectoriel (SVG)"
                badge="SVG"
                badgeColor="amber"
                fresh={!liveData.dxf_path}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={assetUrl(liveData.svg_path)}
                  alt="SVG vector preview"
                  className="w-full h-40 object-contain bg-white/5 rounded-lg"
                />
              </ResultPanel>
            )}

            {/* Generated files download links */}
            {(liveData.dxf_path || liveData.pdf_path || liveData.upscale_png_path || liveData.zip_path) && (
              <div className="glass-panel rounded-2xl p-5 space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Fichiers générés</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {liveData.zip_path && (
                    <DownloadLink
                      href={apiUrl(`/api/creations/${liveData.creation_id}/download/zip`)}
                      label="Package Client (.ZIP)"
                      icon={<FolderArchive className="h-4 w-4 text-indigo-400" />}
                      primary
                    />
                  )}
                  {liveData.dxf_path && (
                    <DownloadLink
                      href={apiUrl(`/api/creations/${liveData.creation_id}/download/dxf`)}
                      label="Fichier CAO (.DXF)"
                      icon={<FileCode className="h-4 w-4 text-slate-400" />}
                    />
                  )}
                  {liveData.pdf_path && (
                    <DownloadLink
                      href={apiUrl(`/api/creations/${liveData.creation_id}/download/pdf`)}
                      label="Impression (.PDF)"
                      icon={<FileText className="h-4 w-4 text-slate-400" />}
                    />
                  )}
                  {liveData.upscale_png_path && (
                    <DownloadLink
                      href={apiUrl(`/api/creations/${liveData.creation_id}/download/png`)}
                      label="Transparent x3 (.PNG)"
                      icon={<ImageIcon className="h-4 w-4 text-slate-400" />}
                    />
                  )}
                </div>
              </div>
            )}

            {/* SEO preview */}
            {(liveData.title_fr || liveData.tags_fr.length > 0) && (
              <div className="glass-panel rounded-2xl p-5 space-y-4 animate-in fade-in duration-500">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                  <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                  <span>SEO Etsy généré (Gemini 1.5 Flash)</span>
                </h3>

                {liveData.title_fr && (
                  <SEOField label="Titre FR" value={liveData.title_fr} maxLen={140} />
                )}
                {liveData.title_en && (
                  <SEOField label="Titre EN" value={liveData.title_en} maxLen={140} />
                )}
                {liveData.description && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold text-slate-500 uppercase">Description FR</p>
                    <p className="text-xs text-slate-300 leading-relaxed line-clamp-4 bg-slate-900/40 rounded-lg p-3 font-mono whitespace-pre-wrap">
                      {liveData.description}
                    </p>
                  </div>
                )}
                {liveData.description_en && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold text-slate-500 uppercase">Description EN</p>
                    <p className="text-xs text-slate-300 leading-relaxed line-clamp-4 bg-slate-900/40 rounded-lg p-3 font-mono whitespace-pre-wrap">
                      {liveData.description_en}
                    </p>
                  </div>
                )}
                {liveData.tags_fr.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-[10px] font-bold text-slate-500 uppercase">Tags ({liveData.tags_fr.length}/13)</p>
                    <div className="flex flex-wrap gap-1.5">
                      {liveData.tags_fr.map((tag, i) => (
                        <span key={i} className="inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-md bg-slate-900 text-slate-300 border border-slate-800">
                          <TagIcon className="h-2.5 w-2.5 opacity-60" />
                          <span>{tag}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {liveData.tags_en.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-[10px] font-bold text-slate-500 uppercase">Tags EN ({liveData.tags_en.length}/13)</p>
                    <div className="flex flex-wrap gap-1.5">
                      {liveData.tags_en.map((tag, i) => (
                        <span key={i} className="inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-md bg-slate-900 text-slate-300 border border-slate-800">
                          <TagIcon className="h-2.5 w-2.5 opacity-60" />
                          <span>{tag}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {liveData.creation_id && liveData.source_png_path && (
        <RetouchModal
          isOpen={isRetouchModalOpen}
          creationId={liveData.creation_id}
          imageUrl={assetUrl(liveData.source_png_path)}
          onClose={() => {
            setIsRetouchModalOpen(false);
            setStreaming(false);
            setPipelineStep("idle");
          }}
          onValidate={resumePipelineAfterValidation}
        />
      )}

      {activeStreamUrl && (
        <LiveStreamPanel 
          streamUrl={activeStreamUrl} 
          onStreamComplete={() => setActiveStreamUrl(null)} 
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

function ResultPanel({
  icon, title, badge, badgeColor, fresh, children,
}: {
  icon: React.ReactNode;
  title: string;
  badge: string;
  badgeColor: "slate" | "indigo" | "amber" | "emerald";
  fresh: boolean;
  children: React.ReactNode;
}) {
  const badgeStyles = {
    slate:   "bg-slate-800 text-slate-400 border-slate-700",
    indigo:  "bg-indigo-950/60 text-indigo-300 border-indigo-500/30",
    amber:   "bg-amber-950/60 text-amber-300 border-amber-500/30",
    emerald: "bg-emerald-950/60 text-emerald-300 border-emerald-500/30",
  };

  return (
    <div className={`glass-panel rounded-2xl overflow-hidden border ${fresh ? "border-indigo-500/30 shadow-lg shadow-indigo-500/10" : "border-slate-800/60"} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-900/80 bg-slate-950/40">
        <div className="flex items-center space-x-2">
          {icon}
          <span className="text-xs font-bold text-slate-300">{title}</span>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${badgeStyles[badgeColor]}`}>
          {badge}
        </span>
      </div>
      <div className="p-3 aspect-video flex items-center justify-center">
        {children}
      </div>
    </div>
  );
}

function DownloadLink({
  href, label, icon, primary = false,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  primary?: boolean;
}) {
  return (
    <a
      href={href}
      download
      className={`flex items-center justify-between p-3 rounded-xl border text-xs font-semibold transition ${
        primary
          ? "bg-indigo-600/15 hover:bg-indigo-600/25 border-indigo-500/30 text-indigo-300"
          : "bg-slate-900/40 hover:bg-slate-900/80 border-slate-800 text-slate-300"
      }`}
    >
      <div className="flex items-center space-x-2">
        {icon}
        <span>{label}</span>
      </div>
      <ArrowRight className="h-3.5 w-3.5 opacity-60" />
    </a>
  );
}

function SEOField({ label, value, maxLen }: { label: string; value: string; maxLen: number }) {
  const over = value.length > maxLen;
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-[10px]">
        <span className="font-bold text-slate-500 uppercase">{label}</span>
        <span className={`font-semibold ${over ? "text-rose-400" : "text-slate-600"}`}>
          {value.length} / {maxLen}
        </span>
      </div>
      <p className={`text-xs px-3 py-2 rounded-lg ${over ? "bg-rose-950/30 text-rose-300 border border-rose-500/20" : "bg-slate-900/40 text-slate-200"}`}>
        {value}
      </p>
    </div>
  );
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
    <div className="flex flex-col gap-1.5 bg-slate-950/40 p-3 rounded-xl border border-slate-800/55 text-left">
      <div className="flex justify-between items-center">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</span>
        <button
          onClick={handleCopy}
          disabled={!value}
          className="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">Copié!</span>
            </>
          ) : (
            <span>Copier</span>
          )}
        </button>
      </div>
      <textarea
        readOnly
        value={value || "En attente de génération..."}
        className="w-full bg-transparent text-xs text-slate-300 outline-none resize-none font-mono mt-1"
        rows={value && value.length > 80 ? 3 : 1}
      />
    </div>
  );
}

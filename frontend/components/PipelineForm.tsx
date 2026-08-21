"use client";

import React, { useState, useEffect } from "react";
import FileUpload from "./FileUpload";
import { Sparkles, Loader2, Image as ImageIcon, Sliders, CheckSquare, Square, Settings, Copy, Check } from "lucide-react";
import { apiUrl } from "@/lib/api";

interface PipelineFormProps {
  onGenerate: (data: {
    files: File[];
    theme: string;
    bundleSize: number;
    designStyle: string;
    sourceType: string;
    sourceIsMultiElement: string;
    outputAssembled: boolean;
    outputSplit: boolean;
    strictFidelity: boolean;
    nImages: number;
    options: {
      generate_ai_stencil: boolean;
      vectorize: boolean;
      convert_cad: boolean;
      format_pdf: boolean;
      upscale: boolean;
      package: boolean;
      generate_seo: boolean;
      use_ai_mockup: boolean;
      generate_real_mockup: boolean;
      removeWhiteBackground: boolean;
      apply_tp_overlay: boolean;
      apply_watermark?: boolean;
    };
    mockupStyles?: string[];
  }) => void;
  loading: boolean;
  initialTheme?: string;
  injected?: boolean;
  renderSourcingGratuitSection?: () => React.ReactNode;
}

export default function PipelineForm({
  onGenerate,
  loading,
  initialTheme = "",
  injected = false,
  renderSourcingGratuitSection,
}: PipelineFormProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [theme, setTheme] = useState(initialTheme);
  const [sourceCondition, setSourceCondition] = useState<"raw_image" | "ready_bw_image" | "transparent_png" | "vector_svg">("raw_image");
  const [sourceIsMultiElement, setSourceIsMultiElement] = useState<"single" | "multi">("single");
  const [bundleSize, setBundleSize] = useState(1);
  const [designStyle, setDesignStyle] = useState("classic");
  const [outputAssembled, setOutputAssembled] = useState(true);
  const [outputSplit, setOutputSplit] = useState(false);
  const [strictFidelity, setStrictFidelity] = useState(true);
  const [mockupStyles, setMockupStyles] = useState<string[]>(["classic_living_room"]);
  const [nImages, setNImages] = useState(1);

  const [options, setOptions] = useState({
    generate_ai_stencil: false,
    vectorize: false,
    convert_cad: false,
    format_pdf: false,
    upscale: false,
    package: false,
    generate_seo: false,
    use_ai_mockup: false,
    generate_real_mockup: false,
    removeWhiteBackground: false,
    apply_tp_overlay: false,
    apply_watermark: false,
    apply_binarization: true,
  });


  const [promptsList, setPromptsList] = useState<any[]>([]);
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (initialTheme) {
      setTheme(initialTheme);
    }
  }, [initialTheme]);

  useEffect(() => {
    fetch(apiUrl("/api/settings/prompts"))
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setPromptsList(data);
        }
      })
      .catch((err) => console.error("Error loading prompts:", err));
  }, []);



  const toggleOption = (key: keyof typeof options) => {
    setOptions((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      return next;
    });
  };

  const handleCopyPrompt = (e: React.MouseEvent, type: "stencil" | "mockup" | "seo") => {
    e.stopPropagation();
    let promptText = "";

    if (type === "stencil") {
      const isMulti = bundleSize > 1;
      const targetId = isMulti ? "stencil_multiple" : "stencil_single";
      const basePromptObj = promptsList.find((p) => p.id === targetId);

      let basePrompt = basePromptObj?.prompt || (isMulti
        ? "An organized flash-sheet collection grid containing exactly {bundle_size} distinct, disconnected variations of: {theme}. Pure solid black #000000 shapes on pristine flat solid white #FFFFFF background. Clean vector-like silhouette stencils, precise outlines, disconnected by wide white spacing, no gradients, no shadings, no text, no gray tones."
        : "A professional 2D flat vector silhouette stencil of {theme}. Pure solid black #000000 shapes on a pristine solid white background #FFFFFF, clean lines, high contrast, minimalist, no shading, no gradient, no text.");

      promptText = basePrompt
        .replace(/\{theme\}/gi, theme || "design")
        .replace(/\{bundle_size\}/gi, String(bundleSize));

      if (designStyle === "framed_filigree") {
        const filigreePromptObj = promptsList.find((p) => p.id === "stencil_framed_filigree");
        const filigreeTemplate = filigreePromptObj?.prompt || "Generate a strictly square image. Intricate stencil silhouette art based on: {final_prompt}. Circular or square borders decorated with ornate mandala style vector filigree frames. Perfect symmetry, solid black shape on clean white background, high-resolution vector style.";
        promptText = filigreeTemplate.replace(/\{final_prompt\}/gi, promptText);
      }
    } else if (type === "mockup") {
      const prompts = mockupStyles.map((style) => {
        let styleSelection = "";
        if (style === "angled_interior") {
          styleSelection = "The scene is a high-end modern living room or industrial loft with a solid concrete and wooden wall viewed from an elegant angled 3D perspective. The input design is crafted as a physical, premium laser-cut matte black metal wall art sculpture. It is mounted directly onto the inclined wall, casting soft, realistic, and deep 3D drop shadows onto the surface behind it, perfectly matching the room's ambient architectural lighting.";
        } else if (style === "tshirt_apparel") {
          styleSelection = "The scene is a clean studio fashion photography mockup featuring a premium heavy-cotton blank t-shirt layout. The input design is cleanly printed directly onto the center chest of the fabric using solid black matte ink. The printed graphics must completely conform to the surface of the garment, following every realistic fabric fold, crease, soft shadow, and textile texture flawlessly.";
        } else if (style === "frame_poster") {
          styleSelection = "The scene is a minimal minimalist aesthetic setup where the input design is presented as a high-contrast printed art piece inside a sleek black wooden frame. The frame is leaning casually against an angled wall next to a textured concrete floor or wooden table. Soft shadows and realistic cinematic lighting sweep across the frame, highlighting the texture of the paper and the depth of the frame edges.";
        } else {
          const styleMap: Record<string, string> = {
            classic_living_room: "A professional product photography of a modern luxury living room, elegant sofa, warm ambient light, with a large blank concrete wall in the center.",
            modern_bedroom: "A professional product photography of a minimalist Scandinavian bedroom, cozy linen bedding, warm wooden side table, with a large blank plaster wall in the center.",
            industrial_loft: "A professional product photography of a spacious industrial loft, brick wall, steel accents, large windows, with a large blank dark brick wall in the center.",
            scandinavian_office: "A professional product photography of a Scandinavian design home office, minimalist light wood desk, plants, with a large blank white wall in the center.",
            boho_chic: "A professional product photography of a cozy bohemian living room, rattan furniture, warm textiles, pampas grass, with a large blank beige wall in the center.",
            industrial: "A professional product photography of a modern industrial room, concrete walls, dark metal accents, warm spotlighting, with a large flat empty concrete wall in the center.",
            luxury_wood: "A professional product photography of a luxury room interior, premium warm rustic oak wooden panels on the wall, elegant high-end styling, with a large flat empty wooden wall in the center.",
            modern_plaster: "A professional product photography of a minimalist modern room, high-end matte plaster textured wall, soft natural side lighting, with a large flat empty plaster wall in the center."
          };
          const orig = styleMap[style] || style;
          styleSelection = `The scene is ${orig.replace('with a large blank concrete wall in the center.', '').replace('with a large blank plaster wall in the center.', '').replace('with a large blank dark brick wall in the center.', '').replace('with a large blank white wall in the center.', '').replace('with a large blank beige wall in the center.', '').replace('with a large flat empty concrete wall in the center.', '').replace('with a large flat empty wooden wall in the center.', '').replace('with a large flat empty plaster wall in the center.', '')}. The input design is crafted as a physical, premium laser-cut matte black metal wall art sculpture mounted on the wall.`;
        }

        return `Photo of a professional e-commerce product mockup showcasing the input design seamlessly integrated into a real-world setting. \n\n${styleSelection}\n\nStrict Constraints:\n- The input design must retain its exact core shapes, contours, and geometry without any modification, distortion of its pattern, or addition of internal elements.\n- The product must be perfectly embedded into the scene, realistically interacting with the lighting, background depth, and surface orientation.`;
      });
      promptText = prompts.join("\n\n──────────────────────────────────────────────────\n\n");
    } else if (type === "seo") {
      const basePromptObj = promptsList.find((p) => p.id === "seo");
      let basePrompt = basePromptObj?.prompt || `You are an elite Etsy SEO copywriter and conversion specialist...`;
      promptText = basePrompt
        .replace(/\[bundle\s*size\]/gi, String(bundleSize))
        .replace(/\[bundle_size\]/gi, String(bundleSize))
        .replace(/\[thème\]/gi, theme || "design")
        .replace(/\[theme\]/gi, theme || "design")
        .replace(/\{theme\}/gi, theme || "design")
        .replace(/\{bundle_size\}/gi, String(bundleSize));
    }

    if (promptText) {
      navigator.clipboard.writeText(promptText).then(() => {
        setCopiedStates((prev) => ({ ...prev, [type]: true }));
        setTimeout(() => {
          setCopiedStates((prev) => ({ ...prev, [type]: false }));
        }, 2000);
      });
    }
  };

  const handleFilesSelect = (selectedFiles: File[]) => {
    if (selectedFiles.length === 0) {
      setFiles([]);
      return;
    }

    // Format Validation: Enforce that all uploaded files share the identical mime-type/extension format
    const firstExt = selectedFiles[0].name.split(".").pop()?.toLowerCase();
    const allSame = selectedFiles.every((f) => f.name.split(".").pop()?.toLowerCase() === firstExt);

    if (!allSame) {
      alert("Erreur : Le mélange d'extensions est interdit. Tous les fichiers doivent posséder la même extension.");
      return;
    }

    setFiles(selectedFiles);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) {
      alert("Veuillez sélectionner au moins un fichier image ou vectoriel à traiter.");
      return;
    }
    if (!outputAssembled && !outputSplit) {
      alert("Vous devez cocher au moins une option de sortie (Pack Assemblé ou Pack Divisé).");
      return;
    }

    onGenerate({
      files,
      theme,
      bundleSize,
      designStyle,
      sourceType: sourceCondition,
      sourceIsMultiElement,
      outputAssembled,
      outputSplit,
      strictFidelity,
      nImages,
      options,
      mockupStyles,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8 bg-slate-900/40 p-8 rounded-2xl border border-slate-800/60 shadow-xl backdrop-blur-sm">


      <div className="flex flex-col gap-3">
        <label className="font-semibold text-slate-200 flex items-center gap-2">
          <ImageIcon className="h-5 w-5 text-indigo-400" /> Fichier(s) source(s) à traiter <span className="text-rose-400">*</span>
        </label>
        <FileUpload
          onFileSelect={() => {}}
          onFilesSelect={handleFilesSelect}
          multiple={true}
        />
      </div>

      {/* Source Image Condition Dropdown */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-semibold text-slate-300">Condition de l'image / fichier source</label>
        <select
          value={sourceCondition}
          onChange={(e) => setSourceCondition(e.target.value as any)}
          className="p-3 bg-slate-800 text-white rounded-lg border border-slate-700 outline-none focus:border-indigo-500 transition text-sm cursor-pointer"
        >
          <option value="raw_image">Image brute (Nécessite détourage & seuillage)</option>
          <option value="ready_bw_image">Image Noir & Blanc Propre (Nécessite transparence)</option>
          <option value="transparent_png">Image PNG transparente (Prête à vectoriser)</option>
          <option value="vector_svg">Fichier vectoriel SVG (Prêt pour mockup / SEO)</option>
        </select>
      </div>

      {/* Contenu du lot toggle - only if Noir & Blanc Propre or Transparent PNG or Vector SVG */}
      {(sourceCondition === "ready_bw_image" || sourceCondition === "transparent_png" || sourceCondition === "vector_svg") && (
        <div className="flex flex-col gap-2 p-4 bg-slate-950/20 rounded-xl border border-slate-800/40">
          <label className="text-sm font-semibold text-slate-300">Contenu du lot</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="radio"
                name="sourceIsMultiElement"
                checked={sourceIsMultiElement === "single"}
                onChange={() => setSourceIsMultiElement("single")}
                className="accent-indigo-600"
              />
              Un seul élément par fichier
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="radio"
                name="sourceIsMultiElement"
                checked={sourceIsMultiElement === "multi"}
                onChange={() => setSourceIsMultiElement("multi")}
                className="accent-indigo-600"
              />
              Plusieurs éléments par fichier
            </label>
          </div>
        </div>
      )}

      {/* Style & Bundle Size */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-950/20 p-4 rounded-xl border border-slate-800/40">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-semibold text-slate-300">Style de Design</label>
          <select
            value={designStyle}
            onChange={(e) => setDesignStyle(e.target.value)}
            className="p-3 bg-slate-800 text-white rounded-lg border border-slate-700 outline-none focus:border-indigo-500 transition text-sm cursor-pointer"
          >
            <option value="classic">Silhouette Classique (Lot)</option>
            <option value="framed_filigree">Filigrane Encadré (Style Dragon/Arbre)</option>
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-sm font-semibold text-slate-300">Nombre d'éléments à extraire (Illimité)</label>
          <input
            type="number"
            min={1}
            step={1}
            value={bundleSize}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              setBundleSize(val > 0 ? val : 1);
            }}
            className="p-3 bg-slate-800 text-white rounded-lg border border-slate-700 outline-none focus:border-indigo-500 transition text-sm"
          />
        </div>
      </div>

      {/* Output Packing Options (Checkboxes) */}
      <div className="flex flex-col gap-2 p-4 bg-slate-950/20 rounded-xl border border-slate-800/40">
        <label className="text-sm font-semibold text-slate-300">Options de sortie</label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={outputAssembled}
              onChange={() => setOutputAssembled(!outputAssembled)}
              className="accent-indigo-600"
            />
            Pack Assemblé (Tous les éléments sur un seul fichier)
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={outputSplit}
              onChange={() => setOutputSplit(!outputSplit)}
              className="accent-indigo-600"
            />
            Pack Divisé (Un fichier unique par élément)
          </label>
        </div>
      </div>

      {/* AI Generation Options (Image Variation Toggle & Quantity) */}
      <div className="flex flex-col gap-4 p-4 bg-slate-950/20 rounded-xl border border-slate-800/40">
        <div>
          <label className="text-sm font-semibold text-slate-300">Options de génération IA (Variation)</label>
          <div className="flex gap-4 mt-2">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="radio"
                name="strictFidelity"
                checked={strictFidelity}
                onChange={() => setStrictFidelity(true)}
                className="accent-indigo-600"
              />
              Générer un élément identique/fidèle à la source
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="radio"
                name="strictFidelity"
                checked={!strictFidelity}
                onChange={() => setStrictFidelity(false)}
                className="accent-indigo-600"
              />
              Générer un élément différent/nouvelle variante inspirée
            </label>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <label className="font-semibold text-slate-200">Thème du design (Optionnel)</label>
        <input
          type="text"
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          placeholder="Recommandé pour la génération de mots-clés & SEO..."
          className="p-4 bg-slate-800 text-white rounded-xl border border-slate-700 outline-none focus:border-indigo-500 transition"
        />
      </div>

      {renderSourcingGratuitSection && renderSourcingGratuitSection()}

      {/* Advanced pipeline step configurations */}
      <div className="border-t border-slate-800 pt-6 space-y-6">
        <h3 className="text-lg font-bold text-slate-200 mb-2 flex items-center gap-2">
          <Settings className="text-indigo-400 h-5 w-5" /> Configurer les étapes du pipeline
        </h3>

        {/* Step 1: Prep & AI Stencil */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Étape 1 : Préparation & Transformation (IA)
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition">
              <button
                type="button"
                onClick={() => toggleOption("generate_ai_stencil")}
                className="flex items-center gap-3 text-left flex-1"
              >
                {options.generate_ai_stencil ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
                <div>
                  <div className="font-bold text-sm text-slate-200">Transformation IA (Stencil Img2Img)</div>
                  <div className="text-xs text-slate-400">Améliore le dessin fourni via IA avant traitement</div>
                </div>
              </button>
              
              <button
                type="button"
                onClick={(e) => handleCopyPrompt(e, "stencil")}
                className="ml-4 p-2 bg-slate-800 hover:bg-slate-750 active:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-705 transition flex items-center gap-1.5 text-xs font-semibold cursor-pointer select-none"
                title="Copier le prompt adapté"
              >
                {copiedStates.stencil ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-[10px] text-emerald-400 font-bold">Copié !</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span className="text-[10px] font-bold">Copier le prompt</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-4 my-4 p-3 bg-slate-800/20 rounded-xl border border-slate-800/40 text-left">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="remove-bg-toggle"
                checked={options.removeWhiteBackground}
                onChange={() => toggleOption("removeWhiteBackground")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
              />
              <label htmlFor="remove-bg-toggle" className="text-xs font-semibold text-slate-300 cursor-pointer select-none">
                Supprimer l'arrière-plan blanc (Rendre transparent)
              </label>
            </div>
            
            <div className="flex items-center space-x-2 sm:border-l sm:border-slate-800 sm:pl-4">
              <input
                type="checkbox"
                id="apply-binarization-toggle"
                checked={options.apply_binarization}
                onChange={() => toggleOption("apply_binarization")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
              />
              <label htmlFor="apply-binarization-toggle" className="text-xs font-semibold text-slate-300 cursor-pointer select-none">
                Activer le lissage & seuillage (Binarisation)
              </label>
            </div>
          </div>
        </div>

        {/* Step 2: Vectorisation & CAD */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Étape 2 : Vectorisation & Formats CAO
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => toggleOption("vectorize")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.vectorize ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Vectoriser (Potrace)</div>
                <div className="text-xs text-slate-400">Génère le tracé vectoriel SVG</div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => toggleOption("convert_cad")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.convert_cad ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Générer les formats CAO (.dxf, .ai, .eps)</div>
                <div className="text-xs text-slate-400">Génère les tracés pour la découpe CNC et Illustrator</div>
              </div>
            </button>
          </div>
        </div>

        {/* Step 3: HQ Client Exports */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Étape 3 : Exports Client Haute Définition
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => toggleOption("upscale")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.upscale ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Upscaler PNG (Haute Définition ×3)</div>
                <div className="text-xs text-slate-400">Export client final sans flou</div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => toggleOption("format_pdf")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.format_pdf ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Générer PDF Vectoriel</div>
                <div className="text-xs text-slate-400">Garantit la compatibilité universelle d'impression</div>
              </div>
            </button>
          </div>
        </div>

        {/* Step 4: Marketing & Packaging */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Étape 4 : Marketing, SEO & Packaging
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition">
              <button
                type="button"
                onClick={() => toggleOption("generate_real_mockup")}
                className="flex items-center gap-3 text-left flex-1"
              >
                {options.generate_real_mockup ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
                <div>
                  <div className="font-bold text-sm text-slate-200">Générer le Mockup 3D par IA</div>
                  <div className="text-xs text-slate-400">Génère des images de mise en scène 3D réalistes par IA</div>
                </div>
              </button>
              
              <button
                type="button"
                onClick={(e) => handleCopyPrompt(e, "mockup")}
                className="ml-4 p-2 bg-slate-800 hover:bg-slate-750 active:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-705 transition flex items-center gap-1.5 text-xs font-semibold cursor-pointer select-none"
                title="Copier le prompt adapté"
              >
                {copiedStates.mockup ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-[10px] text-emerald-400 font-bold">Copié !</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span className="text-[10px] font-bold">Copier le prompt</span>
                  </>
                )}
              </button>
            </div>
            <button
              type="button"
              onClick={() => toggleOption("apply_tp_overlay")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.apply_tp_overlay ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Appliquer le Template (tp.png)</div>
                <div className="text-xs text-slate-400">Applique l'overlay tp.png devant le design et le fond</div>
              </div>
            </button>

            {options.generate_real_mockup && (
              <div className="md:col-span-2 p-5 bg-slate-950/40 rounded-2xl border border-slate-800 space-y-4 text-left animate-in fade-in duration-200">
                <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-4 gap-4">
                  <div>
                    <h5 className="text-sm font-bold text-slate-200">Styles & Quantité de Mockups (1-10)</h5>
                    <p className="text-[11px] text-slate-400">Définissez la quantité de mockups et choisissez leur style</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-slate-400">Quantité :</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={mockupStyles.length}
                      onChange={(e) => {
                        const val = Math.min(10, Math.max(1, parseInt(e.target.value, 10) || 1));
                        const next = [...mockupStyles];
                        if (val > next.length) {
                          while (next.length < val) {
                            next.push("classic_living_room");
                          }
                        } else {
                          next.splice(val);
                        }
                        setMockupStyles(next);
                      }}
                      className="w-16 p-2 bg-slate-800 text-white rounded-lg border border-slate-700 outline-none text-xs text-center font-bold"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {mockupStyles.map((style, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
                      <span className="text-xs font-bold text-slate-400 w-8 font-mono">#{idx + 1}</span>
                      <select
                        value={style}
                        onChange={(e) => {
                          const next = [...mockupStyles];
                          next[idx] = e.target.value;
                          setMockupStyles(next);
                        }}
                        className="flex-1 p-2 bg-slate-800 text-white rounded-lg border border-slate-700 outline-none text-xs cursor-pointer focus:border-indigo-500"
                      >
                        <option value="classic_living_room">Salon Classique</option>
                        <option value="modern_bedroom">Chambre Moderne</option>
                        <option value="industrial_loft">Loft Industriel</option>
                        <option value="scandinavian_office">Bureau Scandinave</option>
                        <option value="boho_chic">Salon Boho Chic</option>
                        <option value="industrial">Industriel (Industrial)</option>
                        <option value="luxury_wood">Bois Luxueux (Luxury Wood)</option>
                        <option value="modern_plaster">Plâtre Moderne (Modern Plaster)</option>
                        <option value="angled_interior">Mur Incliné / Décoration d'Intérieur (Loft)</option>
                        <option value="tshirt_apparel">T-Shirt / Vêtement porté</option>
                        <option value="frame_poster">Cadre Photo / Poster sur Table ou Sol</option>
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition">
              <button
                type="button"
                onClick={() => toggleOption("generate_seo")}
                className="flex items-center gap-3 text-left flex-1"
              >
                {options.generate_seo ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
                <div>
                  <div className="font-bold text-sm text-slate-200">Générer le SEO (Etsy)</div>
                  <div className="text-xs text-slate-400">Titres, descriptions et tags optimisés pour la boutique</div>
                </div>
              </button>
              
              <button
                type="button"
                onClick={(e) => handleCopyPrompt(e, "seo")}
                className="ml-4 p-2 bg-slate-800 hover:bg-slate-750 active:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-705 transition flex items-center gap-1.5 text-xs font-semibold cursor-pointer select-none"
                title="Copier le prompt adapté"
              >
                {copiedStates.seo ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-[10px] text-emerald-400 font-bold">Copié !</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span className="text-[10px] font-bold">Copier le prompt</span>
                  </>
                )}
              </button>
            </div>
            <button
              type="button"
              onClick={() => toggleOption("package")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.package ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Packager l'archive ZIP client</div>
                <div className="text-xs text-slate-400">Regroupe tous les formats générés en un fichier ZIP final</div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => toggleOption("apply_watermark")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.apply_watermark ? <CheckSquare className="text-emerald-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Filigrane Anti-Vol (Aperçus Etsy)</div>
                <div className="text-xs text-slate-400">Applique le nom de boutique semi-transparent pour protéger les visuels</div>
              </div>
            </button>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-4.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-all shadow-md cursor-pointer"
      >
        {loading ? <Loader2 className="animate-spin h-6 w-6" /> : <Sparkles className="h-6 w-6" />}
        {loading ? "Génération modulaire en cours..." : "Lancer le Traitement Modulaire"}
      </button>
    </form>
  );
}

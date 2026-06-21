"use client";

import React, { useState, useEffect } from "react";
import FileUpload from "./FileUpload";
import { Sparkles, Loader2, Image as ImageIcon, Sliders, CheckSquare, Square, Settings } from "lucide-react";

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
  });

  useEffect(() => {
    if (initialTheme) {
      setTheme(initialTheme);
    }
  }, [initialTheme]);



  const toggleOption = (key: keyof typeof options) => {
    setOptions((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      return next;
    });
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
      {/* Permanent notice warning */}
      <div className="p-4 bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs rounded-xl leading-relaxed">
        ⚠️ <strong>Avertissement :</strong> Tous les fichiers importés doivent traiter EXACTEMENT du même sujet/thème et posséder la même extension (.png ou .svg uniquement). Le mélange d'extensions est interdit.
      </div>

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

        <div className="flex flex-col gap-2 border-t border-slate-800/60 pt-3">
          <label className="text-sm font-semibold text-slate-300">Nombre d'images à générer (1-4)</label>
          <select
            value={nImages}
            onChange={(e) => setNImages(parseInt(e.target.value, 10))}
            className="p-3 bg-slate-800 text-white rounded-lg border border-slate-700 outline-none focus:border-indigo-500 transition text-sm cursor-pointer"
          >
            <option value={1}>1 image (Par défaut)</option>
            <option value={2}>2 images</option>
            <option value={3}>3 images</option>
            <option value={4}>4 images</option>
          </select>
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
            <button
              type="button"
              onClick={() => toggleOption("generate_ai_stencil")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.generate_ai_stencil ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Transformation IA (Stencil Img2Img)</div>
                <div className="text-xs text-slate-400">Améliore le dessin fourni via IA avant traitement</div>
              </div>
            </button>
          </div>

          <div className="flex items-center space-x-2 my-4 p-3 bg-slate-800/20 rounded-xl border border-slate-800/40 text-left">
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
            <button
              type="button"
              onClick={() => toggleOption("generate_real_mockup")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.generate_real_mockup ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Générer le Vrai Mockup 3D (Bois)</div>
                <div className="text-xs text-slate-400">Génère le mockup de présentation finale</div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                const isManualMode = sourceCondition !== "raw_image";
                if (isManualMode || options.generate_real_mockup) {
                  toggleOption("use_ai_mockup");
                }
              }}
              disabled={sourceCondition === "raw_image" && !options.generate_real_mockup}
              className={`flex items-center gap-3 p-4 border rounded-xl text-left transition ${
                (sourceCondition !== "raw_image" || options.generate_real_mockup)
                  ? "bg-slate-800/40 hover:bg-slate-800/80 border-slate-800 hover:border-slate-700 cursor-pointer"
                  : "bg-slate-900/20 border-slate-900/40 opacity-40 cursor-not-allowed"
              }`}
            >
              {(sourceCondition !== "raw_image" ? options.use_ai_mockup : (options.use_ai_mockup && options.generate_real_mockup)) ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Mockup par Intelligence Artificielle</div>
                <div className="text-xs text-slate-400">Génère le fond via l'IA au lieu du fond classique</div>
              </div>
            </button>
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
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              type="button"
              onClick={() => toggleOption("generate_seo")}
              className="flex items-center gap-3 p-4 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-left transition"
            >
              {options.generate_seo ? <CheckSquare className="text-indigo-400 h-5 w-5" /> : <Square className="text-slate-600 h-5 w-5" />}
              <div>
                <div className="font-bold text-sm text-slate-200">Générer le SEO (Etsy)</div>
                <div className="text-xs text-slate-400">Titres, descriptions et tags optimisés pour la boutique</div>
              </div>
            </button>
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

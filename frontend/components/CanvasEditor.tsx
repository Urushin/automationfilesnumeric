"use client";

import React, { useRef, useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { ReactSketchCanvas, ReactSketchCanvasRef } from "react-sketch-canvas";
import { Paintbrush, Eraser, RefreshCw, CheckCircle, Wand2, Undo2, Redo2, ZoomIn, ZoomOut, Hand, Ban } from "lucide-react";

import { apiUrl } from "@/lib/api";

interface CanvasEditorProps {
  imageUrl: string;
  creationId: number;
  onSaved: (newUrl: string) => void;
}

export const CanvasEditor = forwardRef(function CanvasEditor(
  { imageUrl, creationId, onSaved }: CanvasEditorProps,
  ref
) {
  const canvasRef = useRef<ReactSketchCanvasRef>(null);
  const [tool, setTool] = useState<"brush" | "eraser" | "mask" | "exclusion" | "hand">("brush");
  const [brushColor, setBrushColor] = useState("#000000"); // black for correction
  const [brushSize, setBrushSize] = useState(12);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [scale, setScale] = useState(1);

  // Pan states
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Memory leak protection: track object URLs & dispose canvas contexts on unmount
  const createdUrlsRef = useRef<string[]>([]);

  useEffect(() => {
    return () => {
      // 1. Revoke all temporary object URLs
      createdUrlsRef.current.forEach((url) => {
        try {
          URL.revokeObjectURL(url);
        } catch {
          // ignore
        }
      });
      createdUrlsRef.current = [];

      // 2. Clear canvas data to free GPU/RAM buffers
      try {
        canvasRef.current?.clearCanvas();
      } catch {
        // ignore
      }
    };
  }, []);

  // Clear canvas overlay when imageUrl changes
  useEffect(() => {
    canvasRef.current?.clearCanvas();
  }, [imageUrl]);

  useImperativeHandle(ref, () => ({
    getMergedCanvasDataUrl: async () => {
      try {
        const overlayUrl = await canvasRef.current?.exportImage("png");
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.src = imageUrl;
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
        });

        const canvas = document.createElement("canvas");
        canvas.width = img.width || 1024;
        canvas.height = img.height || 1024;
        const ctx = canvas.getContext("2d");
        if (!ctx) return null;
        
        // 1. ABSOLUTE CLEAR: Wipe out the entire canvas matrix
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // 2. FILL SOLID WHITE SHEET AS BASE
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        if (overlayUrl) {
          const overlayImg = new Image();
          overlayImg.crossOrigin = "anonymous";
          overlayImg.src = overlayUrl;
          await new Promise((resolve, reject) => {
            overlayImg.onload = resolve;
            overlayImg.onerror = reject;
          });

          // Convert exclusion strokes (#FE0000) to solid white on the merged canvas
          const tempCanvas = document.createElement("canvas");
          tempCanvas.width = canvas.width;
          tempCanvas.height = canvas.height;
          const tempCtx = tempCanvas.getContext("2d");
          if (tempCtx) {
            tempCtx.drawImage(overlayImg, 0, 0, tempCanvas.width, tempCanvas.height);
            const imgData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
            const data = imgData.data;
            for (let i = 0; i < data.length; i += 4) {
              const r = data[i];
              const g = data[i+1];
              const b = data[i+2];
              const a = data[i+3];
              // If it's the exclusion brush (pure red #FE0000 or close)
              if (r > 200 && g < 50 && b < 50 && a > 100) {
                data[i] = 255;
                data[i+1] = 255;
                data[i+2] = 255;
                data[i+3] = 255;
              }
            }
            tempCtx.putImageData(imgData, 0, 0);
            ctx.drawImage(tempCanvas, 0, 0);
          }
        }

        return canvas.toDataURL("image/png");
      } catch (e) {
        console.error("Failed to merge canvas", e);
        return null;
      }
    }
  }));

  // Update canvas tool
  const selectTool = (type: "brush" | "eraser" | "mask" | "exclusion" | "hand") => {
    setTool(type);
    if (type === "brush") {
      canvasRef.current?.eraseMode(false);
      setBrushColor("#000000"); // correction brush (black)
    } else if (type === "eraser") {
      canvasRef.current?.eraseMode(false);
      setBrushColor("#FFFFFF"); // correction brush (white)
    } else if (type === "mask") {
      canvasRef.current?.eraseMode(false);
      setBrushColor("rgba(239, 68, 68, 0.5)"); // semi-transparent red mask
    } else if (type === "exclusion") {
      canvasRef.current?.eraseMode(false);
      setBrushColor("#FFFFFF"); // Exclusion Brush (strictly paint solid white #FFFFFF)
    }
  };

  // Convert canvas to png blob
  const exportCanvasBlob = async (): Promise<Blob | null> => {
    try {
      const dataUrl = await canvasRef.current?.exportImage("png");
      if (!dataUrl) return null;
      const res = await fetch(dataUrl);
      return await res.blob();
    } catch (e) {
      console.error("Export canvas failed:", e);
      return null;
    }
  };

  // Save local correction (draw overlay directly on image)
  const saveLocalCorrection = async () => {
    setLoading(true);
    setStatus("Fusion de la correction locale...");
    try {
      const canvasBlob = await exportCanvasBlob();
      if (!canvasBlob) {
        alert("Impossible de récupérer le tracé.");
        setLoading(false);
        return;
      }

      // Draw canvas drawing on top of the original image
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.src = imageUrl;
      await new Promise((resolve) => { img.onload = resolve; });

      const canvas = document.createElement("canvas");
      canvas.width = img.width || 1024;
      canvas.height = img.height || 1024;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not get 2d context");

      // 1. ABSOLUTE CLEAR: Wipe out the entire canvas matrix
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 2. FILL SOLID WHITE SHEET AS BASE
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw background stencil
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Draw overlay strokes
      const overlayUrl = await canvasRef.current?.exportImage("png");
      if (overlayUrl) {
        const overlayImg = new Image();
        overlayImg.crossOrigin = "anonymous";
        overlayImg.src = overlayUrl;
        await new Promise((resolve) => { overlayImg.onload = resolve; });
        
        // Convert exclusion strokes to white
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = canvas.width;
        tempCanvas.height = canvas.height;
        const tempCtx = tempCanvas.getContext("2d");
        if (tempCtx) {
          tempCtx.drawImage(overlayImg, 0, 0, tempCanvas.width, tempCanvas.height);
          const imgData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
          const data = imgData.data;
          for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i+1];
            const b = data[i+2];
            const a = data[i+3];
            if (r > 200 && g < 50 && b < 50 && a > 100) {
              data[i] = 255;
              data[i+1] = 255;
              data[i+2] = 255;
              data[i+3] = 255;
            }
          }
          tempCtx.putImageData(imgData, 0, 0);
          ctx.drawImage(tempCanvas, 0, 0);
        }
      }

      // Convert combined to blob
      const combinedBlob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob((b) => resolve(b), "image/png");
      });

      if (!combinedBlob) throw new Error("Combined blob conversion failed");

      const formData = new FormData();
      formData.append("file", combinedBlob, "correction.png");
      formData.append("creation_id", creationId.toString());
      formData.append("output_path", imageUrl); // overwrite source image

      const res = await fetch(apiUrl("/api/pipeline/local-correction"), {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setStatus("Correction enregistrée !");
        canvasRef.current?.clearCanvas();
        onSaved(data.output_path + "?t=" + Date.now());
      } else {
        const err = await res.json();
        alert("Erreur: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("Erreur lors de la sauvegarde.");
    } finally {
      setLoading(false);
      setTimeout(() => setStatus(""), 3000);
    }
  };

  // Run AI Inpainting using the transparent red mask
  const runAiInpainting = async () => {
    if (!prompt) return alert("Veuillez saisir des instructions pour l'IA.");
    setLoading(true);
    setStatus("Régénération de la zone par l'IA...");
    try {
      const dataUrl = await canvasRef.current?.exportImage("png");
      if (!dataUrl) {
        alert("Aucun tracé de masque trouvé.");
        setLoading(false);
        return;
      }

      // Create a solid mask image (white where red brush is drawn, black background)
      const overlayImg = new Image();
      overlayImg.crossOrigin = "anonymous";
      overlayImg.src = dataUrl;
      await new Promise((resolve) => { overlayImg.onload = resolve; });

      const canvas = document.createElement("canvas");
      canvas.width = overlayImg.width || 1024;
      canvas.height = overlayImg.height || 1024;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not get context");

      // Clear entire canvas area
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw solid black background
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw mask overlay as white pixels (handling both AI mask and exclusion brush in context)
      ctx.drawImage(overlayImg, 0, 0, canvas.width, canvas.height);
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imgData.data;
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i+1];
        const b = data[i+2];
        const a = data[i+3];
        // If the pixel is not transparent black, make it solid white
        if (a > 10) {
          data[i] = 255;
          data[i+1] = 255;
          data[i+2] = 255;
          data[i+3] = 255;
        } else {
          data[i] = 0;
          data[i+1] = 0;
          data[i+2] = 0;
          data[i+3] = 255;
        }
      }
      ctx.putImageData(imgData, 0, 0);

      const maskBlob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob((b) => resolve(b), "image/png");
      });

      if (!maskBlob) throw new Error("Failed to create mask blob");

      // Upload mask to storage temporarily or send directly
      const formData = new FormData();
      formData.append("image_path", imageUrl);
      
      // Let's create mask file
      const maskFile = new File([maskBlob], "mask.png", { type: "image/png" });
      
      // Upload mask first so backend has file path
      const uploadFormData = new FormData();
      uploadFormData.append("file", maskFile);
      uploadFormData.append("theme", "mask_" + creationId);
      uploadFormData.append("source_type", "ready_bw_image");
      
      const uploadRes = await fetch(apiUrl("/api/pipeline/upload"), {
        method: "POST",
        body: uploadFormData
      });
      if (!uploadRes.ok) throw new Error("Mask upload failed");
      const maskData = await uploadRes.json();
      
      // Send to backend inpainting route
      const inpFormData = new FormData();
      inpFormData.append("image_path", imageUrl);
      inpFormData.append("mask_path", maskData.source_png_path);
      inpFormData.append("prompt", prompt);
      inpFormData.append("output_path", imageUrl);
      inpFormData.append("creation_id", creationId.toString());

      const res = await fetch(apiUrl("/api/pipeline/inpainting"), {
        method: "POST",
        body: inpFormData
      });

      if (res.ok) {
        const resData = await res.json();
        setStatus("Zone régénérée avec succès !");
        canvasRef.current?.clearCanvas();
        onSaved(resData.output_path + "?t=" + Date.now());
      } else {
        const err = await res.json();
        alert("Erreur: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("Erreur lors de la retouche IA.");
    } finally {
      setLoading(false);
      setTimeout(() => setStatus(""), 3000);
    }
  };

  // Drag pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (tool !== "hand") return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - offsetX, y: e.clientY - offsetY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || tool !== "hand") return;
    setOffsetX(e.clientX - dragStart.x);
    setOffsetY(e.clientY - dragStart.y);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Tool panel */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/60 rounded-xl border border-slate-800">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => selectTool("brush")}
            className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition ${
              tool === "brush" ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
            title="Pinceau Réparation Noir"
          >
            <Paintbrush className="h-4 w-4" /> Noir
          </button>
          <button
            type="button"
            onClick={() => selectTool("eraser")}
            className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition ${
              tool === "eraser" ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
            title="Pinceau Réparation Blanc"
          >
            <Eraser className="h-4 w-4" /> Blanc
          </button>
          <button
            type="button"
            onClick={() => selectTool("exclusion")}
            className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition ${
              tool === "exclusion" ? "bg-red-600 text-white" : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
            title="Pinceau Exclusion (Ignoré par OpenCV)"
          >
            <Ban className="h-4 w-4" /> Exclusion
          </button>
          <button
            type="button"
            onClick={() => selectTool("hand")}
            className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition ${
              tool === "hand" ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
            title="Outil Main (Panoramique)"
          >
            <Hand className="h-4 w-4" /> Main
          </button>
          <button
            type="button"
            onClick={() => selectTool("mask")}
            className={`p-2 rounded-lg flex items-center gap-1.5 text-xs font-bold transition ${
              tool === "mask" ? "bg-rose-600 text-white animate-pulse" : "bg-slate-800 text-slate-300 hover:text-white"
            }`}
            title="Zone Retouche IA (Masque rouge)"
          >
            <Wand2 className="h-4 w-4" /> Retouche IA
          </button>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-800/40 px-2 py-1 rounded-lg border border-slate-800">
            <span className="text-[11px] text-slate-400">Taille:</span>
            <input
              type="range"
              min={2}
              max={50}
              value={brushSize}
              onChange={(e) => setBrushSize(parseInt(e.target.value))}
              className="w-16 accent-indigo-500 cursor-pointer h-1.5"
            />
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setScale(prev => Math.min(3, prev + 0.1))}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
              title="Zoom In"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setScale(prev => Math.max(0.5, prev - 0.1))}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
              title="Zoom Out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => { setScale(1); setOffsetX(0); setOffsetY(0); }}
              className="text-[9px] px-1.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition font-bold"
              title="Reset Zoom & Pan"
            >
              {Math.round(scale * 100)}%
            </button>
          </div>

          <span className="w-px h-5 bg-slate-800" />

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => canvasRef.current?.undo()}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
              title="Undo"
            >
              <Undo2 className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => canvasRef.current?.redo()}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
              title="Redo"
            >
              <Redo2 className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => {
                canvasRef.current?.clearCanvas();
                setOffsetX(0);
                setOffsetY(0);
              }}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
              title="Clear Canvas"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Editor Frame */}
      <div 
        className="relative w-full aspect-square bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 flex items-center justify-center select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: tool === "hand" ? (isDragging ? "grabbing" : "grab") : "default" }}
      >
        <div 
          className="relative w-full h-full bg-white"
          style={{ 
            transform: `translate(${offsetX}px, ${offsetY}px) scale(${scale})`, 
            transformOrigin: "center center", 
            transition: isDragging ? "none" : "transform 0.15s ease-out", 
            backgroundColor: "#ffffff" 
          }}
        >
          {/* Background Stencil image */}
          {imageUrl && !loading && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              crossOrigin="anonymous"
              src={imageUrl}
              alt="Base stencil"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none select-none"
            />
          )}

          {/* Draw Canvas */}
          <ReactSketchCanvas
            ref={canvasRef}
            strokeWidth={brushSize}
            strokeColor={brushColor}
            canvasColor="transparent"
            className={`absolute inset-0 w-full h-full z-20 ${tool === "hand" ? "pointer-events-none" : "pointer-events-auto cursor-crosshair"}`}
            style={{ pointerEvents: tool === "hand" ? "none" : "auto" }}
          />
        </div>
      </div>

      {/* Action Zone */}
      <div className="p-4 bg-slate-900/60 rounded-xl border border-slate-800 space-y-4">
        {tool === "mask" ? (
          <div className="space-y-3">
            <div className="text-xs font-semibold text-rose-400">Mode Retouche IA (Inpainting)</div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Dessinez sur la zone défectueuse à remplacer, décrivez ce que l'IA doit y ajouter ou corriger puis validez.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ex: Remplir le trou avec un motif filigrane de feuille..."
                className="flex-1 p-2.5 rounded-lg bg-slate-800 text-white border border-slate-700 outline-none text-xs focus:border-rose-500 transition"
              />
              <button
                type="button"
                onClick={runAiInpainting}
                disabled={loading}
                className="px-4 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg transition flex items-center gap-1.5 disabled:opacity-50"
              >
                <Wand2 className="h-4 w-4" />
                Régénérer
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs font-semibold text-slate-200">Mode Correction Directe & Exclusion</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Réparez manuellement les contours, ou utilisez l'Exclusion (Rouge) pour masquer un élément lors de la découpe OpenCV.
              </p>
            </div>
            <button
              type="button"
              onClick={saveLocalCorrection}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-lg transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <CheckCircle className="h-4 w-4" />
              Enregistrer les retouches
            </button>
          </div>
        )}

        {status && (
          <div className="text-xs text-indigo-400 font-semibold flex items-center gap-1.5 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping"></span>
            {status}
          </div>
        )}
      </div>
    </div>
  );
});

export default CanvasEditor;

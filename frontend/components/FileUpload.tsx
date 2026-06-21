"use client";

import { useState, useRef } from "react";
import { UploadCloud, FileImage, X } from "lucide-react";

interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
  onFilesSelect?: (files: File[]) => void;
  multiple?: boolean;
}

export default function FileUpload({ onFileSelect, onFilesSelect, multiple = false }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);


  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateAndSelectFiles = (filesList: File[]) => {
    if (filesList.length === 0) return;
    
    // Check if formats match
    const firstType = filesList[0].name.split('.').pop()?.toLowerCase();
    const formatsMatch = filesList.every(f => f.name.split('.').pop()?.toLowerCase() === firstType);
    if (!formatsMatch) {
      alert("Tous les fichiers du lot doivent avoir exactement le même format (tous SVG ou tous PNG/JPEG).");
      return;
    }

    setSelectedFiles(filesList);
    setSelectedFile(filesList[0]);
    onFileSelect(filesList[0]);
    onFilesSelect?.(filesList);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files).filter((file) => 
        file.type.startsWith("image/") || file.name.endsWith(".svg")
      );
      validateAndSelectFiles(files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files).filter((file) => 
        file.type.startsWith("image/") || file.name.endsWith(".svg")
      );
      validateAndSelectFiles(files);
    }
  };

  const clearFiles = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setSelectedFiles([]);
    onFileSelect(null);
    onFilesSelect?.([]);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const triggerInput = () => {
    inputRef.current?.click();
  };

  return (
    <div className="w-full space-y-2">
      <input
        type="file"
        ref={inputRef}
        onChange={handleChange}
        multiple={multiple}
        accept="image/*,.svg"
        className="hidden"
      />
      {multiple && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/25 rounded-xl text-xs text-amber-200 leading-relaxed">
          ⚠️ <strong>Avertissement :</strong> Les fichiers importés ensemble doivent contenir le <strong>même sujet</strong> et élément, car ils partageront le même thème de design. Ils doivent également avoir <strong>exactement le même format</strong>.
        </div>
      )}

      {selectedFiles.length === 0 ? (
        <div
          onClick={triggerInput}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${dragActive
              ? "border-indigo-500 bg-indigo-500/10 scale-[0.99]"
              : "border-slate-800 bg-slate-900/40 hover:bg-slate-900/60 hover:border-slate-700"
            }`}
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-900 border border-slate-800 shadow-inner mb-4">
            <UploadCloud className="h-6 w-6 text-slate-400" />
          </div>
          <p className="text-sm font-semibold text-slate-200">
            {multiple ? "Faites glisser vos images ici ou cliquez pour parcourir" : "Faites glisser votre image ici ou cliquez pour parcourir"}
          </p>
          <p className="text-xs text-slate-500 mt-1.5">
            JPEG, PNG, WEBP ou SVG acceptés. Image d'inspiration ou pochoir brut.
            {multiple ? " Plusieurs fichiers peuvent être déposés ensemble." : ""}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {selectedFiles.map((file, idx) => (
            <div key={idx} className="flex items-center justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div className="flex items-center space-x-3 truncate">
                <div className="p-2 rounded-lg bg-indigo-950/50 border border-indigo-500/20 text-indigo-400">
                  <FileImage className="h-5 w-5" />
                </div>
                <div className="truncate text-left">
                  <div className="text-sm font-semibold text-slate-200 truncate">{file.name}</div>
                  <div className="text-xs text-slate-500">
                    {(file.size / 1024).toFixed(1)} KB • Fichier Image
                  </div>
                </div>
              </div>
              {idx === 0 && (
                <button
                  onClick={clearFiles}
                  className="p-1 rounded-full hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
                  title="Supprimer tous les fichiers"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

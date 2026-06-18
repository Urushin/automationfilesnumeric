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

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const files = Array.from(e.dataTransfer.files).filter((file) => file.type === "image/png");
      if (files.length > 0) {
        setSelectedFile(files[0]);
        onFileSelect(files[0]);
        onFilesSelect?.(files);
      } else {
        alert("Seuls les fichiers PNG sont acceptés.");
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const files = Array.from(e.target.files).filter((file) => file.type === "image/png");
      if (files.length > 0) {
        setSelectedFile(files[0]);
        onFileSelect(files[0]);
        onFilesSelect?.(files);
      } else {
        alert("Seuls les fichiers PNG sont acceptés.");
      }
    }
  };

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
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
    <div className="w-full">
      <input
        ref={inputRef}
        type="file"
        accept="image/png"
        multiple={multiple}
        onChange={handleChange}
        className="hidden"
      />
      
      {!selectedFile ? (
        <div
          onClick={triggerInput}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${
            dragActive 
              ? "border-indigo-500 bg-indigo-500/10 scale-[0.99]" 
              : "border-slate-800 bg-slate-900/40 hover:bg-slate-900/60 hover:border-slate-700"
          }`}
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-900 border border-slate-800 shadow-inner mb-4">
            <UploadCloud className="h-6 w-6 text-slate-400" />
          </div>
          <p className="text-sm font-semibold text-slate-200">
            Faites glisser votre motif PNG ici ou cliquez pour parcourir
          </p>
          <p className="text-xs text-slate-500 mt-1.5">
            Noir & Blanc pur, contours nets recommandés.
            {multiple ? " Plusieurs fichiers PNG peuvent être déposés ensemble." : ""}
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center space-x-3 truncate">
            <div className="p-2 rounded-lg bg-indigo-950/50 border border-indigo-500/20 text-indigo-400">
              <FileImage className="h-5 w-5" />
            </div>
            <div className="truncate text-left">
              <div className="text-sm font-semibold text-slate-200 truncate">{selectedFile.name}</div>
              <div className="text-xs text-slate-500">
                {(selectedFile.size / 1024).toFixed(1)} KB • PNG Image
              </div>
            </div>
          </div>
          <button
            onClick={clearFile}
            className="p-1 rounded-full hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
            title="Supprimer le fichier"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

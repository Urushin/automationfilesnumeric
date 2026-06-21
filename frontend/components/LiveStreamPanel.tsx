"use client";

import React, { useEffect, useState } from "react";

interface LiveStreamPanelProps {
  streamUrl: string;
  onStreamComplete?: () => void;
}

export default function LiveStreamPanel({ streamUrl, onStreamComplete }: LiveStreamPanelProps) {
  const [currentSrc, setCurrentSrc] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(true);
  const [imageError, setImageError] = useState(false);

  const activeUrlRef = React.useRef<string | null>(null);

  useEffect(() => {
    if (!streamUrl) return;
    setIsVisible(true);
    setImageError(false);

    let isMounted = true;
    const chunks: Uint8Array[] = [];

    const consumeStream = async () => {
      try {
        const response = await fetch(streamUrl);
        if (!response.body) {
          console.error("Stream response body is empty");
          return;
        }
        const reader = response.body.getReader();

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            setTimeout(() => {
              if (isMounted) {
                setIsVisible(false);
                if (onStreamComplete) onStreamComplete();
              }
            }, 1500);
            break;
          }

          if (value) {
            chunks.push(value);
            const blob = new Blob(chunks as BlobPart[], { type: "image/png" });
            const objectUrl = URL.createObjectURL(blob);

            if (isMounted) {
              if (activeUrlRef.current && activeUrlRef.current.startsWith("blob:")) {
                URL.revokeObjectURL(activeUrlRef.current);
              }
              activeUrlRef.current = objectUrl;
              setCurrentSrc(objectUrl);
            } else {
              URL.revokeObjectURL(objectUrl);
            }
          }
        }
      } catch (err) {
        console.error("Progressive preview stream parsing crashed:", err);
      }
    };

    consumeStream();

    return () => {
      isMounted = false;
      if (activeUrlRef.current && activeUrlRef.current.startsWith("blob:")) {
        URL.revokeObjectURL(activeUrlRef.current);
        activeUrlRef.current = null;
      }
    };
  }, [streamUrl, onStreamComplete]);

  if (!isVisible || !streamUrl) return null;

  return (
    <div className="fixed top-20 right-4 w-96 p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl transition-all duration-500 ease-in-out z-50 animate-in fade-in slide-in-from-right-8">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-indigo-400 animate-pulse flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></div>
          ⚡ Tracé IA en temps réel...
        </h4>
        <span className="text-xs bg-indigo-600/30 border border-indigo-500/50 text-indigo-200 px-2 py-0.5 rounded-full font-bold">gpt-image-2</span>
      </div>
      <div className="w-full aspect-square bg-slate-950 border border-slate-800 rounded-lg overflow-hidden flex items-center justify-center relative">
        {/* Loading Scanner Animation */}
        <div className="absolute inset-0 bg-indigo-500/5 animate-pulse"></div>
        <div className="absolute top-0 left-0 w-full h-1 bg-indigo-500 shadow-[0_0_20px_rgba(99,102,241,0.8)] animate-[scan_2s_ease-in-out_infinite]"></div>
        
        {/* Hexagon / Grid background placeholder */}
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-10"></div>

        {currentSrc && !imageError && (
          // eslint-disable-next-line @next/next/no-img-element
          <img 
            src={currentSrc} 
            crossOrigin="anonymous" 
            alt="Progressive Stream Preview" 
            className="w-full h-full object-contain relative z-10 opacity-70 mix-blend-screen"
            onError={() => setImageError(true)}
          />
        )}
      </div>
    </div>
  );
}

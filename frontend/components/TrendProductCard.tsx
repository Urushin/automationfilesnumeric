import React from 'react';
import { Sparkles, ExternalLink, Lightbulb } from 'lucide-react';

export interface TrendItem {
    id: number;
    title: string;
    source_url: string;
    thumbnail_url: string;
    trend_score: number;
    section: string;
    description?: string;
    source?: string;
    category?: string | null;
}

interface Props {
    item: TrendItem;
    onGenerate?: (item: TrendItem) => void;
}

export const TrendProductCard: React.FC<Props> = ({ item, onGenerate }) => {
    const isConcept = item.section === "ideas";

    return (
        <div className="glass-panel border border-slate-800/80 rounded-2xl overflow-hidden flex flex-col justify-between group transition duration-300 hover:border-slate-700/60 bg-slate-900/40 shadow-xl backdrop-blur-sm">
            {/* Visual Header */}
            <div className="relative w-full h-48 bg-slate-950/40 flex items-center justify-center overflow-hidden border-b border-slate-900">
                {item.thumbnail_url ? (
                    <img
                        src={item.thumbnail_url}
                        alt={item.title}
                        className="w-full h-full object-cover object-center group-hover:scale-105 transition duration-500"
                        loading="lazy"
                    />
                ) : (
                    <div className="flex flex-col items-center justify-center text-indigo-400/60 p-6 text-center select-none">
                        <Lightbulb className="h-10 w-10 text-indigo-400 mb-2 animate-pulse" />
                        <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">Idée de Concept</span>
                    </div>
                )}

                {/* Score & Trend Badge */}
                {(() => {
                    const score = item.trend_score;
                    const isConcept = item.section === "ideas";
                    if (score >= 85 && !isConcept) {
                        return (
                            <div className="absolute top-3 right-3 bg-rose-950/80 backdrop-blur-md text-rose-400 border border-rose-500/30 font-bold text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-lg shadow-md flex items-center gap-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-ping"></span>
                                Explosif ({score})
                            </div>
                        );
                    } else if (score >= 60 && !isConcept) {
                        return (
                            <div className="absolute top-3 right-3 bg-blue-950/80 backdrop-blur-md text-blue-400 border border-blue-500/30 font-bold text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-lg shadow-md">
                                Stable ({score})
                            </div>
                        );
                    } else {
                        return (
                            <div className="absolute top-3 right-3 bg-emerald-950/80 backdrop-blur-md text-emerald-400 border border-emerald-500/30 font-bold text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-lg shadow-md">
                                Nouveauté ({score})
                            </div>
                        );
                    }
                })()}

                {/* Platform Source badge */}
                {item.source && (
                    <div className="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md text-slate-300 border border-slate-800 text-[10px] uppercase font-bold px-2 py-0.5 rounded-md">
                        {item.source.replace("_", " ")}
                    </div>
                )}
            </div>

            {/* Body */}
            <div className="p-5 flex flex-col flex-grow justify-between gap-4">
                <div className="space-y-2">
                    <h3 className="font-bold text-slate-200 text-sm line-clamp-2 min-h-[40px] leading-snug">
                        {item.title}
                    </h3>
                    {item.description && (
                        <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                            {item.description}
                        </p>
                    )}
                </div>

                <div className="flex flex-col gap-2.5 mt-auto pt-3 border-t border-slate-900/60">
                    {onGenerate && (
                        <button
                            onClick={() => onGenerate(item)}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs py-2.5 rounded-xl flex items-center justify-center gap-1.5 transition shadow-sm"
                        >
                            <Sparkles className="h-3.5 w-3.5" />
                            <span>Générer ce design</span>
                        </button>
                    )}
                    {item.source_url && (
                        <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full flex items-center justify-center gap-1 text-xs font-semibold text-slate-300 bg-slate-800/60 hover:bg-slate-800 border border-slate-800/80 py-2 rounded-xl transition"
                        >
                            <span>Voir la source</span>
                            <ExternalLink className="h-3 w-3 opacity-60" />
                        </a>
                    )}
                </div>
            </div>
        </div>
    );
};
"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  TrendingUp,
  RefreshCw,
  Zap,
  Flame,
  ArrowUpRight,
  Clock,
  Sparkles,
  ExternalLink,
  Filter,
  Star,
} from "lucide-react";
import { apiUrl, API_BASE } from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────
interface IdeaItem {
  id: number;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  source_url: string | null;
  trend_score: number;
  category: string | null;
  detected_at: string;
  is_injected: boolean;
  keywords: string | null;
  source: string | null;
}

interface SeasonalContext {
  label: string;
  keywords: string[];
  category: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function getScoreBadge(score: number) {
  if (score >= 80) return { label: "🔥 Viral", color: "bg-rose-600/20 text-rose-300 border-rose-500/40" };
  if (score >= 60) return { label: "📈 Stable", color: "bg-blue-600/20 text-blue-300 border-blue-500/40" };
  return { label: "🌱 Nouveau", color: "bg-emerald-600/20 text-emerald-300 border-emerald-500/40" };
}

function parseKeywords(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return raw.split(",").map((k) => k.trim()).filter(Boolean);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// IDEA CARD
// ─────────────────────────────────────────────────────────────────────────────
function IdeaCard({ idea, onInject }: { idea: IdeaItem; onInject: (id: number) => void }) {
  const badge = getScoreBadge(idea.trend_score);
  const keywords = parseKeywords(idea.keywords);

  const hasSourceUrl = Boolean(idea.source_url);
  const proxiedThumb = idea.thumbnail_url
    ? `${apiUrl(`/api/scraper/proxy-image?url=${encodeURIComponent(idea.thumbnail_url)}`)}`
    : null;

  return (
    <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800/60 hover:border-slate-700/80 transition-all duration-300 hover:shadow-lg hover:shadow-indigo-500/5 group flex flex-col">
      {/* Thumbnail or placeholder */}
      <div className="relative aspect-square w-full bg-slate-900/60 overflow-hidden">
        {idea.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={proxiedThumb || idea.thumbnail_url}
            alt={idea.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={(e) => {
              (e.target as HTMLImageElement).src = `https://placehold.co/400x400/1e293b/64748b?text=${encodeURIComponent((idea.category || 'Design').slice(0, 1))}`;
            }}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-700 space-y-2">
            <Sparkles className="h-10 w-10 opacity-40" />
            <span className="text-xs opacity-40 text-center px-4">{idea.category || "Design"}</span>
          </div>
        )}

        {/* Score badge */}
        <div className={`absolute top-2 right-2 text-[10px] font-bold px-2 py-1 rounded-lg border backdrop-blur-md ${badge.color}`}>
          {badge.label}
        </div>

        {/* Score number */}
        <div className="absolute bottom-2 left-2 flex items-center space-x-1 bg-slate-950/80 backdrop-blur-md rounded-lg px-2 py-1 border border-slate-800/60">
          <TrendingUp className="h-3 w-3 text-indigo-400" />
          <span className="text-[10px] font-bold text-slate-300">{idea.trend_score}/100</span>
        </div>
      </div>

        {/* Content */}
        <div className="p-4 flex flex-col flex-1 space-y-3">
          <h3 className="text-xs font-semibold text-slate-200 leading-relaxed line-clamp-3">
            {idea.title}
          </h3>

          {/* Description */}
          {idea.description && (
            <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">
              {idea.description}
            </p>
          )}

          {/* Keywords */}
          {keywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {keywords.slice(0, 4).map((kw, i) => (
                <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                  {kw}
                </span>
              ))}
            </div>
          )}

          {/* Category & Source */}
          <div className="flex items-center justify-between text-[9px] text-slate-600">
            <span>{idea.category || "Général"}</span>
            <span>{idea.source === "mock" ? "Exemple" : "Etsy RSS"}</span>
          </div>

        {/* Actions */}
        <div className="flex gap-2 mt-auto pt-2">
          {hasSourceUrl && (
            <a
              href={idea.source_url!}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center space-x-1.5 text-[11px] bg-slate-800 hover:bg-slate-700 border border-slate-700/50 text-slate-300 py-2 rounded-xl font-semibold transition"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Voir la source</span>
            </a>
          )}
          <button
            onClick={() => onInject(idea.id)}
            disabled={idea.is_injected}
            className={`flex-1 flex items-center justify-center space-x-1.5 rounded-xl py-2 text-xs font-bold transition ${
              hasSourceUrl ? "" : "w-full"
            } ${
              idea.is_injected
                ? "bg-emerald-950/40 text-emerald-500 border border-emerald-500/20 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-500/20"
            }`}
          >
            {idea.is_injected ? (
              <>
                <Star className="h-3.5 w-3.5" />
                <span>Injecté</span>
              </>
            ) : (
              <>
                <Zap className="h-3.5 w-3.5" />
                <span>Créer similaire</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────────────
export default function TrendsPage() {
  const router = useRouter();
  const [ideas, setIdeas] = useState<IdeaItem[]>([]);
  const [seasonal, setSeasonal] = useState<SeasonalContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "info"; message: string } | null>(null);

  const fetchIdeas = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: "60" });
      if (activeCategory) params.set("category", activeCategory);
      const res = await fetch(apiUrl(`/api/scraper/ideas?${params}`));
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        console.error("Failed to fetch ideas:", res.status, text);
        setNotification({ type: "info", message: `Erreur API (${res.status}). Vérifiez que le backend est démarré sur ${API_BASE}` });
        return;
      }
      const data = await res.json();
      setIdeas(data);
    } catch (e: any) {
      console.error("Fetch error:", e);
      setNotification({ type: "info", message: `Erreur de connexion au backend (${API_BASE}). Vérifiez qu'il est démarré.` });
    }
  }, [activeCategory]);

  const fetchSeasonal = async () => {
    try {
      const res = await fetch(apiUrl("/api/scraper/seasonal"));
      if (res.ok) setSeasonal(await res.json());
    } catch {}
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([fetchIdeas(), fetchSeasonal()]);
      setLoading(false);
    };
    load();
  }, [fetchIdeas]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(apiUrl("/api/scraper/refresh"), { method: "POST" });
      if (res.ok) {
        setNotification({ type: "info", message: "Actualisation en cours... Revenez dans 30 secondes." });
        setTimeout(() => {
          fetchIdeas();
          setNotification(null);
        }, 8000);
      }
    } catch {}
    setRefreshing(false);
  };

  const handleInject = async (id: number) => {
    try {
      const res = await fetch(apiUrl(`/api/scraper/inject/${id}`), { method: "POST" });
      if (!res.ok) return;
      const data = await res.json();

      // Update local state
      setIdeas((prev) => prev.map((item) => item.id === id ? { ...item, is_injected: true } : item));

      // Copy stencil prompt to clipboard
      if (data.stencil_prompt) {
        await navigator.clipboard.writeText(data.stencil_prompt).catch(() => {});
      }

      // Open Google AI Studio in a new tab
      window.open(data.google_ai_studio_url, "_blank");

      // Navigate to create page with theme pre-filled
      const theme = encodeURIComponent(data.theme);
      router.push(`/?theme=${theme}`);
    } catch (e) {
      console.error("Inject failed", e);
    }
  };

  // Extract unique categories from ideas
  const categories = Array.from(new Set(ideas.map((i) => i.category).filter(Boolean) as string[]));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-slate-100 via-rose-200 to-amber-200 bg-clip-text text-transparent">
            Banque d&apos;Idées & Tendances
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {seasonal ? (
              <span>
                🗓 Saison actuelle :{" "}
                <span className="text-amber-300 font-semibold">{seasonal.label}</span>
              </span>
            ) : (
              "Tendances Etsy scrapées en temps réel"
            )}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm font-semibold transition disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          <span>{refreshing ? "Actualisation..." : "Actualiser les tendances"}</span>
        </button>
      </div>

      {/* Notification */}
      {notification && (
        <div className="p-4 rounded-xl bg-indigo-950/40 text-indigo-300 border border-indigo-500/20 text-sm flex items-center space-x-2">
          <Sparkles className="h-4 w-4 flex-shrink-0" />
          <span>{notification.message}</span>
        </div>
      )}

      {/* Seasonal banner */}
      {seasonal && (
        <div className="glass-panel rounded-2xl p-5 border border-amber-500/20 bg-amber-950/10">
          <div className="flex items-center space-x-3 mb-3">
            <Flame className="h-5 w-5 text-amber-400" />
            <h2 className="text-sm font-bold text-amber-300">
              Tendances saisonnières : {seasonal.label}
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {seasonal.keywords.map((kw, i) => (
              <button
                key={i}
                onClick={() => {
                  setActiveCategory(null);
                  // Pre-fill the creation page with seasonal keyword
                  router.push(`/?theme=${encodeURIComponent(kw + " laser cut SVG stencil")}`);
                }}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-950/40 hover:bg-amber-900/40 border border-amber-500/30 text-amber-300 text-xs font-semibold transition"
              >
                <ArrowUpRight className="h-3 w-3" />
                <span>{kw}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Category filters */}
      {categories.length > 0 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-hide">
          <Filter className="h-4 w-4 text-slate-500 flex-shrink-0" />
          <button
            onClick={() => setActiveCategory(null)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              !activeCategory
                ? "bg-indigo-600 border-indigo-500 text-white"
                : "bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Tout
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat === activeCategory ? null : cat)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                activeCategory === cat
                  ? "bg-indigo-600 border-indigo-500 text-white"
                  : "bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <RefreshCw className="h-10 w-10 text-indigo-500 animate-spin" />
          <p className="text-slate-400 text-sm">Chargement de la banque d&apos;idées...</p>
        </div>
      ) : ideas.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-6">
          <div className="w-20 h-20 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center">
            <TrendingUp className="h-8 w-8 text-slate-600" />
          </div>
          <div className="text-center space-y-2">
            <p className="text-slate-300 font-semibold">Aucune idée dans la banque</p>
            <p className="text-slate-500 text-sm">Cliquez sur &quot;Actualiser les tendances&quot; pour scraper Etsy</p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition disabled:opacity-50"
          >
            <Zap className="h-4 w-4" />
            <span>Lancer le scraping</span>
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {ideas.map((idea) => (
              <IdeaCard key={idea.id} idea={idea} onInject={handleInject} />
            ))}
          </div>
          <p className="text-center text-[11px] text-slate-600 pb-4">
            {ideas.length} idée{ideas.length > 1 ? "s" : ""} dans la banque
            {activeCategory ? ` · Filtre : ${activeCategory}` : ""}
          </p>
        </>
      )}

      {/* Info box */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800/40 space-y-2">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-2">
          <Clock className="h-3.5 w-3.5" />
          <span>Comment ça fonctionne ?</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-slate-500 leading-relaxed">
          <div className="space-y-1">
            <p className="font-semibold text-slate-400">1. Scraping Etsy RSS</p>
            <p>Le backend lit les flux XML Etsy sans risque de blocage et extrait les produits tendance.</p>
          </div>
          <div className="space-y-1">
            <p className="font-semibold text-slate-400">2. Score algorithmique</p>
            <p>Chaque idée reçoit un score 1-100 basé sur le rang et la fréquence d&apos;apparition inter-requêtes.</p>
          </div>
          <div className="space-y-1">
            <p className="font-semibold text-slate-400">3. Injection pipeline</p>
            <p>Cliquez &quot;Créer similaire&quot; pour pré-remplir le thème et ouvrir Google AI Studio avec le prompt stencil.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

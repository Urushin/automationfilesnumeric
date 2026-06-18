"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Download, 
  ExternalLink, 
  Eye, 
  ShoppingBag, 
  Calendar, 
  RefreshCw, 
  Search,
  CheckCircle,
  FileArchive,
  AlertCircle,
  Trash2
} from "lucide-react";
import { apiUrl, assetUrl } from "@/lib/api";

interface Creation {
  id: number;
  timestamp: string;
  theme: string;
  title_fr: string | null;
  title_en: string | null;
  description: string | null;
  tags_fr: string | null;
  tags_en: string | null;
  source_png_path: string | null;
  svg_path: string | null;
  dxf_path: string | null;
  pdf_path: string | null;
  upscale_png_path: string | null;
  mockup_path: string | null;
  zip_path: string | null;
  is_published_etsy: boolean;
  etsy_listing_id: string | null;
}

export default function DashboardPage() {
  const [creations, setCreations] = useState<Creation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [publishingId, setPublishingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    fetchCreations();
  }, []);

  const fetchCreations = async () => {
    try {
      setLoading(true);
      const res = await fetch(apiUrl("/api/creations"));
      if (!res.ok) throw new Error("Failed to fetch creations");
      const data = await res.json();
      setCreations(data);
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Erreur de chargement de l'historique" });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (creationId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Voulez-vous vraiment supprimer cette création ? Cette action est irréversible.")) return;
    
    try {
      setDeletingId(creationId);
      const res = await fetch(apiUrl(`/api/creations/${creationId}`), {
        method: "DELETE"
      });
      
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Échec de la suppression.");
      }
      
      setNotification({ type: "success", message: "Création supprimée avec succès." });
      fetchCreations();
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setDeletingId(null);
    }
  };

  const handlePublish = async (creationId: number) => {
    try {
      setPublishingId(creationId);
      setNotification(null);
      
      const res = await fetch(apiUrl(`/api/creations/${creationId}/publish`), {
        method: "POST"
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Échec de publication Etsy.");
      }
      
      const data = await res.json();
      
      setNotification({
        type: "success",
        message: data.is_simulation 
          ? `[Mode Simulé] Fiche produit créée ! ID: ${data.listing_id}`
          : `Fiche produit publiée avec succès sur Etsy !`
      });
      
      // Open listing url in new tab
      if (data.listing_url) {
        window.open(data.listing_url, "_blank");
      }
      
      // Reload history to update publication status
      fetchCreations();
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setPublishingId(null);
    }
  };

  const filteredCreations = creations.filter(c => {
    const term = searchQuery.toLowerCase();
    return (
      (c.theme && c.theme.toLowerCase().includes(term)) ||
      (c.title_fr && c.title_fr.toLowerCase().includes(term)) ||
      (c.title_en && c.title_en.toLowerCase().includes(term))
    );
  });

  const formatDate = (isoString: string) => {
    const d = new Date(isoString);
    return d.toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  if (loading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center space-y-4">
        <RefreshCw className="h-10 w-10 text-indigo-500 animate-spin" />
        <p className="text-slate-400">Chargement de l&apos;historique...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
            Tableau de Bord
          </h1>
          <p className="text-slate-400">Suivez et gérez l&apos;ensemble de vos créations locales et publications Etsy.</p>
        </div>

        {/* Search bar */}
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-500" />
          <input
            type="text"
            placeholder="Rechercher un motif..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm rounded-xl glass-input placeholder:text-slate-600"
          />
        </div>
      </div>

      {notification && (
        <div className={`p-4 rounded-xl flex items-start space-x-3 border ${
          notification.type === "success" 
            ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/20" 
            : "bg-rose-950/40 text-rose-300 border-rose-500/20"
        } max-w-2xl`}>
          {notification.type === "success" ? (
            <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0" />
          )}
          <div className="flex-1 text-sm font-medium">{notification.message}</div>
          <button onClick={() => setNotification(null)} className="text-xs font-bold hover:underline opacity-80">
            Fermer
          </button>
        </div>
      )}

      {/* Grid listing */}
      {filteredCreations.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800/40">
          <ShoppingBag className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-300">Aucune création trouvée</h3>
          <p className="text-slate-500 text-sm mt-1">
            {searchQuery ? "Aucun motif ne correspond à vos filtres." : "Commencez à créer des motifs à la page de création !"}
          </p>
          {!searchQuery && (
            <Link 
              href="/" 
              className="inline-flex items-center space-x-1 text-sm font-bold text-indigo-400 hover:text-indigo-300 mt-4"
            >
              <span>Créer mon premier motif</span>
              <span>&rarr;</span>
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCreations.map((item) => (
            <div 
              key={item.id} 
              className="glass-panel rounded-2xl overflow-hidden flex flex-col justify-between group transition hover:border-slate-700/60"
            >
              {/* Media Thumbnail Container */}
              <div className="relative aspect-square w-full bg-slate-950/40 flex items-center justify-center overflow-hidden border-b border-slate-900">
                {item.mockup_path ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={assetUrl(item.mockup_path)}
                    alt={item.theme || "Laser pattern mockup"}
                    className="object-cover w-full h-full group-hover:scale-105 transition duration-500"
                  />
                ) : item.source_png_path ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={assetUrl(item.source_png_path)}
                    alt="Raw PNG preview"
                    className="object-contain max-h-[70%] w-auto opacity-70 p-4"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-slate-700">
                    <FileArchive className="h-12 w-12" />
                    <span className="text-xs mt-2">Aucun rendu visuel</span>
                  </div>
                )}

                {/* Date overlay tag */}
                <div className="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md px-2.5 py-1 rounded-lg text-[10px] text-slate-300 font-semibold border border-slate-800 flex items-center space-x-1.5">
                  <Calendar className="h-3 w-3 text-slate-400" />
                  <span>{formatDate(item.timestamp)}</span>
                </div>

                {/* Publication status tag */}
                <div className="absolute top-3 right-12">
                  {item.is_published_etsy ? (
                    <span className="bg-emerald-950/80 backdrop-blur-md text-emerald-400 border border-emerald-500/30 text-[10px] font-bold px-2.5 py-1 rounded-lg">
                      Publié Etsy
                    </span>
                  ) : (
                    <span className="bg-amber-950/80 backdrop-blur-md text-amber-400 border border-amber-500/30 text-[10px] font-bold px-2.5 py-1 rounded-lg">
                      Non publié
                    </span>
                  )}
                </div>

                {/* Delete button - top right */}
                <button
                  onClick={(e) => handleDelete(item.id, e)}
                  disabled={deletingId === item.id}
                  className="absolute top-3 right-3 z-10 bg-rose-950/80 hover:bg-rose-900/80 backdrop-blur-md text-rose-400 border border-rose-500/30 p-1.5 rounded-lg transition opacity-0 group-hover:opacity-100 disabled:opacity-50"
                  title="Supprimer cette création"
                >
                  {deletingId === item.id ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>

              {/* Description & Details Info */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-slate-200 line-clamp-1">
                    {item.theme || "Design sans thème"}
                  </h3>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    {item.title_fr || "Titre non rédigé."}
                  </p>
                </div>

                {/* Listing Action buttons */}
                <div className="space-y-2.5 pt-2 border-t border-slate-900">
                  <div className="flex items-center space-x-2">
                    <Link
                      href={`/review/${item.id}`}
                      className="flex-1 flex items-center justify-center space-x-1.5 bg-slate-800 hover:bg-slate-750 border border-slate-700/50 text-slate-200 py-2 rounded-xl text-xs font-semibold transition"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      <span>Revoir & Éditer</span>
                    </Link>

                    {item.zip_path && (
                      <a
                        href={apiUrl(`/api/creations/${item.id}/download/zip`)}
                        className="flex items-center justify-center bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/20 text-indigo-300 p-2 rounded-xl transition"
                        title="Télécharger le package .ZIP"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    )}
                  </div>

                  {!item.is_published_etsy && (
                    <button
                      onClick={() => handlePublish(item.id)}
                      disabled={publishingId === item.id || !item.zip_path || !item.mockup_path}
                      className="w-full flex items-center justify-center space-x-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2 rounded-xl text-xs font-bold transition shadow-sm"
                    >
                      {publishingId === item.id ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <ShoppingBag className="h-3.5 w-3.5" />
                      )}
                      <span>Publier sur Etsy</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

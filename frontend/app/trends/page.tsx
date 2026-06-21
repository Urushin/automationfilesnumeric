"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiUrl } from '@/lib/api';
import { TrendProductCard, TrendItem } from '@/components/TrendProductCard';
import { TrendingUp, RefreshCw, Zap, Star, Lightbulb, Calendar } from 'lucide-react';

export default function TrendsDashboard() {
  const router = useRouter();
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [progressMsg, setProgressMsg] = useState("");
  const [selectedSeason, setSelectedSeason] = useState<string>("Tous");

  const getSystemSeason = () => {
    const month = new Date().getMonth() + 1; // 1-12
    if ([12, 1, 2].includes(month)) return "Hiver / Noël";
    if ([3, 4, 5].includes(month)) return "Printemps / Fête des mères";
    if ([6, 7, 8].includes(month)) return "Été / Vacances / Mariage";
    return "Automne / Halloween";
  };

  useEffect(() => {
    setSelectedSeason(getSystemSeason());
  }, []);

  const fetchTrends = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/scraper/trends?limit=100'));
      if (res.ok) {
        const data = await res.json();
        setTrends(data);
      }
    } catch (error) {
      console.error("Failed to fetch trends", error);
    } finally {
      setLoading(false);
    }
  };

  const triggerScrape = () => {
    if (triggering) return;
    setTriggering(true);
    setProgressMsg("Connexion au processus de recherche...");

    const eventSource = new EventSource(apiUrl('/api/scraper/stream'));
    let isDone = false;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.msg) setProgressMsg(data.msg);

        if (data.done) {
          isDone = true;
          eventSource.close();
          setTriggering(false);
          setTimeout(() => setProgressMsg(""), 4000);
          fetchTrends();
        }
      } catch (err) {
        console.error("SSE Parse Error", err);
      }
    };

    eventSource.onerror = (error) => {
      console.error("EventSource Error", error);
      eventSource.close();
      if (!isDone) {
        setTriggering(false);
        setProgressMsg("Une erreur réseau est survenue.");
        setTimeout(() => setProgressMsg(""), 4000);
      }
    };
  };

  const handleGenerate = (item: TrendItem) => {
    // Injecter dans le pipeline de création
    router.push(`/?theme=${encodeURIComponent(item.title)}&image_url=${encodeURIComponent(item.thumbnail_url || "")}&inject=true`);
  };

  useEffect(() => {
    fetchTrends();
  }, []);

  // Fonction de filtrage saisonnier
  const filterBySeason = (item: TrendItem) => {
    if (selectedSeason === "Tous" || !selectedSeason) return true;
    const cat = item.category || "General";
    
    if (selectedSeason === "Hiver / Noël") {
      return ["Christmas", "Winter", "Valentine"].includes(cat);
    }
    if (selectedSeason === "Printemps / Pâques") {
      return ["Spring", "Mother", "Easter", "Wedding"].includes(cat);
    }
    if (selectedSeason === "Été / Vacances / Mariage") {
      return ["Summer", "BackToSchool"].includes(cat);
    }
    if (selectedSeason === "Automne / Halloween") {
      return ["Autumn", "Halloween"].includes(cat);
    }
    return cat === "General";
  };

  const filteredTrends = trends.filter(filterBySeason);
  const trendingNow = filteredTrends.filter(t => t.section === "trending");
  const popularAllTime = filteredTrends.filter(t => t.section === "popular");
  const ideas = filteredTrends.filter(t => t.section === "ideas");

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <TrendingUp className="h-8 w-8 text-rose-400" />
            Tendances Actuelles
          </h1>
          <p className="text-slate-400 mt-2">
            Découvrez les designs de découpe laser les plus populaires (Scores calculés via l'API & Badges Bestsellers).
          </p>
        </div>
        <button
          onClick={triggerScrape}
          disabled={triggering}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 transition"
        >
          <RefreshCw className={`h-4 w-4 ${triggering ? 'animate-spin' : ''}`} />
          {triggering ? 'Recherche en cours...' : 'Actualiser les tendances'}
        </button>
      </div>

      {triggering && progressMsg && (
        <div className="bg-indigo-500/20 border border-indigo-500/30 rounded-lg p-4 mb-6 flex items-center gap-3 shadow-sm">
          <RefreshCw className="h-5 w-5 text-indigo-400 animate-spin flex-shrink-0" />
          <span className="text-indigo-200 font-medium">{progressMsg}</span>
        </div>
      )}

      {/* Filtres Saisonniers (Onglets style Pinterest) */}
      <div className="flex flex-wrap gap-2 mb-8 p-1.5 bg-slate-900/60 border border-slate-800/60 rounded-xl w-full max-w-fit backdrop-blur-sm">
        {["Tous", "Printemps / Pâques", "Été / Vacances / Mariage", "Automne / Halloween", "Hiver / Noël"].map((season) => (
          <button
            key={season}
            onClick={() => setSelectedSeason(season)}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition duration-200 flex items-center gap-1.5 ${
              selectedSeason === season
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
            }`}
          >
            <Calendar className="h-3.5 w-3.5" />
            {season}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center text-slate-400 py-20 flex flex-col items-center">
          <RefreshCw className="h-8 w-8 animate-spin mb-4 text-indigo-400" />
          Chargement de la base d'idées...
        </div>
      ) : (
        <div className="space-y-16">

          {/* RUBRIQUE 1 : TENDANCES DU MOMENT */}
          <section>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Zap className="text-yellow-400 h-6 w-6" /> Tendances du moment
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {trendingNow.map(item => (
                <TrendProductCard key={item.id} item={item} onGenerate={handleGenerate} />
              ))}
            </div>
          </section>

          {/* RUBRIQUE 2 : LES PLUS POPULAIRES */}
          <section>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Star className="text-orange-400 h-6 w-6" /> Les Plus Populaires (Général)
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {popularAllTime.map(item => (
                <TrendProductCard key={item.id} item={item} onGenerate={handleGenerate} />
              ))}
            </div>
          </section>

          {/* RUBRIQUE 3 : IDÉES DE PROJETS */}
          <section>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Lightbulb className="text-blue-400 h-6 w-6" /> Idées de concepts
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {ideas.map(item => (
                <TrendProductCard key={item.id} item={item} onGenerate={handleGenerate} />
              ))}
            </div>
          </section>

          {trends.length === 0 && (
            <div className="col-span-full text-center text-slate-500 py-10 bg-slate-900/30 rounded-xl border border-slate-800">
              Aucune tendance disponible pour le moment. Cliquez sur "Actualiser".
            </div>
          )}
        </div>
      )}
    </div>
  );
}
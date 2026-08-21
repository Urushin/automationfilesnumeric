"use client";

import React, { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api";
import Link from "next/link";
import {
  Save, Settings as SettingsIcon, Image as ImageIcon,
  FileText, Wrench, Zap, Star, Gift, ChevronDown, Store, Shield,
  HardDrive, Trash2,
} from "lucide-react";

// ── Generation profile presets ──────────────────────────────────────────────
const PROFILES = {
  pro: {
    label: "🎨 Mode Studio (Pro)",
    description: "Meilleure qualité — Claude Haiku + GPT Image 2 (pro)",
    image_ai_provider: "gpt-image-2",
    stencil_image_provider: "gpt-image-2",
    mockup_image_provider: "gpt-image-2",
    stencil_image_quality: "auto",
    mockup_image_quality: "auto",
    text_ai_provider: "claude-3-5-haiku",
  },
  eco: {
    label: "⚡ Mode Artisan (Rentable)",
    description: "Équilibré — GPT-4o-mini + Flux Pro (eco)",
    image_ai_provider: "black-forest-labs-flux-pro",
    stencil_image_provider: "black-forest-labs-flux-pro",
    mockup_image_provider: "black-forest-labs-flux-pro",
    stencil_image_quality: "low",
    mockup_image_quality: "low",
    text_ai_provider: "gpt-4o-mini",
  },
  free: {
    label: "🆓 Mode Gratuit",
    description: "Quota Free — Gemini Flash + HF FLUX Schnell (free)",
    image_ai_provider: "huggingface-flux-free",
    stencil_image_provider: "huggingface-flux-free",
    mockup_image_provider: "huggingface-flux-free",
    stencil_image_quality: "auto",
    mockup_image_quality: "auto",
    text_ai_provider: "gemini-2.0-flash",
  },
};

const INPUT_CLS =
  "p-3 rounded-lg bg-slate-800 text-white border border-slate-700 outline-none focus:border-indigo-500 transition";

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
        {icon}
        {title}
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">{children}</div>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm text-slate-400">{label}</label>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [testingBinaries, setTestingBinaries] = useState(false);

  useEffect(() => {
    fetch(apiUrl("/api/settings"))
      .then((res) => res.json())
      .then((data) => {
        setSettings(data);
        setLoading(false);
      });

    // Check query params for Etsy connection status
    const params = new URLSearchParams(window.location.search);
    if (params.get("etsy_connect") === "success") {
      setToast({ msg: "Connexion Etsy réussie ! 🛒", ok: true });
      setTimeout(() => setToast(null), 4000);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const testBinaries = async () => {
    setTestingBinaries(true);
    try {
      const res = await fetch(apiUrl("/api/settings/test-binaries"), { method: "POST" });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const pOk = data.potrace?.status === "OK";
      const iOk = data.inkscape?.status === "OK";
      if (pOk && iOk) {
        setToast({ msg: "Potrace & Inkscape sont opérationnels ! ✔", ok: true });
      } else {
        const errors = [];
        if (!pOk) errors.push("Potrace");
        if (!iOk) errors.push("Inkscape");
        setToast({ msg: `Échec : ${errors.join(" & ")} introuvable(s). ❌`, ok: false });
      }
    } catch {
      setToast({ msg: "Erreur lors du test des binaires.", ok: false });
    } finally {
      setTestingBinaries(false);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const applyProfile = (key: keyof typeof PROFILES) => {
    const p = PROFILES[key];
    setSettings((s: any) => ({
      ...s,
      image_ai_provider: p.image_ai_provider,
      stencil_image_provider: p.stencil_image_provider,
      mockup_image_provider: p.mockup_image_provider,
      stencil_image_quality: p.stencil_image_quality,
      mockup_image_quality: p.mockup_image_quality,
      text_ai_provider: p.text_ai_provider,
    }));
  };

  const [storageStats, setStorageStats] = useState<any>(null);
  const [purgingStorage, setPurgingStorage] = useState(false);

  const loadStorageStats = () => {
    fetch(apiUrl("/api/settings/storage-stats"))
      .then((res) => res.json())
      .then((data) => setStorageStats(data))
      .catch(() => {});
  };

  useEffect(() => {
    loadStorageStats();
  }, []);

  const handlePurgeStorage = async () => {
    if (!confirm("Voulez-vous supprimer les fichiers temporaires et caches de calcul ? Vos fichiers finaux (SVG, DXF, PNG, Mockups, ZIP) seront strictement préservés.")) return;
    setPurgingStorage(true);
    try {
      const res = await fetch(apiUrl("/api/settings/purge-storage"), { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setToast({ msg: `Purge terminée : ${data.deleted_files_count} fichier(s) temporaire(s) supprimé(s) (${data.freed_space_mb} Mo libérés) ✔`, ok: true });
        loadStorageStats();
      } else {
        setToast({ msg: "Erreur lors de la purge.", ok: false });
      }
    } catch {
      setToast({ msg: "Erreur réseau lors de la purge.", ok: false });
    } finally {
      setPurgingStorage(false);
      setTimeout(() => setToast(null), 4500);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const res = await fetch(apiUrl("/api/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      setToast({ msg: res.ok ? "Paramètres sauvegardés ✔" : "Erreur lors de la sauvegarde.", ok: res.ok });
    } catch {
      setToast({ msg: "Erreur réseau.", ok: false });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3500);
    }
  };


  if (loading)
    return (
      <div className="text-slate-400 p-10 text-center animate-pulse">
        Chargement des configurations...
      </div>
    );

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-5 right-5 z-50 px-5 py-3 rounded-xl font-medium shadow-xl transition-all ${
            toast.ok ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <SettingsIcon className="text-indigo-400 h-8 w-8" />
          Configuration universelle
        </h1>
        <Link
          href="/settings/prompts"
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-650 hover:bg-indigo-600 border border-indigo-500/40 text-white font-bold rounded-xl text-xs transition duration-200 shadow-md hover:shadow-indigo-500/10 cursor-pointer select-none"
        >
          <FileText className="h-4 w-4 text-indigo-300" />
          Gérer les Prompts
        </Link>
      </div>

      {/* ── Profile presets ─────────────────────────────────────────────── */}
      <div className="mb-8">
        <p className="text-sm text-slate-400 mb-3 flex items-center gap-1">
          <Zap className="h-4 w-4 text-amber-400" /> Profils de génération (applique les providers recommandés)
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(PROFILES).map(([key, p]) => (
            <button
              key={key}
              onClick={() => applyProfile(key as keyof typeof PROFILES)}
              className="text-left p-4 rounded-xl border border-slate-700 bg-slate-800/60 hover:border-indigo-500 hover:bg-slate-800 transition group"
            >
              <div className="font-bold text-white text-base mb-1">{p.label}</div>
              <div className="text-xs text-slate-400 group-hover:text-slate-300">{p.description}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-8 bg-slate-900/50 p-8 rounded-2xl border border-slate-800 shadow-xl">

        {/* ── Image providers ───────────────────────────────────────────── */}
        <Section
          icon={<ImageIcon className="text-rose-400 h-6 w-6" />}
          title="Génération d'Images (Pochoirs & Mockups)"
        >
          <Field label="Modèle pour les Pochoirs (Stencils)">
            <select
              value={settings.stencil_image_provider || settings.image_ai_provider || "huggingface-flux-free"}
              onChange={(e) => setSettings({ ...settings, stencil_image_provider: e.target.value, image_ai_provider: e.target.value })}
              className={INPUT_CLS}
            >
              <optgroup label="OpenAI (Série GPT Image)">
                <option value="gpt-image-2">GPT Image 2 ⭐ (haut de gamme, thinking)</option>
                <option value="gpt-image-1.5">GPT Image 1.5 (équilibré)</option>
                <option value="gpt-image-1">GPT Image 1</option>
                <option value="gpt-image-1-mini">GPT Image 1 Mini (économique)</option>
              </optgroup>
              <optgroup label="Google">
                <option value="imagen-3-generate">Imagen 3 Generate</option>
                <option value="imagen-3-edit">Imagen 3 Edit</option>
              </optgroup>
              <optgroup label="Replicate">
                <option value="black-forest-labs-flux-pro">Flux Pro ⭐ (recommandé)</option>
                <option value="stable-diffusion-xl-core">SDXL Core</option>
                <option value="stable-diffusion-3-pro">SD 3 Pro</option>
                <option value="bria-2.3">Bria 2.3</option>
              </optgroup>
              <optgroup label="Hugging Face (Gratuit/économique)">
                <option value="huggingface-flux-free">HF FLUX.1-schnell (gratuit)</option>
              </optgroup>
              <optgroup label="Stability AI">
                <option value="stability">Stability AI SD3 (Stable Diffusion 3)</option>
              </optgroup>
              <optgroup label="Banana / Legacy">
                <option value="banana">Banana SDXL (img2img)</option>
              </optgroup>
            </select>
          </Field>

          <Field label="Modèle pour les Mockups">
            <select
              value={settings.mockup_image_provider || settings.image_ai_provider || "huggingface-flux-free"}
              onChange={(e) => setSettings({ ...settings, mockup_image_provider: e.target.value })}
              className={INPUT_CLS}
            >
              <optgroup label="OpenAI (Série GPT Image)">
                <option value="gpt-image-2">GPT Image 2 ⭐ (haut de gamme, thinking)</option>
                <option value="gpt-image-1.5">GPT Image 1.5 (équilibré)</option>
                <option value="gpt-image-1">GPT Image 1</option>
                <option value="gpt-image-1-mini">GPT Image 1 Mini (économique)</option>
              </optgroup>
              <optgroup label="Google">
                <option value="imagen-3-generate">Imagen 3 Generate</option>
                <option value="imagen-3-edit">Imagen 3 Edit</option>
              </optgroup>
              <optgroup label="Replicate">
                <option value="black-forest-labs-flux-pro">Flux Pro ⭐ (recommandé)</option>
                <option value="stable-diffusion-xl-core">SDXL Core</option>
                <option value="stable-diffusion-3-pro">SD 3 Pro</option>
                <option value="bria-2.3">Bria 2.3</option>
              </optgroup>
              <optgroup label="Hugging Face (Gratuit/économique)">
                <option value="huggingface-flux-free">HF FLUX.1-schnell (gratuit)</option>
              </optgroup>
              <optgroup label="Stability AI">
                <option value="stability">Stability AI SD3 (Stable Diffusion 3)</option>
              </optgroup>
              <optgroup label="Banana / Legacy">
                <option value="banana">Banana SDXL (img2img)</option>
              </optgroup>
            </select>
          </Field>

          <Field label="Qualité de Génération OpenAI GPT Image (Pochoirs)">
            <select
              value={settings.stencil_image_quality || "auto"}
              onChange={(e) => setSettings({ ...settings, stencil_image_quality: e.target.value })}
              className={INPUT_CLS}
            >
              <option value="low">Low (Économique et sans micro-détails parasites - Recommandé)</option>
              <option value="medium">Medium (Compromis détails modérés)</option>
              <option value="high">High (Très cher - Haute fidélité)</option>
              <option value="auto">Auto (L'IA choisit le meilleur compromis)</option>
            </select>
          </Field>

          <Field label="Qualité de Génération OpenAI GPT Image (Mockups)">
            <select
              value={settings.mockup_image_quality || "auto"}
              onChange={(e) => setSettings({ ...settings, mockup_image_quality: e.target.value })}
              className={INPUT_CLS}
            >
              <option value="low">Low (Économique et sans micro-détails parasites - Recommandé)</option>
              <option value="medium">Medium (Compromis détails modérés)</option>
              <option value="high">High (Très cher - Haute fidélité)</option>
              <option value="auto">Auto (L'IA choisit le meilleur compromis)</option>
            </select>
          </Field>

          <Field label="Clé API Stability AI (SD3)">
            <input
              id="stability_key"
              type="password"
              value={settings.stability_key || ""}
              onChange={(e) => setSettings({ ...settings, stability_key: e.target.value })}
              placeholder="sk-..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API OpenAI (DALL-E)">
            <input
              id="openai_key"
              type="password"
              value={settings.openai_key || ""}
              onChange={(e) => setSettings({ ...settings, openai_key: e.target.value })}
              placeholder="sk-proj-..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API Google Gemini / Imagen">
            <input
              id="gemini_key_image"
              type="password"
              value={settings.gemini_key || ""}
              onChange={(e) => setSettings({ ...settings, gemini_key: e.target.value })}
              placeholder="AIzaSy..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API Replicate (Flux, SDXL, Bria…)">
            <input
              id="replicate_key"
              type="password"
              value={settings.replicate_key || ""}
              onChange={(e) => setSettings({ ...settings, replicate_key: e.target.value })}
              placeholder="r8_..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API OpenRouter">
            <input
              id="openrouter_key"
              type="password"
              value={settings.openrouter_key || ""}
              onChange={(e) => setSettings({ ...settings, openrouter_key: e.target.value })}
              placeholder="sk-or-v1-..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API Hugging Face">
            <input
              id="huggingface_key"
              type="password"
              value={settings.huggingface_key || ""}
              onChange={(e) => setSettings({ ...settings, huggingface_key: e.target.value })}
              placeholder="hf_..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API Banana (SDXL img2img)">
            <input
              id="banana_key"
              type="password"
              value={settings.banana_key || ""}
              onChange={(e) => setSettings({ ...settings, banana_key: e.target.value })}
              placeholder="sk-..."
              className={INPUT_CLS}
            />
          </Field>
        </Section>

        <hr className="border-slate-800" />

        {/* ── Text / SEO providers ──────────────────────────────────────── */}
        <Section
          icon={<FileText className="text-emerald-400 h-6 w-6" />}
          title="Génération de Texte & Vision (SEO — litellm)"
        >
          <Field label="Fournisseur de Texte/Vision Préféré">
            <select
              value={settings.text_ai_provider || "gemini-2.0-flash"}
              onChange={(e) => setSettings({ ...settings, text_ai_provider: e.target.value })}
              className={INPUT_CLS}
            >
              <optgroup label="Anthropic (Claude)">
                <option value="claude-3-5-haiku">Claude 3.5 Haiku ⚡ (rapide, économique)</option>
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet ⭐ (premium)</option>
                <option value="claude-3-opus">Claude 3 Opus (puissant)</option>
              </optgroup>
              <optgroup label="OpenAI">
                <option value="gpt-4o">GPT-4o (vision)</option>
                <option value="gpt-4o-mini">GPT-4o-mini (économique)</option>
              </optgroup>
              <optgroup label="Google (Gemini)">
                <option value="gemini-2.0-flash">Gemini 2.0 Flash ⚡ (gratuit/quota)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (vision)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite (ultra-économique)</option>
              </optgroup>
              <optgroup label="Mistral">
                <option value="mistral-large-latest">Mistral Large (bilingue)</option>
                <option value="mistral-small-latest">Mistral Small (léger)</option>
              </optgroup>
              <optgroup label="OpenRouter (Meta LLaMA)">
                <option value="llama-3-70b-instruct-openrouter">LLaMA 3 70B (gratuit via OpenRouter)</option>
              </optgroup>
            </select>
          </Field>

          <Field label="Clé API Anthropic (Claude)">
            <input
              id="anthropic_key"
              type="password"
              value={settings.anthropic_key || ""}
              onChange={(e) => setSettings({ ...settings, anthropic_key: e.target.value })}
              placeholder="sk-ant-..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API Google Gemini (SEO/Vision)">
            <input
              id="gemini_key"
              type="password"
              value={settings.gemini_key || ""}
              onChange={(e) => setSettings({ ...settings, gemini_key: e.target.value })}
              placeholder="AIzaSy..."
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Clé API Mistral">
            <input
              id="mistral_key"
              type="password"
              value={settings.mistral_key || ""}
              onChange={(e) => setSettings({ ...settings, mistral_key: e.target.value })}
              placeholder="MISTRAL_API_KEY"
              className={INPUT_CLS}
            />
          </Field>
        </Section>

        <hr className="border-slate-800" />

        {/* ── Etsy Integration ──────────────────────────────────────────── */}
        <Section
          icon={<Store className="text-amber-400 h-6 w-6" />}
          title="Intégration Etsy (Publication automatique)"
        >
          <Field label="Etsy API Keystring (Client ID)">
            <input
              id="etsy_client_id"
              type="text"
              value={settings.etsy_client_id || ""}
              onChange={(e) => setSettings({ ...settings, etsy_client_id: e.target.value })}
              placeholder="okz43zxofym53cz5acokxqrk"
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Etsy API Shared Secret (Client Secret)">
            <input
              id="etsy_client_secret"
              type="password"
              value={settings.etsy_client_secret || ""}
              onChange={(e) => setSettings({ ...settings, etsy_client_secret: e.target.value })}
              placeholder="tozeexfwvt"
              className={INPUT_CLS}
            />
          </Field>

          <Field label="Connexion OAuth Etsy">
            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={async () => {
                  try {
                    const res = await fetch(apiUrl("/api/etsy/login"));
                    if (!res.ok) {
                      const err = await res.json();
                      alert("Erreur : " + (err.detail || "Impossible de générer le lien OAuth."));
                      return;
                    }
                    const data = await res.json();
                    if (data.url) {
                      window.location.href = data.url;
                    }
                  } catch (err) {
                    alert("Erreur réseau : " + (err as Error).message);
                  }
                }}
                className="px-5 py-3 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-xl transition text-sm flex items-center justify-center gap-2"
              >
                <Store className="h-4 w-4" />
                Se connecter à Etsy (OAuth)
              </button>
              <p className="text-[10px] text-slate-500 leading-relaxed">
                Cliquez sur ce bouton pour être redirigé vers Etsy et autoriser l'application.
                Assurez-vous d'avoir enregistré le Keystring et Shared Secret ci-dessus avant de cliquer.
              </p>
            </div>
          </Field>

          <Field label="Statut de connexion">
            <div className="flex items-center gap-2 text-sm">
              {settings.etsy_oauth_token && !settings.etsy_oauth_token.startsWith("temp:") ? (
                <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block"></span>
                  Connecté à Etsy
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-slate-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-slate-600 inline-block"></span>
                  Non connecté
                </span>
              )}
              {settings.etsy_oauth_token && !settings.etsy_oauth_token.startsWith("temp:") && (
                <button
                  type="button"
                  onClick={async () => {
                    if (confirm("Voulez-vous vraiment déconnecter Etsy ?")) {
                      const updated = { ...settings, etsy_oauth_token: "" };
                      setSettings(updated);
                      setSaving(true);
                      try {
                        const res = await fetch(apiUrl("/api/settings"), {
                          method: "PUT",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify(updated),
                        });
                        setToast({ msg: res.ok ? "Etsy déconnecté avec succès ✔" : "Erreur lors de la déconnexion.", ok: res.ok });
                      } catch {
                        setToast({ msg: "Erreur réseau.", ok: false });
                      } finally {
                        setSaving(false);
                        setTimeout(() => setToast(null), 3500);
                      }
                    }
                  }}
                  className="text-[10px] text-rose-400 hover:text-rose-300 underline ml-2"
                >
                  Déconnecter
                </button>
              )}
            </div>
          </Field>

          <Field label="Paramètres par défaut de publication">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-500">Prix par défaut (€)</label>
                <input
                  type="number"
                  min="0.50"
                  max="999"
                  step="0.50"
                  value={settings.default_price ?? 3.0}
                  onChange={(e) => setSettings({ ...settings, default_price: parseFloat(e.target.value) || 3.0 })}
                  className={INPUT_CLS}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-500">Stock par défaut</label>
                <input
                  type="number"
                  min="1"
                  max="999"
                  value={settings.default_quantity ?? 999}
                  onChange={(e) => setSettings({ ...settings, default_quantity: parseInt(e.target.value) || 999 })}
                  className={INPUT_CLS}
                />
              </div>
            </div>
          </Field>

          <Field label="Statut de publication par défaut">
            <select
              value={settings.default_status || "draft"}
              onChange={(e) => setSettings({ ...settings, default_status: e.target.value })}
              className={INPUT_CLS}
            >
              <option value="draft">Brouillon (draft) — Recommandé</option>
              <option value="active">Actif (active) — Publié immédiatement</option>
            </select>
          </Field>
        </Section>

        <hr className="border-slate-800" />

        {/* ── Filigrane & Protection d'Images ─────────────────────────── */}
        <Section
          icon={<Shield className="text-emerald-400 h-6 w-6" />}
          title="Filigrane & Protection d'Images (Anti-Vol Etsy)"
        >
          <Field label="Texte du Filigrane">
            <input
              id="watermark_text"
              type="text"
              value={settings.watermark_text ?? "digitalfilesbymop"}
              onChange={(e) => setSettings({ ...settings, watermark_text: e.target.value })}
              placeholder="digitalfilesbymop"
              className={INPUT_CLS}
            />
            <p className="text-[10px] text-slate-500">
              Texte imprimé en diagonale semi-transparente sur les aperçus Etsy pour empêcher le vol de vos créations.
            </p>
          </Field>

          <Field label="Activation du Filigrane par Défaut">
            <div className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg border border-slate-700">
              <input
                id="default_apply_watermark"
                type="checkbox"
                checked={settings.default_apply_watermark ?? false}
                onChange={(e) => setSettings({ ...settings, default_apply_watermark: e.target.checked })}
                className="h-5 w-5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
              />
              <label htmlFor="default_apply_watermark" className="text-sm text-slate-300 cursor-pointer">
                Appliquer le filigrane par défaut sur les mockups Etsy
              </label>
            </div>
            <p className="text-[10px] text-slate-500">
              Option cochable et modifiable à tout moment lors du lancement ou de la révision.
            </p>
          </Field>
        </Section>

        <hr className="border-slate-800" />

        {/* ── CLI / System paths ───────────────────────────────────────── */}
        <Section
          icon={<Wrench className="text-blue-400 h-6 w-6" />}
          title="Système & Chemins CLI"
        >
          <Field label="Chemin Potrace">
            <input
              id="potrace_path"
              type="text"
              value={settings.potrace_path || ""}
              onChange={(e) => setSettings({ ...settings, potrace_path: e.target.value })}
              className={INPUT_CLS}
            />
          </Field>
          <Field label="Chemin Inkscape">
            <input
              id="inkscape_path"
              type="text"
              value={settings.inkscape_path || ""}
              onChange={(e) => setSettings({ ...settings, inkscape_path: e.target.value })}
              className={INPUT_CLS}
            />
          </Field>
          <div className="col-span-1 md:col-span-2 flex justify-end">
            <button
              type="button"
              onClick={testBinaries}
              disabled={testingBinaries}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-bold rounded-xl transition duration-200 cursor-pointer"
            >
              {testingBinaries ? "Test en cours..." : "Tester la connexion des binaires CLI"}
            </button>
          </div>
        </Section>

        <hr className="border-slate-800" />

        {/* ── Maintenance & Stockage Disque ───────────────────────────── */}
        <Section
          icon={<HardDrive className="text-purple-400 h-6 w-6" />}
          title="Maintenance & Stockage Disque (Storage/)"
        >
          <div className="p-4 bg-slate-800/80 rounded-xl border border-slate-700 space-y-2">
            <div className="text-xs text-slate-400 font-semibold">Espace total occupé :</div>
            <div className="text-xl font-bold text-white font-mono">
              {storageStats ? `${storageStats.total_size_mb} Mo` : "Calcul en cours..."}
            </div>
            <div className="text-[11px] text-slate-400">
              {storageStats ? `${storageStats.total_files} fichiers dans ${storageStats.creation_folders_count} dossiers de créations` : ""}
            </div>
          </div>

          <div className="p-4 bg-slate-800/80 rounded-xl border border-slate-700 flex flex-col justify-between gap-3">
            <div>
              <div className="text-xs text-slate-400 font-semibold">Fichiers temporaires & caches :</div>
              <div className="text-lg font-bold text-amber-400 font-mono">
                {storageStats ? `${storageStats.temp_size_mb} Mo (${storageStats.temp_files_count} fichiers)` : "..."}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">
                Fonds IA intermédiaires, fragments de découpe et fichiers .tmp
              </div>
            </div>

            <button
              type="button"
              onClick={handlePurgeStorage}
              disabled={purgingStorage}
              className="w-full py-2.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4 text-rose-400" />
              {purgingStorage ? "Nettoyage en cours..." : "Purger les fichiers temporaires"}
            </button>
          </div>
        </Section>

        <button
          id="save-settings-btn"
          onClick={saveSettings}
          disabled={saving}
          className="w-full mt-6 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white py-4 rounded-xl font-bold transition shadow-md"
        >
          <Save className="h-6 w-6" />
          {saving ? "Sauvegarde en cours..." : "Sauvegarder la configuration"}
        </button>
      </div>
    </div>
  );
}

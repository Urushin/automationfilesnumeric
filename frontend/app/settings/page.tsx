"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { 
  Key, 
  Settings as SettingsIcon, 
  Terminal, 
  Tag, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  AlertCircle, 
  Link2 
} from "lucide-react";
import { apiUrl } from "@/lib/api";

interface BinaryTestResult {
  status: "OK" | "FAILED";
  path: string;
  error: string | null;
}

interface BinaryResults {
  potrace: BinaryTestResult;
  inkscape: BinaryTestResult;
}

function SettingsContent() {
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingBinaries, setTestingBinaries] = useState(false);
  const [binaryResults, setBinaryResults] = useState<BinaryResults | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form states
  const [openaiKey, setOpenaiKey] = useState("");
  const [mistralKey, setMistralKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [etsyClientId, setEtsyClientId] = useState("");
  const [etsyClientSecret, setEtsyClientSecret] = useState("");
  const [etsyOauthToken, setEtsyOauthToken] = useState("");
  const [defaultPrice, setDefaultPrice] = useState(3.0);
  const [defaultQuantity, setDefaultQuantity] = useState(999);
  const [defaultStatus, setDefaultStatus] = useState("draft");
  const [potracePath, setPotracePath] = useState("potrace");
  const [inkscapePath, setInkscapePath] = useState("inkscape");

  // Fetch Settings
  useEffect(() => {
    fetchSettings();
    
    // Check if redirect query param says success
    if (searchParams.get("etsy_connect") === "success") {
      setNotification({
        type: "success",
        message: "Votre compte Etsy a été connecté avec succès !"
      });
    }
  }, [searchParams]);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const res = await fetch(apiUrl("/api/settings"));
      if (!res.ok) throw new Error("Failed to load settings");
      const data = await res.json();
      
      setOpenaiKey(data.openai_key || "");
      setMistralKey(data.mistral_key || "");
      setGeminiKey(data.gemini_key || "");
      setEtsyClientId(data.etsy_client_id || "");
      setEtsyClientSecret(data.etsy_client_secret || "");
      setEtsyOauthToken(data.etsy_oauth_token || "");
      setDefaultPrice(data.default_price);
      setDefaultQuantity(data.default_quantity);
      setDefaultStatus(data.default_status);
      setPotracePath(data.potrace_path || "potrace");
      setInkscapePath(data.inkscape_path || "inkscape");
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Erreur de chargement" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      const res = await fetch(apiUrl("/api/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          openai_key: openaiKey,
          mistral_key: mistralKey,
          gemini_key: geminiKey,
          etsy_client_id: etsyClientId,
          etsy_client_secret: etsyClientSecret,
          default_price: parseFloat(defaultPrice.toString()),
          default_quantity: parseInt(defaultQuantity.toString()),
          default_status: defaultStatus,
          potrace_path: potracePath,
          inkscape_path: inkscapePath
        })
      });

      if (!res.ok) throw new Error("Failed to save settings");
      setNotification({ type: "success", message: "Configuration enregistrée avec succès !" });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Erreur d'enregistrement" });
    } finally {
      setSaving(false);
    }
  };

  const handleEtsyConnect = async () => {
    if (!etsyClientId) {
      setNotification({ type: "error", message: "Veuillez d'abord renseigner le Etsy Client ID et enregistrer." });
      return;
    }
    
    try {
      // First save settings
      await fetch(apiUrl("/api/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          openai_key: openaiKey,
          mistral_key: mistralKey,
          gemini_key: geminiKey,
          etsy_client_id: etsyClientId,
          etsy_client_secret: etsyClientSecret,
          default_price: parseFloat(defaultPrice.toString()),
          default_quantity: parseInt(defaultQuantity.toString()),
          default_status: defaultStatus,
          potrace_path: potracePath,
          inkscape_path: inkscapePath
        })
      });

      const res = await fetch(apiUrl("/api/etsy/login"));
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to generate auth URL");
      }
      const data = await res.json();
      // Redirect user to Etsy OAuth Login page
      window.location.href = data.url;
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Erreur de connexion Etsy" });
    }
  };

  const handleEtsyDisconnect = async () => {
    try {
      const res = await fetch(apiUrl("/api/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ etsy_oauth_token: "" })
      });
      if (!res.ok) throw new Error("Failed to clear Etsy connection");
      setEtsyOauthToken("");
      setNotification({ type: "success", message: "Compte Etsy déconnecté avec succès." });
    } catch (err: any) {
      setNotification({ type: "error", message: err.message });
    }
  };

  const testBinaries = async () => {
    try {
      setTestingBinaries(true);
      setBinaryResults(null);
      const res = await fetch(apiUrl("/api/settings/test-binaries"), {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to test binaries");
      const data = await res.json();
      setBinaryResults(data);
    } catch (err: any) {
      setNotification({ type: "error", message: err.message || "Erreur de test CLI" });
    } finally {
      setTestingBinaries(false);
    }
  };

  const isEtsyConnected = etsyOauthToken && 
    etsyOauthToken !== "" && 
    !etsyOauthToken.startsWith("temp:");

  if (loading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center space-y-4">
        <RefreshCw className="h-10 w-10 text-indigo-500 animate-spin" />
        <p className="text-slate-400">Chargement de la configuration...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
            Configuration
          </h1>
          <p className="text-slate-400">Gérez vos clés d&apos;API, vos préférences Etsy et vérifiez vos dépendances locales.</p>
        </div>
      </div>

      {notification && (
        <div className={`p-4 rounded-xl flex items-start space-x-3 border ${
          notification.type === "success" 
            ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/20" 
            : "bg-rose-950/40 text-rose-300 border-rose-500/20"
        }`}>
          {notification.type === "success" ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1 text-sm font-medium">{notification.message}</div>
          <button 
            onClick={() => setNotification(null)}
            className="text-xs font-bold hover:underline opacity-80"
          >
            Fermer
          </button>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* API Keys Panel */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Key className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold">Clés d&apos;API d&apos;Intelligence Artificielle</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">OpenAI API Key (DALL-E 3)</label>
              <input 
                type="password" 
                placeholder="sk-..." 
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>
            
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Gemini API Key (SEO)</label>
              <input 
                type="password" 
                placeholder="AIzaSy..." 
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>
            
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Mistral AI API Key (SEO)</label>
              <input 
                type="password" 
                placeholder="Mistral API Key" 
                value={mistralKey}
                onChange={(e) => setMistralKey(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>
          </div>
        </div>

        {/* Etsy API Setup */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Link2 className="h-5 w-5 text-rose-400" />
            <h2 className="text-lg font-bold">Intégration Marketplace Etsy</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Etsy Client ID (Keystring)</label>
              <input 
                type="text" 
                placeholder="Identifiant de l'application Etsy" 
                value={etsyClientId}
                onChange={(e) => setEtsyClientId(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Etsy Client Secret (Shared Secret)</label>
              <input 
                type="password" 
                placeholder="Clé secrète Etsy" 
                value={etsyClientSecret}
                onChange={(e) => setEtsyClientSecret(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>
          </div>

          <div className="bg-slate-900/60 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between border border-slate-800/40">
            <div className="mb-4 md:mb-0">
              <div className="text-sm font-semibold">Statut de la connexion</div>
              <div className="text-xs text-slate-400 mt-0.5">
                Authentification OAuth 2.0 PKCE sécurisée pour les fiches produits.
              </div>
            </div>

            {isEtsyConnected ? (
              <div className="flex items-center space-x-3">
                <span className="flex items-center space-x-1 text-xs px-2.5 py-1 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-500/25">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>Connecté à Etsy</span>
                </span>
                <button
                  type="button"
                  onClick={handleEtsyDisconnect}
                  className="text-xs font-semibold text-rose-400 hover:text-rose-300 transition"
                >
                  Déconnecter
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                  Déconnecté
                </span>
                <button
                  type="button"
                  onClick={handleEtsyConnect}
                  className="flex items-center space-x-1 text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white px-3 py-1.5 rounded-lg transition"
                >
                  <span>Connecter mon compte</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Default Etsy Listing Settings */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Tag className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold">Valeurs par défaut des Fiches Produits</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Prix de vente par défaut (€)</label>
              <input 
                type="number" 
                step="0.01" 
                value={defaultPrice}
                onChange={(e) => setDefaultPrice(parseFloat(e.target.value))}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Quantité disponible</label>
              <input 
                type="number" 
                value={defaultQuantity}
                onChange={(e) => setDefaultQuantity(parseInt(e.target.value))}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Statut de la fiche produit</label>
              <select 
                value={defaultStatus}
                onChange={(e) => setDefaultStatus(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              >
                <option value="draft">Brouillon (Draft)</option>
                <option value="active">Active (Publication directe)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Local CLI Binary Settings */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Terminal className="h-5 w-5 text-emerald-400" />
              <h2 className="text-lg font-bold">Dépendances Systèmes (CLI)</h2>
            </div>
            <button
              type="button"
              onClick={testBinaries}
              disabled={testingBinaries}
              className="flex items-center space-x-1 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 transition"
            >
              {testingBinaries && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
              <span>Tester les binaires</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Chemin Executable Potrace</label>
              <input 
                type="text" 
                placeholder="potrace" 
                value={potracePath}
                onChange={(e) => setPotracePath(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Chemin Executable Inkscape</label>
              <input 
                type="text" 
                placeholder="/Applications/Inkscape.app/Contents/MacOS/inkscape" 
                value={inkscapePath}
                onChange={(e) => setInkscapePath(e.target.value)}
                className="w-full rounded-lg px-4 py-2 text-sm glass-input"
              />
            </div>
          </div>

          {binaryResults && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
              {/* Potrace Diagnostic Result */}
              <div className={`p-4 rounded-xl border flex flex-col justify-between ${
                binaryResults.potrace.status === "OK" 
                  ? "bg-emerald-950/20 text-emerald-300 border-emerald-500/20" 
                  : "bg-rose-950/20 text-rose-300 border-rose-500/20"
              }`}>
                <div>
                  <div className="flex items-center space-x-2 font-bold text-sm">
                    {binaryResults.potrace.status === "OK" ? (
                      <CheckCircle2 className="h-4.5 w-4.5 text-emerald-400" />
                    ) : (
                      <XCircle className="h-4.5 w-4.5 text-rose-400" />
                    )}
                    <span>Potrace CLI : {binaryResults.potrace.status}</span>
                  </div>
                  {binaryResults.potrace.error && (
                    <p className="text-xs opacity-75 mt-1.5 leading-relaxed">{binaryResults.potrace.error}</p>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-2 truncate font-mono">
                  Chemin: {binaryResults.potrace.path}
                </div>
              </div>

              {/* Inkscape Diagnostic Result */}
              <div className={`p-4 rounded-xl border flex flex-col justify-between ${
                binaryResults.inkscape.status === "OK" 
                  ? "bg-emerald-950/20 text-emerald-300 border-emerald-500/20" 
                  : "bg-rose-950/20 text-rose-300 border-rose-500/20"
              }`}>
                <div>
                  <div className="flex items-center space-x-2 font-bold text-sm">
                    {binaryResults.inkscape.status === "OK" ? (
                      <CheckCircle2 className="h-4.5 w-4.5 text-emerald-400" />
                    ) : (
                      <XCircle className="h-4.5 w-4.5 text-rose-400" />
                    )}
                    <span>Inkscape CLI : {binaryResults.inkscape.status}</span>
                  </div>
                  {binaryResults.inkscape.error && (
                    <p className="text-xs opacity-75 mt-1.5 leading-relaxed">{binaryResults.inkscape.error}</p>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-2 truncate font-mono">
                  Chemin: {binaryResults.inkscape.path}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Submit Actions */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="glow-btn inline-flex items-center space-x-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 font-semibold transition disabled:opacity-50"
          >
            {saving ? (
              <>
                <RefreshCw className="h-5 w-5 animate-spin" />
                <span>Enregistrement...</span>
              </>
            ) : (
              <span>Enregistrer la configuration</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={
      <div className="flex h-[60vh] flex-col items-center justify-center space-y-4">
        <RefreshCw className="h-10 w-10 text-indigo-500 animate-spin" />
        <p className="text-slate-400">Chargement de la configuration...</p>
      </div>
    }>
      <SettingsContent />
    </Suspense>
  );
}

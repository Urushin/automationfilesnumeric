const getApiBase = () => {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
};

export const API_BASE = getApiBase();

export function apiUrl(path: string) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export function assetUrl(path: string | null | undefined) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return apiUrl(path);
}


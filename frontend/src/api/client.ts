import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Attach auth token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vf_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const register = (email: string, password: string) =>
  api.post("/auth/register", { email, password });

export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password });

export const getMe = () => api.get("/auth/me");

export const createApiKey = (name?: string) =>
  api.post("/auth/api-keys", { name });

export const listApiKeys = () => api.get("/auth/api-keys");

export const revokeApiKey = (id: string) =>
  api.delete(`/auth/api-keys/${id}`);

// Conversions
export const uploadFile = (file: File, settings: Record<string, string>) => {
  const form = new FormData();
  form.append("file", file);
  Object.entries(settings).forEach(([k, v]) => form.append(k, v));
  return api.post("/conversions", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const uploadBatch = (files: File[], settings: Record<string, string>) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  Object.entries(settings).forEach(([k, v]) => form.append(k, v));
  return api.post("/conversions/batch", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getConversion = (id: string) =>
  api.get(`/conversions/${id}`);

export const listConversions = (page = 1, perPage = 20) =>
  api.get(`/conversions?page=${page}&per_page=${perPage}`);

export const downloadConversion = (id: string, format = "svg") =>
  `/api/conversions/${id}/download?format=${format}`;

// Sharing
export const shareConversion = (id: string) =>
  api.post(`/conversions/${id}/share`);

export const getShared = (token: string) =>
  api.get(`/s/${token}`);

export const downloadShared = (token: string, format = "svg") =>
  `/api/s/${token}/download?format=${format}`;

// Webhooks
export const createWebhook = (url: string, events?: string[]) =>
  api.post("/webhooks", { url, events });

export const listWebhooks = () => api.get("/webhooks");

export const deleteWebhook = (id: string) =>
  api.delete(`/webhooks/${id}`);

// Usage
export const getUsage = () => api.get("/usage");

export const getUsageHistory = (months = 6) =>
  api.get(`/usage/history?months=${months}`);

export default api;

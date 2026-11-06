import mockService from "./mockService";
import tokenService from "./token.service";

const USE_MOCK = true;
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      Authorization: `Bearer ${tokenService.getLocalAccessToken()}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "La petición no se pudo completar");
  }

  return response.json();
}

async function requestBlob(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${tokenService.getLocalAccessToken()}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "La descarga no se pudo completar");
  }

  return response.blob();
}

const backendService = {
  register: (username, email, password) => request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  }),
  async login(username, password) {
    const result = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    tokenService.saveAccessToken(result.access_token);
    const user = await request("/auth/me");
    tokenService.saveUser(user);
    return { ...result, user };
  },
  logout: () => request("/auth/logout", { method: "POST" }),
  getFiles: () => request("/files"),
  upload: (file) => {
    const body = new FormData();
    body.append("file", file);
    return request("/files/upload", { method: "POST", body });
  },
  uploadVersion: (fileId, file) => {
    const body = new FormData();
    body.append("file", file);
    return request(`/files/${fileId}/versions`, { method: "POST", body });
  },
  download: (fileId, version) => {
    const path = version
      ? `/files/${fileId}/versions/${version}/download`
      : `/files/${fileId}/download`;
    return requestBlob(path);
  },
  delete: () => {
    throw new Error("Not available"); // TODO: El endpoint de borrado todavía no está definido en el backend.
  },
  getLogs: () => request("/logs"),
};

const api = USE_MOCK ? mockService : backendService;

export default api;

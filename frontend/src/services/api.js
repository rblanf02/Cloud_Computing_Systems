import tokenService from "./token.service";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function readError(response) {
  try {
    const data = await response.json();
    return data.detail || "La petición no se pudo completar";
  } catch {
    return "La petición no se pudo completar";
  }
}

function handleUnauthorized() {
  tokenService.removeSession();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

async function request(path, options = {}) {
  const { auth = true, ...fetchOptions } = options;
  const headers = {
    ...(fetchOptions.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...fetchOptions.headers,
  };

  if (auth) {
    const token = tokenService.getLocalAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers });
  } catch {
    throw new Error("No se pudo conectar con el servidor.");
  }

  if (response.status === 401 && auth) {
    handleUnauthorized();
  }

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

async function requestBlob(path) {
  const token = tokenService.getLocalAccessToken();

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new Error("No se pudo conectar con el servidor.");
  }

  if (response.status === 401) {
    handleUnauthorized();
  }

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return response.blob();
}

function uploadWith(path, file) {
  const body = new FormData();
  body.append("file", file);
  return request(path, { method: "POST", body });
}

const api = {
  register: (username, email, password) =>
    request("/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ username, email, password }),
    }),
  async login(username, password) {
    const result = await request("/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ username, password }),
    });
    tokenService.saveAccessToken(result.access_token);
    const user = await request("/auth/me");
    tokenService.saveUser(user);
    return { ...result, user };
  },
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  getFiles: () => request("/files"),
  upload: (file) => uploadWith("/files/upload", file),
  uploadVersion: (fileId, file) => uploadWith(`/files/${fileId}/versions`, file),
  download: (fileId, version) => {
    const path = version
      ? `/files/${fileId}/versions/${version}/download`
      : `/files/${fileId}/download`;
    return requestBlob(path);
  },
  delete: (fileId) => request(`/files/${fileId}`, { method: "DELETE" }),
  getVersions: (fileId) => request(`/files/${fileId}/versions`),
  restoreVersion: (fileId, version) =>
    request(`/files/${fileId}/versions/${version}/restore`, { method: "POST" }),
  getSharedFiles: () => request("/files/shared"),
  getTrash: () => request("/files/trash"),
  restoreFile: (fileId) => request(`/files/${fileId}/restore`, { method: "POST" }),
  permanentDelete: (fileId) =>
    request(`/files/${fileId}/permanent`, { method: "DELETE" }),
  shareFile: (fileId, username, accessLevel) =>
    request(`/files/${fileId}/share`, {
      method: "POST",
      body: JSON.stringify({
        granted_to_username: username,
        access_level: accessLevel,
      }),
    }),
  getShares: (fileId) => request(`/files/${fileId}/shares`),
  revokeShare: (fileId, userId) =>
    request(`/files/${fileId}/share/${userId}`, { method: "DELETE" }),
  getLogs: () => request("/logs"),
  exportLogs: (format) => requestBlob(`/logs/export?fmt=${format}`),
  getUsers: () => request("/admin/users"),
  updatePermissions: (userId, permissions) =>
    request(`/admin/users/${userId}/permissions`, {
      method: "PATCH",
      body: JSON.stringify(permissions),
    }),
  getAllFiles: () => request("/admin/files"),
};

export default api;

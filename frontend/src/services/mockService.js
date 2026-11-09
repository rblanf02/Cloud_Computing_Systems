let files = [
  { //mock data
    id: 1,
    filename: "informe-cloud.pdf",
    content_type: "application/pdf",
    current_version: 2,
    size_bytes: 2480000,
    version_created_at: "2026-10-28T11:30:00Z",
    versions: [
      { version_number: 2, size_bytes: 2480000, created_at: "2026-10-28T11:30:00Z" },
      { version_number: 1, size_bytes: 2310000, created_at: "2026-10-20T09:10:00Z" },
    ],
  },
  {
    id: 2,
    filename: "diagrama-arquitectura.png",
    content_type: "image/png",
    current_version: 1,
    size_bytes: 845000,
    version_created_at: "2026-10-25T16:05:00Z",
    versions: [
      { version_number: 1, size_bytes: 845000, created_at: "2026-10-25T16:05:00Z" },
    ],
  },
];
 //SIMULADOR DEL BACKEND, NO HACE LLAMADAS REALES A NINGÚN SERVIDOR. SOLO SIMULA EL COMPORTAMIENTO DE UN BACKEND PARA PRUEBAS LOCALES.
let logs = [];
const registeredUsers = [];

function addLog(action, resource) {
  logs = [{ timestamp: new Date().toISOString(), action, resource, result: "OK" }, ...logs];
}

const mockService = {
  async register(username, email, password) {
    if (registeredUsers.some((user) => user.username === username)) {
      throw new Error("El usuario ya existe.");
    }
    registeredUsers.push({ username, email, password });
    return { username, email };
  },
  async login(username) {
    const user = { username, can_read: true, can_write: true, can_update: true };
    files = files.map((file) => ({ ...file, fileObject: undefined }));
    logs = [];
    addLog("LOGIN", `user:${username}`);
    return { access_token: "mock-token", user };
  },
  async logout(username) {
    addLog("LOGOUT", `user:${username}`);
  },
  async getFiles() {
    return files;
  },
  async upload(file) {
    const now = new Date().toISOString();
    const newFile = {
      id: Date.now(),
      filename: file.name,
      content_type: file.type || "application/octet-stream",
      current_version: 1,
      size_bytes: file.size,
      version_created_at: now,
      fileObject: file,
      versions: [{ version_number: 1, size_bytes: file.size, created_at: now, fileObject: file }],
    };
    files = [newFile, ...files];
    addLog("UPLOAD_NEW", `file:${newFile.id}/v1`);
    return newFile;
  },
  async uploadVersion(fileId, file) {
    const now = new Date().toISOString();
    const currentFile = files.find((item) => item.id === fileId);
    const version = currentFile.current_version + 1;
    const newVersion = { version_number: version, size_bytes: file.size, created_at: now, fileObject: file };
    const updatedFile = {
      ...currentFile,
      current_version: version,
      size_bytes: file.size,
      version_created_at: now,
      fileObject: file,
      versions: [newVersion, ...currentFile.versions],
    };
    files = files.map((item) => item.id === fileId ? updatedFile : item);
    addLog("UPLOAD_VERSION", `file:${fileId}/v${version}`);
    return updatedFile;
  },
  async download(fileId, version) {
    const currentFile = files.find((file) => file.id === fileId);
    const selectedVersion = currentFile?.versions.find((item) => item.version_number === version);

    if (!selectedVersion?.fileObject) {
      throw new Error("En modo demo solo puedes descargar ficheros subidos en esta sesión.");
    }

    addLog("DOWNLOAD", `file:${fileId}/v${version}`);
    return selectedVersion.fileObject;
  },
  async delete(fileId) {
    files = files.filter((file) => file.id !== fileId);
    addLog("DELETE", `file:${fileId}`);
  },
  async getLogs() {
    return logs;
  },
};

export default mockService;

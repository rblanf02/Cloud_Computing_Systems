import { useEffect, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import { downloadFile } from "../utils/formatters";
import FileCard from "./FileCard";

function SharedFiles() {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadFiles() {
    setLoading(true);
    setError("");
    try {
      setFiles(await api.getSharedFiles());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function uploadVersion(fileId, file) {
    setMessage("");
    setError("");
    try {
      await api.uploadVersion(fileId, file);
      await loadFiles();
      setMessage("Nueva versión subida correctamente.");
    } catch (uploadError) {
      setError(uploadError.message);
    }
  }

  async function download(file, version = file.current_version) {
    setMessage("");
    setError("");
    try {
      const downloadedFile = await api.download(file.file_id, version);
      downloadFile(downloadedFile, file.filename);
      setMessage("Fichero descargado correctamente.");
    } catch (downloadError) {
      setError(downloadError.message);
    }
  }

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Colaboración</p>
            <h1>Compartidos conmigo</h1>
            <p className="muted">Ficheros que otros usuarios han compartido con tu cuenta.</p>
          </div>
        </div>
        {message && <div className="message success">{message}</div>}
        {error && <div className="message error">{error}</div>}
        {loading && <div className="empty-state">Cargando ficheros compartidos...</div>}
        {!loading && (
          <div className="file-list">
            {files.length ? files.map((file) => (
              <FileCard
                key={file.file_id}
                file={file}
                showOwner
                onUploadVersion={uploadVersion}
                onDownload={download}
                onRestored={loadFiles}
                canManage={file.access_level === "manager"}
                canUpdate={file.access_level === "editor" || file.access_level === "manager"}
              />
            )) : <div className="empty-state">No tienes ficheros compartidos.</div>}
          </div>
        )}
      </main>
    </>
  );
}

export default SharedFiles;

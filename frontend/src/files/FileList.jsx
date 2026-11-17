import { useEffect, useRef, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import FileCard from "./FileCard";
import { downloadFile } from "../utils/formatters";

function FileList() {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const inputRef = useRef(null);

  async function loadFiles() {
    setLoading(true);
    setError("");
    try {
      setFiles(await api.getFiles());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function uploadFile(file) {
    if (!file) return;
    setMessage("");
    setError("");
    try {
      await api.upload(file);
      await loadFiles();
      setMessage("Fichero subido correctamente.");
    } catch (uploadError) {
      setError(uploadError.message);
    }
  }

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

  async function deleteFile(file) {
    if (!window.confirm(`¿Mover "${file.filename}" a la papelera?`)) return;
    setMessage("");
    setError("");
    try {
      await api.delete(file.file_id);
      await loadFiles();
      setMessage("Fichero movido a la papelera.");
    } catch (deleteError) {
      setError(deleteError.message);
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

  function handleFileChange(event) {
    const file = event.target.files[0];
    uploadFile(file);
    event.target.value = "";
  }

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Área personal</p>
            <h1>Mis ficheros</h1>
            <p className="muted">Sube, descarga, comparte y consulta las versiones de tus documentos.</p>
          </div>
          <button className="button button-primary" onClick={() => inputRef.current.click()}>＋ Subir fichero</button>
          <input ref={inputRef} className="visually-hidden" type="file" onChange={handleFileChange} />
        </div>
        {message && <div className="message success">{message}</div>}
        {error && <div className="message error">{error}</div>}
        {loading && <div className="empty-state">Cargando ficheros...</div>}
        {!loading && (
          <div className="file-list">
            {files.length ? files.map((file) => (
              <FileCard
                key={file.file_id}
                file={file}
                onDelete={deleteFile}
                onUploadVersion={uploadVersion}
                onDownload={download}
                onRestored={loadFiles}
              />
            )) : <div className="empty-state">Todavía no tienes ficheros.</div>}
          </div>
        )}
      </main>
    </>
  );
}

export default FileList;

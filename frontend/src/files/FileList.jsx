import { useEffect, useRef, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import FileCard from "./FileCard";
import { downloadFile } from "../utils/formatters";

function FileList() {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  async function loadFiles() {
    try {
      setFiles(await api.getFiles());
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => { loadFiles(); }, []);

  async function uploadFile(file) {
    if (!file) return;
    try {
      await api.upload(file);
      await loadFiles();
      setMessage("Fichero subido correctamente.");
    } catch (uploadError) {
      setError(uploadError.message);
    }
  }

  async function uploadVersion(fileId, file) {
    try {
      await api.uploadVersion(fileId, file);
      await loadFiles();
      setMessage("Nueva versión subida correctamente.");
    } catch (uploadError) {
      setError(uploadError.message);
    }
  }

  async function deleteFile(file) {
    if (!window.confirm(`¿Borrar "${file.filename}"?`)) return;
    try {
      await api.delete(file.id);
      await loadFiles();
      setMessage("Fichero borrado correctamente.");
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  async function download(file, version = file.current_version) {
    try {
      const downloadedFile = await api.download(file.id, version);
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
            <p className="eyebrow">Área personal</p>
            <h1>Mis ficheros</h1>
            <p className="muted">Sube, descarga y consulta las versiones de tus documentos.</p>
          </div>
          <button className="button button-primary" onClick={() => inputRef.current.click()}>＋ Subir fichero</button>
          <input ref={inputRef} className="visually-hidden" type="file" onChange={(event) => uploadFile(event.target.files[0])} />
        </div>
        {message && <div className="message success">{message}</div>}
        {error && <div className="message error">{error}</div>}
        <div className="file-list">
          {files.length ? files.map((file) => (
            <FileCard key={file.id} file={file} onDelete={deleteFile} onUploadVersion={uploadVersion} onDownload={download} />
          )) : <div className="empty-state">Todavía no tienes ficheros.</div>}
        </div>
      </main>
    </>
  );
}

export default FileList;

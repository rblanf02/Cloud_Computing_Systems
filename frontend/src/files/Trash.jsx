import { useEffect, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import { formatBytes, formatDate } from "../utils/formatters";

function Trash() {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadFiles() {
    setLoading(true);
    setError("");
    try {
      setFiles(await api.getTrash());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function restore(file) {
    setMessage("");
    setError("");
    try {
      await api.restoreFile(file.id);
      await loadFiles();
      setMessage("Fichero restaurado correctamente.");
    } catch (restoreError) {
      setError(restoreError.message);
    }
  }

  async function permanentDelete(file) {
    if (!window.confirm(`¿Eliminar definitivamente "${file.filename}" y todo su historial?`)) return;
    setMessage("");
    setError("");
    try {
      await api.permanentDelete(file.id);
      await loadFiles();
      setMessage("Fichero eliminado definitivamente.");
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Recuperación</p>
            <h1>Papelera</h1>
            <p className="muted">Restaura ficheros o elimínalos de forma permanente.</p>
          </div>
        </div>
        {message && <div className="message success">{message}</div>}
        {error && <div className="message error">{error}</div>}
        {loading && <div className="empty-state">Cargando papelera...</div>}
        {!loading && (
          <div className="file-list">
            {files.length ? files.map((file) => (
              <article className="file-card" key={file.id}>
                <div className="file-info">
                  <div className="file-icon">▣</div>
                  <div>
                    <div className="file-name" title={file.filename}>{file.filename}</div>
                    <div className="file-meta">
                      {formatBytes(file.size_bytes)} · versión {file.current_version} · {formatDate(file.version_created_at)}
                    </div>
                  </div>
                </div>
                <div className="file-actions">
                  <button className="button button-secondary" onClick={() => restore(file)}>Restaurar</button>
                  <button className="button button-danger" onClick={() => permanentDelete(file)}>Borrar definitivo</button>
                </div>
              </article>
            )) : <div className="empty-state">La papelera está vacía.</div>}
          </div>
        )}
      </main>
    </>
  );
}

export default Trash;

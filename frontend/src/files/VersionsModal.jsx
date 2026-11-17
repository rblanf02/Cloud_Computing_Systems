import { useEffect, useState } from "react";
import api from "../services/api";
import { formatBytes, formatDate } from "../utils/formatters";

function VersionsModal({ file, onClose, onDownload, onRestored, canUpdate }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyVersion, setBusyVersion] = useState(null);

  async function loadVersions() {
    setLoading(true);
    setError("");
    try {
      setVersions(await api.getVersions(file.file_id));
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadVersions();
  }, [file.file_id]);

  async function restore(versionNumber) {
    if (!window.confirm(`¿Restaurar la versión ${versionNumber} como una versión nueva?`)) return;
    setBusyVersion(versionNumber);
    setError("");
    try {
      await api.restoreVersion(file.file_id, versionNumber);
      await loadVersions();
      onRestored?.();
    } catch (restoreError) {
      setError(restoreError.message);
    } finally {
      setBusyVersion(null);
    }
  }

  return (
    <div className="modal" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h2>Versiones de {file.filename}</h2>
          <button className="icon-button" onClick={onClose}>×</button>
        </div>
        {error && <div className="message error">{error}</div>}
        {loading && <p className="muted">Cargando versiones...</p>}
        {!loading && !versions.length && <p className="muted">No hay versiones registradas.</p>}
        {versions.map((version) => (
          <div className="version-row" key={version.version_number}>
            <div>
              <strong>Versión {version.version_number}</strong>
              <div className="file-meta">
                {formatBytes(version.size_bytes)} · {formatDate(version.uploaded_at)} · {version.uploaded_by_username}
              </div>
              <div className="file-meta hash-value" title={version.sha256 || "Sin hash"}>
                SHA-256: {version.sha256 ? `${version.sha256.slice(0, 20)}...` : "no disponible"}
              </div>
            </div>
            <div className="file-actions">
              <button className="button button-secondary" onClick={() => onDownload(file, version.version_number)}>
                Descargar
              </button>
              {canUpdate && (
                <button
                  className="button button-secondary"
                  disabled={busyVersion === version.version_number}
                  onClick={() => restore(version.version_number)}
                >
                  {busyVersion === version.version_number ? "Restaurando..." : "Restaurar"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default VersionsModal;

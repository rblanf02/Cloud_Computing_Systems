import { useEffect, useState } from "react";
import api from "../services/api";
import { formatDate } from "../utils/formatters";

function ShareModal({ file, onClose }) {
  const [shares, setShares] = useState([]);
  const [username, setUsername] = useState("");
  const [accessLevel, setAccessLevel] = useState("reader");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadShares() {
    setLoading(true);
    setError("");
    try {
      setShares(await api.getShares(file.id));
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadShares();
  }, [file.id]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);
    try {
      await api.shareFile(file.id, username.trim(), accessLevel);
      setUsername("");
      setMessage("Permiso concedido correctamente.");
      await loadShares();
    } catch (shareError) {
      setError(shareError.message);
    } finally {
      setSaving(false);
    }
  }

  async function revoke(share) {
    if (!window.confirm(`¿Quitar el acceso a ${share.granted_to_username}?`)) return;
    setError("");
    setMessage("");
    try {
      await api.revokeShare(file.id, share.granted_to);
      setMessage("Permiso revocado.");
      await loadShares();
    } catch (revokeError) {
      setError(revokeError.message);
    }
  }

  return (
    <div className="modal" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h2>Compartir {file.filename}</h2>
          <button className="icon-button" onClick={onClose}>×</button>
        </div>

        {error && <div className="message error">{error}</div>}
        {message && <div className="message success">{message}</div>}

        <form className="share-form" onSubmit={handleSubmit}>
          <label htmlFor="share-username">Usuario</label>
          <input
            id="share-username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="nombre de usuario"
            required
          />
          <label htmlFor="share-level">Nivel de acceso</label>
          <select
            id="share-level"
            value={accessLevel}
            onChange={(event) => setAccessLevel(event.target.value)}
          >
            <option value="reader">Lectura</option>
            <option value="editor">Editor</option>
            <option value="manager">Gestor</option>
          </select>
          <button className="button button-primary" disabled={saving}>
            {saving ? "Compartiendo..." : "Compartir"}
          </button>
        </form>

        <h3 className="section-title">Permisos actuales</h3>
        {loading && <p className="muted">Cargando permisos...</p>}
        {!loading && !shares.length && <p className="muted">Este fichero no está compartido.</p>}
        {shares.map((share) => (
          <div className="version-row" key={`${share.file_id}-${share.granted_to}`}>
            <div>
              <strong>{share.granted_to_username}</strong>
              <div className="file-meta">
                {share.access_level} · desde {formatDate(share.created_at)} · por {share.granted_by_username}
              </div>
            </div>
            <button className="button button-danger" onClick={() => revoke(share)}>
              Revocar
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ShareModal;

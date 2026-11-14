import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import { downloadFile, formatBytes, formatDate } from "../utils/formatters";

function AdminFiles() {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadFiles() {
    setLoading(true);
    setError("");
    try {
      setFiles(await api.getAllFiles());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function download(file) {
    setMessage("");
    setError("");
    try {
      const downloadedFile = await api.download(file.id);
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
            <p className="eyebrow">Administración</p>
            <h1>Todos los ficheros</h1>
            <p className="muted">Vista global de los ficheros almacenados por todos los usuarios.</p>
          </div>
          <Link className="button button-secondary" to="/admin/users">Volver a usuarios</Link>
        </div>
        {message && <div className="message success">{message}</div>}
        {error && <div className="message error">{error}</div>}
        {loading && <div className="empty-state">Cargando ficheros...</div>}
        {!loading && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fichero</th>
                  <th>Propietario</th>
                  <th>Versión</th>
                  <th>Tamaño</th>
                  <th>Actualizado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {files.length ? files.map((file) => (
                  <tr key={file.id}>
                    <td>{file.filename}</td>
                    <td>{file.owner_username}</td>
                    <td>{file.current_version}</td>
                    <td>{formatBytes(file.size_bytes)}</td>
                    <td>{formatDate(file.version_created_at)}</td>
                    <td>
                      <button className="button button-secondary" onClick={() => download(file)}>
                        Descargar
                      </button>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan="6">No hay ficheros registrados.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}

export default AdminFiles;

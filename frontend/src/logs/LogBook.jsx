import { useEffect, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import tokenService from "../services/token.service";
import { downloadFile, formatDate } from "../utils/formatters";

function LogBook() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const user = tokenService.getUser();

  async function loadLogs() {
    setLoading(true);
    setError("");
    try {
      setLogs(await api.getLogs());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  async function exportLogs(format) {
    setError("");
    try {
      const blob = await api.exportLogs(format);
      downloadFile(blob, `logbook.${format}`);
    } catch (exportError) {
      setError(exportError.message);
    }
  }

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Auditoría</p>
            <h1>LogBook</h1>
            <p className="muted">
              {user?.is_admin
                ? "Todos los eventos registrados en el sistema."
                : "Últimas acciones registradas en tu cuenta."}
            </p>
          </div>
          <div className="export-buttons">
            <button className="button button-secondary" onClick={() => exportLogs("json")}>Exportar JSON</button>
            <button className="button button-secondary" onClick={() => exportLogs("csv")}>Exportar CSV</button>
          </div>
        </div>
        {error && <div className="message error">{error}</div>}
        {loading && <div className="empty-state">Cargando eventos...</div>}
        {!loading && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Usuario</th>
                  <th>Acción</th>
                  <th>Recurso</th>
                  <th>Resultado</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {logs.length ? logs.map((log, index) => (
                  <tr key={`${log.timestamp}-${index}`}>
                    <td>{formatDate(log.timestamp)}</td>
                    <td>{log.username || "—"}</td>
                    <td>{log.action}</td>
                    <td>{log.resource || "—"}</td>
                    <td>{log.result}</td>
                    <td>{log.details || "—"}</td>
                  </tr>
                )) : <tr><td colSpan="6">No hay acciones registradas.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}

export default LogBook;

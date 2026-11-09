import { useEffect, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import { formatDate } from "../utils/formatters";

function LogBook() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    api.getLogs().then(setLogs).catch((error) => console.error(error));
  }, []);

  function exportLogs(format) {
    const content = format === "json"
      ? JSON.stringify(logs, null, 2)
      : ["timestamp,action,resource,result", ...logs.map((log) => Object.values(log).join(","))].join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
    link.download = `logbook.${format}`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Auditoría</p>
            <h1>LogBook</h1>
            <p className="muted">Consulta las últimas acciones realizadas en tu cuenta.</p>
          </div>
          <div className="export-buttons">
            <button className="button button-secondary" onClick={() => exportLogs("json")}>Exportar JSON</button>
            <button className="button button-secondary" onClick={() => exportLogs("csv")}>Exportar CSV</button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Acción</th><th>Recurso</th><th>Resultado</th></tr></thead>
            <tbody>
              {logs.length ? logs.map((log, index) => (
                <tr key={`${log.timestamp}-${index}`}><td>{formatDate(log.timestamp)}</td><td>{log.action}</td><td>{log.resource}</td><td>{log.result}</td></tr>
              )) : <tr><td colSpan="4">No hay acciones registradas.</td></tr>}
            </tbody>
          </table>
        </div>
      </main>
    </>
  );
}

export default LogBook;

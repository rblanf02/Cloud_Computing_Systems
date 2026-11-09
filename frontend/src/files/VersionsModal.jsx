import { formatBytes, formatDate } from "../utils/formatters";

function VersionsModal({ file, onClose, onDownload }) {
  return (
    <div className="modal" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h2>Versiones de {file.filename}</h2>
          <button className="icon-button" onClick={onClose}>×</button>
        </div>
        {file.versions.map((version) => (
          <div className="version-row" key={version.version_number}>
            <div>
              <strong>Versión {version.version_number}</strong>
              <div className="file-meta">{formatBytes(version.size_bytes)} · {formatDate(version.created_at)}</div>
            </div>
            <button className="button button-secondary" onClick={() => onDownload(file, version.version_number)}>
              Descargar
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default VersionsModal;

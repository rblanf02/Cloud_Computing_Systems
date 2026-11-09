import { useState } from "react";
import { formatBytes, formatDate } from "../utils/formatters";
import VersionsModal from "./VersionsModal";

function FileCard({ file, onDelete, onUploadVersion, onDownload }) {
  const [showVersions, setShowVersions] = useState(false);

  function chooseVersion() {
    const input = document.createElement("input");
    input.type = "file";
    input.onchange = () => input.files[0] && onUploadVersion(file.id, input.files[0]);
    input.click();
  }

  return (
    <>
      <article className="file-card">
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
          <button className="button button-secondary" onClick={() => onDownload(file)}>Descargar</button>
          <button className="button button-secondary" onClick={() => setShowVersions(true)}>Versiones</button>
          <button className="button button-secondary" onClick={chooseVersion}>Nueva versión</button>
          <button className="button button-danger" onClick={() => onDelete(file)}>Borrar</button>
        </div>
      </article>
      {showVersions && <VersionsModal file={file} onClose={() => setShowVersions(false)} onDownload={onDownload} />}
    </>
  );
}

export default FileCard;

import { useState } from "react";
import { formatBytes, formatDate } from "../utils/formatters";
import ShareModal from "./ShareModal";
import VersionsModal from "./VersionsModal";

function FileCard({
  file,
  onDelete,
  onUploadVersion,
  onDownload,
  onRestored,
  showOwner = false,
  canManage = true,
  canUpdate = true,
}) {
  const [showVersions, setShowVersions] = useState(false);
  const [showShare, setShowShare] = useState(false);

  function chooseVersion() {
    const input = document.createElement("input");
    input.type = "file";
    input.onchange = () => input.files[0] && onUploadVersion(file.file_id, input.files[0]);
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
              {formatBytes(file.size_bytes)} · versión {file.current_version} · {formatDate(file.uploaded_at)}
            </div>
            {showOwner && (
              <div className="file-meta">
                Propietario: {file.owner_username}
                {file.access_level ? ` · acceso ${file.access_level}` : ""}
              </div>
            )}
          </div>
        </div>
        <div className="file-actions">
          <button className="button button-secondary" onClick={() => onDownload(file)}>Descargar</button>
          <button className="button button-secondary" onClick={() => setShowVersions(true)}>Versiones</button>
          {canUpdate && (
            <button className="button button-secondary" onClick={chooseVersion}>Nueva versión</button>
          )}
          {canManage && (
            <button className="button button-secondary" onClick={() => setShowShare(true)}>Compartir</button>
          )}
          {canManage && onDelete && (
            <button className="button button-danger" onClick={() => onDelete(file)}>Borrar</button>
          )}
        </div>
      </article>
      {showVersions && (
        <VersionsModal
          file={file}
          onClose={() => setShowVersions(false)}
          onDownload={onDownload}
          onRestored={onRestored}
          canUpdate={canUpdate}
        />
      )}
      {showShare && <ShareModal file={file} onClose={() => setShowShare(false)} />}
    </>
  );
}

export default FileCard;

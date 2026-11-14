import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import { formatDate } from "../utils/formatters";

const PERMISSIONS = [
  { key: "can_read", label: "Leer" },
  { key: "can_write", label: "Escribir" },
  { key: "can_update", label: "Actualizar" },
];

function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  async function loadUsers() {
    setLoading(true);
    setError("");
    try {
      setUsers(await api.getUsers());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function togglePermission(user, key) {
    setMessage("");
    setError("");
    setSavingId(user.id);
    try {
      const updated = await api.updatePermissions(user.id, { [key]: !user[key] });
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setMessage(`Permisos de ${updated.username} actualizados.`);
    } catch (updateError) {
      setError(updateError.message);
    } finally {
      setSavingId(null);
    }
  }

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Administración</p>
            <h1>Usuarios y permisos</h1>
            <p className="muted">Concede o revoca los permisos de lectura, escritura y actualización.</p>
          </div>
          <Link className="button button-secondary" to="/admin/files">Ver todos los ficheros</Link>
        </div>
        {message && <div className="message success">{message}</div>}
        {error && <div className="message error">{error}</div>}
        {loading && <div className="empty-state">Cargando usuarios...</div>}
        {!loading && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Email</th>
                  <th>Rol</th>
                  <th>Alta</th>
                  {PERMISSIONS.map((permission) => (
                    <th key={permission.key}>{permission.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{user.is_admin ? "Administrador" : "Usuario"}</td>
                    <td>{formatDate(user.created_at)}</td>
                    {PERMISSIONS.map((permission) => (
                      <td key={permission.key}>
                        <input
                          type="checkbox"
                          className="permission-checkbox"
                          checked={user[permission.key]}
                          disabled={user.is_admin || savingId === user.id}
                          onChange={() => togglePermission(user, permission.key)}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}

export default AdminUsers;

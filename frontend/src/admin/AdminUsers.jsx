import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import api from "../services/api";
import { formatBytes, formatDate } from "../utils/formatters";

function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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

  return (
    <>
      <AppNavbar />
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Administración</p>
            <h1>Usuarios</h1>
            <p className="muted">Listado global de usuarios registrados en el sistema.</p>
          </div>
          <Link className="button button-secondary" to="/admin/files">Ver todos los ficheros</Link>
        </div>
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
                  <th>Cuota</th>
                </tr>
              </thead>
              <tbody>
                {users.length ? users.map((user) => (
                  <tr key={user.user_id}>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{user.is_admin ? "Administrador" : "Usuario"}</td>
                    <td>{formatDate(user.created_at)}</td>
                    <td>{formatBytes(user.quota_bytes)}</td>
                  </tr>
                )) : (
                  <tr><td colSpan="5">No hay usuarios registrados.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}

export default AdminUsers;

import { NavLink, useNavigate } from "react-router-dom";
import api from "../services/api";
import tokenService from "../services/token.service";

function AppNavbar() {
  const navigate = useNavigate();
  const user = tokenService.getUser();

  async function handleLogout() {
    if (!window.confirm("¿Seguro que quieres cerrar sesión?")) return;

    try {
      await api.logout(user?.username);
    } finally {
      tokenService.removeSession();
      navigate("/login");
    }
  }

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">☁</span>
        <span>CloudFile <strong>Exchange</strong></span>
      </div>
      <nav className="main-nav">
        <NavLink to="/files">Mis ficheros</NavLink>
        <NavLink to="/logs">LogBook</NavLink>
      </nav>
      <div className="user-menu">
        <span>{user?.username}</span>
        <button className="button button-secondary" onClick={handleLogout}>Cerrar sesión</button>
      </div>
    </header>
  );
}

export default AppNavbar;

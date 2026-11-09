import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import api from "../services/api";
import tokenService from "../services/token.service";

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (tokenService.getLocalAccessToken()) {
    return <Navigate to="/files" replace />; //replace evita que el usuario pueda volver a la página de login usando el botón de atrás del navegador
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true); //inicia que el login está en proceso

    try {
      const result = await api.login(username, password); //TODO: el login actual es mockeado, cuando se implemente el backend, este método 
      tokenService.saveAccessToken(result.access_token); //deberá hacer la llamada real al endpoint de login
      tokenService.saveUser(result.user); //guarda la sesion y los datos del user
      navigate("/files");
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand brand-large">
          <span className="brand-mark">☁</span>
          <span>CloudFile <strong>Exchange</strong></span>
        </div>
        <p className="muted">Tus documentos, disponibles desde cualquier dispositivo.</p>
        {error && <div className="message error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <label htmlFor="username">Usuario</label>
          <input id="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          <button className="button button-primary button-full" disabled={loading}>
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p className="auth-link">
          ¿No tienes una cuenta? <Link to="/register">Registrarse</Link>
        </p>
        <p className="demo-hint">Modo demo: puedes usar cualquier usuario y contraseña.</p>
      </section>
    </main>
  );
}

export default Login;

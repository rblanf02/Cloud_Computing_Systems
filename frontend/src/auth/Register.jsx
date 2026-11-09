import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";

function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (password !== passwordConfirmation) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setLoading(true);
    try {
      await api.register(username, email, password);
      setSuccess("Cuenta creada correctamente. Ya puedes iniciar sesión.");
      setTimeout(() => navigate("/login"), 1200);
    } catch (registerError) {
      setError(registerError.message);
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
        <p className="muted">Crea tu cuenta para empezar a guardar ficheros.</p>
        {error && <div className="message error">{error}</div>}
        {success && <div className="message success">{success}</div>}
        <form onSubmit={handleSubmit}>
          <label htmlFor="register-username">Usuario</label>
          <input id="register-username" value={username} onChange={(event) => setUsername(event.target.value)} minLength="3" maxLength="50" required />
          <label htmlFor="register-email">Email</label>
          <input id="register-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <label htmlFor="register-password">Contraseña</label>
          <input id="register-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength="6" required />
          <label htmlFor="register-password-confirmation">Repetir contraseña</label>
          <input id="register-password-confirmation" type="password" value={passwordConfirmation} onChange={(event) => setPasswordConfirmation(event.target.value)} minLength="6" required />
          <button className="button button-primary button-full" disabled={loading}>
            {loading ? "Creando cuenta..." : "Registrarse"}
          </button>
        </form>
        <p className="auth-link">
          ¿Ya tienes una cuenta? <Link to="/login">Iniciar sesión</Link>
        </p>
        <p className="demo-hint">En el backend real se validarán usuario, email y contraseña.</p>
      </section>
    </main>
  );
}

export default Register;

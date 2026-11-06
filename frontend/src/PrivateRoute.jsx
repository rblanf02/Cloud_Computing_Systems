import { Navigate } from "react-router-dom";
import tokenService from "./services/token.service";

function PrivateRoute({ children }) {
  if (!tokenService.getLocalAccessToken()) { //si el usuario no tiene un token de acceso, lo redirige a la página de login (protege las rutas privadas)
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default PrivateRoute;

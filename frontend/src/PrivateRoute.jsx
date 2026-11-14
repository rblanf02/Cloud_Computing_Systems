import { Navigate } from "react-router-dom";
import tokenService from "./services/token.service";

function PrivateRoute({ children, adminOnly = false }) {
  if (!tokenService.getLocalAccessToken()) {
    return <Navigate to="/login" replace />;
  }

  const user = tokenService.getUser();
  if (adminOnly && !user?.is_admin) {
    return <Navigate to="/files" replace />;
  }

  return children;
}

export default PrivateRoute;

import { Navigate, Route, Routes } from "react-router-dom";
import AdminFiles from "./admin/AdminFiles";
import AdminUsers from "./admin/AdminUsers";
import Login from "./auth/Login";
import Register from "./auth/Register";
import PrivateRoute from "./PrivateRoute";
import FileList from "./files/FileList";
import SharedFiles from "./files/SharedFiles";
import Trash from "./files/Trash";
import LogBook from "./logs/LogBook";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<PrivateRoute><FileList /></PrivateRoute>} />
      <Route path="/files" element={<PrivateRoute><FileList /></PrivateRoute>} />
      <Route path="/shared" element={<PrivateRoute><SharedFiles /></PrivateRoute>} />
      <Route path="/trash" element={<PrivateRoute><Trash /></PrivateRoute>} />
      <Route path="/logs" element={<PrivateRoute><LogBook /></PrivateRoute>} />
      <Route path="/admin" element={<Navigate to="/admin/users" replace />} />
      <Route path="/admin/users" element={<PrivateRoute adminOnly><AdminUsers /></PrivateRoute>} />
      <Route path="/admin/files" element={<PrivateRoute adminOnly><AdminFiles /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/files" replace />} />
    </Routes>
  );
}

export default App;

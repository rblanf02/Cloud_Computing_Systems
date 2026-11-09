import { Route, Routes } from "react-router-dom";
import Login from "./auth/Login";
import Register from "./auth/Register";
import PrivateRoute from "./PrivateRoute";
import FileList from "./files/FileList";
import LogBook from "./logs/LogBook";

function Home() {
  return <FileList />;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<PrivateRoute><Home /></PrivateRoute>} />
      <Route path="/files" element={<PrivateRoute><FileList /></PrivateRoute>} />
      <Route path="/logs" element={<PrivateRoute><LogBook /></PrivateRoute>} />
    </Routes>
  );
}

export default App;

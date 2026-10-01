import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";

import ChatPage from "./pages/ChatPage";
import ComplaintsPage from "./pages/ComplaintsPage";
import DashboardPage from "./pages/DashboardPage";
import EvidencePage from "./pages/EvidencePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

import CasesPage from "./pages/CasesPage";

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={<LoginPage />}
      />

      <Route
        path="/register"
        element={<RegisterPage />}
      />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route
            index
            element={<DashboardPage />}
          />

          <Route
            path="cases"
            element={<CasesPage />}
          />

          <Route
            path="chat"
            element={<ChatPage />}
          />

          {/* Complaints workspace */}
          <Route
            path="complaints"
            element={<ComplaintsPage />}
          />
          <Route
            path="complaints/:complaintId"
            element={<ComplaintsPage />}
          />

          {/* Evidence Vault */}
          <Route
            path="evidence"
            element={<EvidencePage />}
          />
          <Route
            path="evidence/:evidenceId"
            element={<EvidencePage />}
          />
        </Route>
      </Route>

      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  );
}
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import Navbar from './components/Navbar.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';
import Dashboard from './pages/Dashboard.jsx';
import History from './pages/History.jsx';
import Login from './pages/Login.jsx';
import NotFound from './pages/NotFound.jsx';
import Register from './pages/Register.jsx';
import Summarize from './pages/Summarize.jsx';
import SummaryDetails from './pages/SummaryDetails.jsx';

/** Chrome shared by every authenticated page. */
function AppLayout() {
  return (
    <div className="app-shell">
      <Navbar />
      <Outlet />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/summarize" element={<Summarize />} />
        <Route path="/history" element={<History />} />
        <Route path="/summaries/:summaryId" element={<SummaryDetails />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

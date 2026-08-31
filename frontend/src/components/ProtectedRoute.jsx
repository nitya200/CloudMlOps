import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext.jsx';
import LoadingSpinner from './LoadingSpinner.jsx';

/**
 * Guards a route. Set requireAdmin to restrict it to administrators.
 * This is a convenience for the UI only - the API enforces the same rules.
 */
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { isAuthenticated, isAdmin, initializing } = useAuth();
  const location = useLocation();

  if (initializing) {
    return <LoadingSpinner label="Restoring your session" />;
  }

  if (!isAuthenticated) {
    // Remember where the user was headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

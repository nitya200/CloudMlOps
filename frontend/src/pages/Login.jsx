import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage.jsx';
import { Spinner } from '../components/LoadingSpinner.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import AuthLayout from './AuthLayout.jsx';

export default function Login() {
  const { login, isAuthenticated, initializing } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!initializing && isAuthenticated) {
    return <Navigate to={location.state?.from || '/dashboard'} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    const result = await login(email.trim(), password);
    setSubmitting(false);
    if (result.ok) {
      navigate(location.state?.from || '/dashboard', { replace: true });
    } else {
      setError(result.error);
    }
  };

  return (
    <AuthLayout>
      <form className="auth__form" onSubmit={handleSubmit} noValidate>
        <div>
          <span className="eyebrow">Welcome back</span>
          <h2 style={{ marginTop: 6 }}>Sign in to your workspace</h2>
        </div>

        <ErrorMessage message={error} onDismiss={() => setError('')} />

        <div className="field">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            className="input"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@university.edu"
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          className="btn btn--primary btn--lg btn--block"
          disabled={submitting || !email || !password}
        >
          {submitting ? <Spinner /> : null}
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="auth__footer">
          No account yet? <Link to="/register">Create one</Link>
        </p>
      </form>
    </AuthLayout>
  );
}

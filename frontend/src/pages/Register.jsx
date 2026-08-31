import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage.jsx';
import { Spinner } from '../components/LoadingSpinner.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import AuthLayout from './AuthLayout.jsx';

/** Mirrors the backend's password policy so the user is not surprised by a 422. */
function validate({ name, email, password, confirm }) {
  if (name.trim().length < 2) return 'Please enter your full name.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email address.';
  if (password.length < 8) return 'Password must be at least 8 characters long.';
  if (!/[a-zA-Z]/.test(password)) return 'Password must contain at least one letter.';
  if (!/\d/.test(password)) return 'Password must contain at least one digit.';
  if (password !== confirm) return 'The two passwords do not match.';
  return '';
}

export default function Register() {
  const { register, isAuthenticated, initializing } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!initializing && isAuthenticated) return <Navigate to="/dashboard" replace />;

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    const problem = validate(form);
    if (problem) {
      setError(problem);
      return;
    }
    setError('');
    setSubmitting(true);
    const result = await register(form.name.trim(), form.email.trim(), form.password);
    setSubmitting(false);
    if (result.ok) navigate('/dashboard', { replace: true });
    else setError(result.error);
  };

  return (
    <AuthLayout>
      <form className="auth__form" onSubmit={handleSubmit} noValidate>
        <div>
          <span className="eyebrow">Get started</span>
          <h2 style={{ marginTop: 6 }}>Create your account</h2>
        </div>

        <ErrorMessage message={error} onDismiss={() => setError('')} />

        <div className="field">
          <label htmlFor="name">Full name</label>
          <input
            id="name"
            className="input"
            autoComplete="name"
            required
            value={form.name}
            onChange={update('name')}
            placeholder="Aakash Malipeddi"
          />
        </div>

        <div className="field">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            className="input"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={update('email')}
            placeholder="you@university.edu"
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="new-password"
            required
            value={form.password}
            onChange={update('password')}
            placeholder="At least 8 characters"
          />
          <p className="field__hint">Must be 8+ characters and include a letter and a digit.</p>
        </div>

        <div className="field">
          <label htmlFor="confirm">Confirm password</label>
          <input
            id="confirm"
            className="input"
            type="password"
            autoComplete="new-password"
            required
            value={form.confirm}
            onChange={update('confirm')}
          />
        </div>

        <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={submitting}>
          {submitting ? <Spinner /> : null}
          {submitting ? 'Creating account…' : 'Create account'}
        </button>

        <p className="auth__footer">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </AuthLayout>
  );
}

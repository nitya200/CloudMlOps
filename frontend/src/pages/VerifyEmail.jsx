import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage.jsx';
import { Spinner } from '../components/LoadingSpinner.jsx';
import api from '../services/api.js';
import AuthLayout from './AuthLayout.jsx';

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setError('Missing verification token.');
      return;
    }
    api
      .get('/api/auth/verify-email', { params: { token } })
      .then(() => setStatus('ok'))
      .catch((err) => {
        setStatus('error');
        setError(err.response?.data?.message || 'Verification failed.');
      });
  }, [token]);

  return (
    <AuthLayout>
      <div className="auth__form">
        <span className="eyebrow">Email verification</span>
        <h2 style={{ marginTop: 6 }}>Confirm your address</h2>
        {status === 'loading' ? (
          <p className="text-muted">
            <Spinner /> Verifying…
          </p>
        ) : null}
        {status === 'ok' ? (
          <p>
            Your email is verified. <Link to="/login">Sign in</Link> to continue.
          </p>
        ) : null}
        <ErrorMessage message={status === 'error' ? error : ''} onDismiss={() => setError('')} />
      </div>
    </AuthLayout>
  );
}

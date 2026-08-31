import { NavLink, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext.jsx';
import { initials } from '../utils/format.js';
import { LogoutIcon } from './Icons.jsx';

const LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/summarize', label: 'Summarize' },
  { to: '/history', label: 'History' },
];

export default function Navbar() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="navbar">
      <nav className="navbar__inner">
        <NavLink to="/dashboard" className="brand">
          <span className="brand__mark">CM</span>
          <span className="brand__text">
            CloudMLOps
            <small>Document AI</small>
          </span>
        </NavLink>

        <div className="nav-links">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
          {isAdmin ? (
            <NavLink
              to="/admin"
              className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}
            >
              Admin
            </NavLink>
          ) : null}
        </div>

        <span className="spacer" />

        <div className="nav-user">
          <div className="nav-user__meta">
            <strong>{user?.name}</strong>
            <span>{isAdmin ? 'Administrator' : 'Member'}</span>
          </div>
          <span className="avatar" title={user?.email}>
            {initials(user?.name)}
          </span>
          <button
            type="button"
            className="btn btn--subtle btn--sm"
            onClick={handleLogout}
            aria-label="Sign out"
          >
            <LogoutIcon size={16} />
            <span className="hide-sm">Sign out</span>
          </button>
        </div>
      </nav>
    </header>
  );
}

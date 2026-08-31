import { Link } from 'react-router-dom';

import { ArrowLeftIcon } from '../components/Icons.jsx';

export default function NotFound() {
  return (
    <div className="page">
      <div className="empty" style={{ minHeight: '60vh', alignContent: 'center' }}>
        <span className="eyebrow">404</span>
        <h1>This page does not exist</h1>
        <p>The link may be out of date, or the summary it pointed to was deleted.</p>
        <Link className="btn btn--primary" to="/dashboard">
          <ArrowLeftIcon size={16} />
          Back to the dashboard
        </Link>
      </div>
    </div>
  );
}

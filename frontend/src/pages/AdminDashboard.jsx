import { useCallback, useEffect, useState } from 'react';

import ErrorMessage from '../components/ErrorMessage.jsx';
import { ChartIcon, SearchIcon, UsersIcon } from '../components/Icons.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import Pagination from '../components/Pagination.jsx';
import StarRating from '../components/StarRating.jsx';
import StatCard from '../components/StatCard.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import adminService from '../services/adminService.js';
import { readError } from '../services/api.js';
import { formatDate, formatNumber, formatSeconds } from '../utils/format.js';

const PAGE_SIZE = 8;

const METRIC_LABELS = {
  login: 'Sign-ins',
  registration: 'Registrations',
  document_upload: 'Document uploads',
  text_summarization: 'Text summaries',
  document_summarization: 'Document summaries',
  summary_download: 'Downloads',
  feedback: 'Ratings submitted',
};

export default function AdminDashboard() {
  const { user: currentAdmin } = useAuth();

  const [stats, setStats] = useState(null);
  const [usage, setUsage] = useState(null);
  const [quality, setQuality] = useState(null);
  const [users, setUsers] = useState({ items: [], total: 0, pages: 0, page: 1 });

  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyUserId, setBusyUserId] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const loadMetrics = useCallback(async () => {
    const [statsData, usageData, qualityData] = await Promise.all([
      adminService.stats(),
      adminService.usage(14),
      adminService.quality(),
    ]);
    setStats(statsData);
    setUsage(usageData);
    setQuality(qualityData);
  }, []);

  const loadUsers = useCallback(async () => {
    const response = await adminService.users({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
    });
    setUsers(response);
  }, [page, search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([loadMetrics(), loadUsers()])
      .then(() => !cancelled && setError(''))
      .catch((requestError) => !cancelled && setError(readError(requestError)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [loadMetrics, loadUsers]);

  const toggleActive = async (target) => {
    setBusyUserId(target.id);
    try {
      const updated = await adminService.setStatus(target.id, !target.is_active);
      setNotice(
        `${updated.name} is now ${updated.is_active ? 'active' : 'deactivated'}.` +
          (updated.is_active ? '' : ' Their active sessions were revoked.'),
      );
      await Promise.all([loadUsers(), loadMetrics()]);
      setError('');
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setBusyUserId(null);
    }
  };

  const changeRole = async (target, role) => {
    setBusyUserId(target.id);
    try {
      const updated = await adminService.setRole(target.id, role);
      setNotice(`${updated.name} is now ${updated.role === 'admin' ? 'an administrator' : 'a member'}.`);
      await loadUsers();
      setError('');
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setBusyUserId(null);
    }
  };

  if (loading && !stats) {
    return (
      <div className="page">
        <LoadingSpinner label="Loading platform metrics" />
      </div>
    );
  }

  const peakActivity = Math.max(1, ...(usage?.daily_activity ?? []).map((day) => day.total));
  const maxRatingCount = Math.max(1, ...Object.values(quality?.rating_distribution ?? { 1: 0 }));

  return (
    <div className="page fade-in">
      <div className="page-header">
        <div className="page-header__text">
          <span className="eyebrow">Administration</span>
          <h1>Platform overview</h1>
          <p className="page-subtitle">
            Usage, quality and user management across the whole deployment. These figures come from
            the usage_metrics and feedback tables.
          </p>
        </div>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError('')} />
      <ErrorMessage message={notice} variant="success" onDismiss={() => setNotice('')} />

      <div className="grid grid--4 mb-2">
        <StatCard
          label="Users"
          value={formatNumber(stats?.total_users)}
          hint={`${formatNumber(stats?.active_users)} active`}
          tone="brand"
        />
        <StatCard
          label="Summaries"
          value={formatNumber(stats?.total_summaries)}
          hint={`${formatNumber(stats?.total_requests)} requests total`}
        />
        <StatCard
          label="Avg. processing"
          value={formatSeconds(stats?.average_processing_time_seconds)}
          hint="Per summary, end to end"
          tone="success"
        />
        <StatCard
          label="Avg. rating"
          value={stats?.total_feedback ? `${stats.average_rating.toFixed(2)} / 5` : 'No ratings'}
          hint={`${formatNumber(stats?.total_feedback)} ratings submitted`}
          tone="warning"
        />
      </div>

      <div className="grid grid--3 mb-2">
        <StatCard
          label="Documents uploaded"
          value={formatNumber(stats?.total_documents)}
          hint="PDF, DOCX and TXT"
        />
        <StatCard
          label="Words condensed"
          value={formatNumber(stats?.total_words_summarized)}
          hint="Total input across all requests"
        />
        <StatCard
          label="Failed requests"
          value={formatNumber(stats?.failed_requests)}
          hint={`${quality?.success_rate ?? 0}% success rate`}
          tone={stats?.failed_requests ? 'warning' : 'success'}
        />
      </div>

      <div className="grid grid--2 mb-2">
        <section className="card">
          <div className="card__header">
            <div className="card__title">
              <h3>Requests per day</h3>
              <span>Last 14 days of recorded activity</span>
            </div>
            <ChartIcon size={18} />
          </div>
          {usage?.daily_activity?.length ? (
            <>
              <div className="sparkline" role="img" aria-label="Daily request volume">
                {usage.daily_activity.map((day) => (
                  <div
                    key={day.day}
                    className="sparkline__bar"
                    style={{ height: `${(day.total / peakActivity) * 100}%` }}
                    title={`${day.day}: ${day.total} requests`}
                  />
                ))}
              </div>
              <div className="row row--between mt-2 text-xs text-faint">
                <span>{usage.daily_activity[0].day}</span>
                <span>peak {peakActivity}/day</span>
                <span>{usage.daily_activity[usage.daily_activity.length - 1].day}</span>
              </div>
            </>
          ) : (
            <p className="text-muted text-sm">No activity recorded yet.</p>
          )}
        </section>

        <section className="card">
          <div className="card__header">
            <div className="card__title">
              <h3>Summary quality</h3>
              <span>Distribution of user ratings</span>
            </div>
            <StarRating value={Math.round(quality?.average_rating ?? 0)} readOnly size={16} />
          </div>
          <div className="distribution">
            {[5, 4, 3, 2, 1].map((star) => {
              const count = quality?.rating_distribution?.[star] ?? 0;
              return (
                <div className="distribution__row" key={star}>
                  <span>
                    {star} star{star === 1 ? '' : 's'}
                  </span>
                  <div className="bar">
                    <div
                      className="bar__fill"
                      style={{ width: `${(count / maxRatingCount) * 100}%` }}
                    />
                  </div>
                  <span className="distribution__count">{count}</span>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <section className="card mb-2">
        <div className="card__header">
          <div className="card__title">
            <h3>Usage by request type</h3>
            <span>Every business operation is recorded as a usage metric</span>
          </div>
          {usage?.failures ? (
            <span className="badge badge--danger">{usage.failures} failures</span>
          ) : (
            <span className="badge badge--success">No failures</span>
          )}
        </div>
        <div className="grid grid--4">
          {Object.entries(METRIC_LABELS).map(([key, label]) => (
            <StatCard key={key} label={label} value={formatNumber(usage?.counts_by_type?.[key] ?? 0)} />
          ))}
        </div>
      </section>

      <section className="card card--flush">
        <div style={{ padding: '22px 22px 16px' }}>
          <div className="card__header" style={{ marginBottom: 14 }}>
            <div className="card__title">
              <h3>User management</h3>
              <span>Deactivating a user immediately revokes their active sessions</span>
            </div>
            <UsersIcon size={18} />
          </div>
          <div className="search">
            <span className="search__icon">
              <SearchIcon size={16} />
            </span>
            <input
              className="input"
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search by name or email…"
              aria-label="Search users"
              maxLength={120}
            />
          </div>
        </div>

        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Joined</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.items.map((row) => {
                const isSelf = row.id === currentAdmin?.id;
                return (
                  <tr key={row.id}>
                    <td>
                      <span className="cell-primary">
                        <strong>
                          {row.name}
                          {isSelf ? ' (you)' : ''}
                        </strong>
                        <span>{row.email}</span>
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${row.role === 'admin' ? 'badge--brand' : ''}`}>
                        {row.role}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${row.is_active ? 'badge--success' : 'badge--danger'}`}>
                        {row.is_active ? 'Active' : 'Deactivated'}
                      </span>
                    </td>
                    <td className="text-sm text-muted nowrap">{formatDate(row.created_at)}</td>
                    <td>
                      <div className="row" style={{ justifyContent: 'flex-end' }}>
                        <select
                          className="select"
                          style={{ width: 'auto', padding: '6px 10px', fontSize: '0.8rem' }}
                          value={row.role}
                          disabled={isSelf || busyUserId === row.id}
                          onChange={(event) => changeRole(row, event.target.value)}
                          aria-label={`Role for ${row.name}`}
                        >
                          <option value="user">user</option>
                          <option value="admin">admin</option>
                        </select>
                        <button
                          type="button"
                          className={`btn btn--sm ${row.is_active ? 'btn--danger' : 'btn--ghost'}`}
                          disabled={isSelf || busyUserId === row.id}
                          onClick={() => toggleActive(row)}
                          title={isSelf ? 'You cannot change your own account' : undefined}
                        >
                          {row.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {users.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-muted" style={{ padding: 34 }}>
                    No users matched that search.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div style={{ padding: '0 22px 20px' }}>
          <Pagination
            page={users.page}
            pages={users.pages}
            total={users.total}
            pageSize={PAGE_SIZE}
            onChange={setPage}
            noun="users"
          />
        </div>
      </section>
    </div>
  );
}

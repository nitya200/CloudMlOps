import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import EmptyState from '../components/EmptyState.jsx';
import ErrorMessage from '../components/ErrorMessage.jsx';
import { HistoryIcon, SearchIcon, SparkIcon } from '../components/Icons.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import Pagination from '../components/Pagination.jsx';
import SummaryCard from '../components/SummaryCard.jsx';
import { readError } from '../services/api.js';
import summaryService from '../services/summaryService.js';

const PAGE_SIZE = 6;

export default function History() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyId, setBusyId] = useState(null);

  // Debounce so typing does not fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await summaryService.history({
        page,
        page_size: PAGE_SIZE,
        ...(search ? { search } : {}),
      });
      setData(response);
      setError('');
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (item) => {
    if (!window.confirm(`Delete "${item.title}"? This cannot be undone.`)) return;
    setBusyId(item.id);
    try {
      await summaryService.deleteSummary(item.id);
      setNotice(`Deleted "${item.title}".`);
      // Step back a page if the last item on this page just disappeared.
      if (data.items.length === 1 && page > 1) setPage(page - 1);
      else await load();
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const handleDownload = async (item) => {
    setBusyId(item.id);
    try {
      await summaryService.download(item.id, item.title);
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="page fade-in">
      <div className="page-header">
        <div className="page-header__text">
          <span className="eyebrow">History</span>
          <h1>Your summaries</h1>
          <p className="page-subtitle">
            Every summary you generate is stored with its metrics. Search across titles, summaries
            and the original text.
          </p>
        </div>
        <Link className="btn btn--primary" to="/summarize">
          <SparkIcon size={17} />
          New summary
        </Link>
      </div>

      <div className="row mb-2">
        <div className="search">
          <span className="search__icon">
            <SearchIcon size={16} />
          </span>
          <input
            className="input"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search your summaries…"
            aria-label="Search summaries"
            maxLength={200}
          />
        </div>
        {search ? (
          <button type="button" className="btn btn--ghost" onClick={() => setSearchInput('')}>
            Clear
          </button>
        ) : null}
      </div>

      <ErrorMessage message={error} onDismiss={() => setError('')} />
      <ErrorMessage message={notice} variant="success" onDismiss={() => setNotice('')} />

      {loading ? (
        <LoadingSpinner label="Loading history" />
      ) : data.items.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={<HistoryIcon size={24} />}
            title={search ? 'No matches found' : 'Your history is empty'}
            description={
              search
                ? `Nothing matched "${search}". Try a different word or clear the search.`
                : 'Once you generate a summary it will show up here with its metrics and rating.'
            }
            action={
              search ? (
                <button type="button" className="btn btn--ghost" onClick={() => setSearchInput('')}>
                  Clear search
                </button>
              ) : (
                <Link className="btn btn--primary" to="/summarize">
                  Create your first summary
                </Link>
              )
            }
          />
        </div>
      ) : (
        <>
          <div className="grid grid--2">
            {data.items.map((item) => (
              <SummaryCard
                key={item.id}
                item={item}
                onDelete={handleDelete}
                onDownload={handleDownload}
                busy={busyId === item.id}
              />
            ))}
          </div>
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            pageSize={PAGE_SIZE}
            onChange={setPage}
            noun="summaries"
          />
        </>
      )}
    </div>
  );
}

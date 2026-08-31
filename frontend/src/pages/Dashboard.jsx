import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import EmptyState from '../components/EmptyState.jsx';
import ErrorMessage from '../components/ErrorMessage.jsx';
import { DocumentIcon, HistoryIcon, SparkIcon, UploadIcon } from '../components/Icons.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import StatCard from '../components/StatCard.jsx';
import SummaryCard from '../components/SummaryCard.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { readError } from '../services/api.js';
import summaryService from '../services/summaryService.js';
import { formatNumber, formatRelative, formatSeconds } from '../utils/format.js';

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const [state, setState] = useState({ loading: true, error: '' });
  const [history, setHistory] = useState({ items: [], total: 0 });
  const [documents, setDocuments] = useState({ total: 0 });
  const [engine, setEngine] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setState({ loading: true, error: '' });
    try {
      const [recent, docs, options] = await Promise.all([
        summaryService.history({ page: 1, page_size: 4 }),
        summaryService.listDocuments({ page: 1, page_size: 1 }),
        summaryService.options(),
      ]);
      setHistory(recent);
      setDocuments(docs);
      setEngine(options);
      setState({ loading: false, error: '' });
    } catch (error) {
      setState({ loading: false, error: readError(error) });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (item) => {
    setBusyId(item.id);
    try {
      await summaryService.deleteSummary(item.id);
      await load();
    } catch (error) {
      setState((prev) => ({ ...prev, error: readError(error) }));
    } finally {
      setBusyId(null);
    }
  };

  const handleDownload = async (item) => {
    setBusyId(item.id);
    try {
      await summaryService.download(item.id, item.title);
    } catch (error) {
      setState((prev) => ({ ...prev, error: readError(error) }));
    } finally {
      setBusyId(null);
    }
  };

  const averageTime = history.items.length
    ? history.items.reduce((sum, item) => sum + item.processing_time_seconds, 0) /
      history.items.length
    : 0;
  const wordsIn = history.items.reduce((sum, item) => sum + item.input_word_count, 0);

  if (state.loading) {
    return (
      <div className="page">
        <LoadingSpinner label="Loading your workspace" />
      </div>
    );
  }

  return (
    <div className="page fade-in">
      <div className="page-header">
        <div className="page-header__text">
          <span className="eyebrow">Dashboard</span>
          <h1>Welcome back, {user?.name?.split(' ')[0]}</h1>
          <p className="page-subtitle">
            Upload a document or paste text, and FLAN-T5 will condense it into a summary you can
            search, download and rate.
          </p>
        </div>
        <div className="row">
          <Link className="btn btn--primary" to="/summarize">
            <SparkIcon size={17} />
            New summary
          </Link>
          <Link className="btn btn--ghost" to="/history">
            <HistoryIcon size={17} />
            History
          </Link>
        </div>
      </div>

      <ErrorMessage message={state.error} onDismiss={() => setState((p) => ({ ...p, error: '' }))} />

      <div className="grid grid--4 mt-2">
        <StatCard
          label="Summaries generated"
          value={formatNumber(history.total)}
          hint={history.items[0] ? `Latest ${formatRelative(history.items[0].created_at)}` : 'None yet'}
          tone="brand"
        />
        <StatCard
          label="Documents uploaded"
          value={formatNumber(documents.total)}
          hint="PDF, DOCX and TXT"
        />
        <StatCard
          label="Avg. generation time"
          value={formatSeconds(averageTime)}
          hint="Across your recent summaries"
          tone="success"
        />
        <StatCard
          label="Words condensed"
          value={formatNumber(wordsIn)}
          hint="In the last 4 summaries"
        />
      </div>

      <div className="grid grid--2 mt-2">
        <section className="card">
          <div className="card__header">
            <div className="card__title">
              <h3>Start a new summary</h3>
              <span>Two ways in, one pipeline out</span>
            </div>
          </div>
          <div className="stack">
            <Link className="file-chip" to="/summarize" style={{ textDecoration: 'none' }}>
              <span className="file-chip__icon">
                <UploadIcon size={18} />
              </span>
              <span className="file-chip__meta">
                <strong>Upload a document</strong>
                <span>PDF, DOCX or TXT up to 10 MB — text is extracted automatically</span>
              </span>
            </Link>
            <Link className="file-chip" to="/summarize" style={{ textDecoration: 'none' }}>
              <span className="file-chip__icon">
                <DocumentIcon size={18} />
              </span>
              <span className="file-chip__meta">
                <strong>Paste raw text</strong>
                <span>Drop in an article or set of notes and pick a summary length</span>
              </span>
            </Link>
          </div>
        </section>

        <section className="card">
          <div className="card__header">
            <div className="card__title">
              <h3>Summarization engine</h3>
              <span>Live configuration reported by the API</span>
            </div>
            <span className={`badge ${engine?.backend === 'flan-t5' ? 'badge--success' : 'badge--warning'}`}>
              {engine?.backend ?? 'unknown'}
            </span>
          </div>
          <div className="stack">
            <div className="meta-list">
              <span>
                <strong>Model</strong> <code>{engine?.model ?? '—'}</code>
              </span>
            </div>
            {engine?.backend === 'extractive' ? (
              <ErrorMessage
                variant="warning"
                title="Running on the extractive fallback"
                message="transformers and torch are not installed, so summaries are produced by ranking sentences instead of generating new text. Install requirements-ai.txt to enable FLAN-T5."
              />
            ) : (
              <ErrorMessage
                variant="info"
                title="Abstractive summarization active"
                message="FLAN-T5 rewrites the document in its own words. Long documents are summarized in chunks and then merged."
              />
            )}
            {isAdmin ? (
              <Link className="btn btn--ghost btn--sm" to="/admin">
                View platform metrics
              </Link>
            ) : null}
          </div>
        </section>
      </div>

      <section className="mt-2">
        <div className="page-header" style={{ marginBottom: 16 }}>
          <div className="page-header__text">
            <h2>Recent summaries</h2>
          </div>
          {history.total > 4 ? (
            <Link className="btn btn--subtle btn--sm" to="/history">
              View all {history.total}
            </Link>
          ) : null}
        </div>

        {history.items.length === 0 ? (
          <div className="card">
            <EmptyState
              icon={<SparkIcon size={24} />}
              title="No summaries yet"
              description="Generate your first summary and it will appear here, ready to search, download or rate."
              action={
                <Link className="btn btn--primary" to="/summarize">
                  Create a summary
                </Link>
              }
            />
          </div>
        ) : (
          <div className="grid grid--2">
            {history.items.map((item) => (
              <SummaryCard
                key={item.id}
                item={item}
                onDelete={handleDelete}
                onDownload={handleDownload}
                busy={busyId === item.id}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

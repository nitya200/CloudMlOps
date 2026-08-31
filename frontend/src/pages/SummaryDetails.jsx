import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage.jsx';
import { ArrowLeftIcon, CopyIcon, DownloadIcon, TrashIcon } from '../components/Icons.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import StarRating from '../components/StarRating.jsx';
import StatCard from '../components/StatCard.jsx';
import { readError } from '../services/api.js';
import summaryService from '../services/summaryService.js';
import {
  formatDate,
  formatNumber,
  formatPercent,
  formatSeconds,
  readingTime,
} from '../utils/format.js';

export default function SummaryDetails() {
  const { summaryId } = useParams();
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [comment, setComment] = useState('');
  const [rating, setRating] = useState(0);
  const [savingFeedback, setSavingFeedback] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await summaryService.getSummary(summaryId);
      setSummary(data);
      setRating(data.my_rating ?? 0);
      setError('');
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setLoading(false);
    }
  }, [summaryId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleFeedback = async (stars) => {
    setRating(stars);
    setSavingFeedback(true);
    try {
      await summaryService.rate(summaryId, stars, comment);
      setNotice(`Rating saved — ${stars} out of 5.`);
      setError('');
    } catch (requestError) {
      setError(readError(requestError));
      setRating(summary?.my_rating ?? 0);
    } finally {
      setSavingFeedback(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(summary.summary_text);
      setNotice('Summary copied to the clipboard.');
    } catch {
      setError('Your browser blocked clipboard access. Select the text and copy it manually.');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this summary? This cannot be undone.')) return;
    try {
      await summaryService.deleteSummary(summaryId);
      navigate('/history', { replace: true });
    } catch (requestError) {
      setError(readError(requestError));
    }
  };

  if (loading) {
    return (
      <div className="page">
        <LoadingSpinner label="Loading summary" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="page">
        <ErrorMessage message={error || 'This summary could not be found.'} />
        <Link className="btn btn--ghost mt-2" to="/history">
          <ArrowLeftIcon size={16} />
          Back to history
        </Link>
      </div>
    );
  }

  return (
    <div className="page fade-in">
      <Link className="btn btn--subtle btn--sm" to="/history" style={{ marginBottom: 14 }}>
        <ArrowLeftIcon size={15} />
        Back to history
      </Link>

      <div className="page-header">
        <div className="page-header__text">
          <span className="eyebrow">Summary</span>
          <h1>{summary.title}</h1>
          <div className="meta-list">
            <span>{formatDate(summary.created_at)}</span>
            <span className="badge badge--brand">{summary.summary_length}</span>
            <span className="badge">
              {summary.source_type === 'document' ? summary.document_filename : 'Pasted text'}
            </span>
            <span className="badge">{summary.backend}</span>
          </div>
        </div>
        <div className="row">
          <button type="button" className="btn btn--ghost" onClick={handleCopy}>
            <CopyIcon size={16} />
            Copy
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => summaryService.download(summary.id, summary.title)}
          >
            <DownloadIcon size={16} />
            Download
          </button>
          <button type="button" className="btn btn--danger" onClick={handleDelete}>
            <TrashIcon size={16} />
            Delete
          </button>
        </div>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError('')} />
      <ErrorMessage message={notice} variant="success" onDismiss={() => setNotice('')} />

      <div className="grid grid--4 mb-2">
        <StatCard
          label="Summary length"
          value={formatNumber(summary.word_count)}
          hint={`words · ${readingTime(summary.word_count)}`}
          tone="brand"
        />
        <StatCard
          label="Original length"
          value={formatNumber(summary.input_word_count)}
          hint={`words · ${readingTime(summary.input_word_count)}`}
        />
        <StatCard
          label="Compression"
          value={formatPercent(summary.compression_ratio, 1)}
          hint="of the original length"
          tone="success"
        />
        <StatCard
          label="Processing time"
          value={formatSeconds(summary.processing_time_seconds)}
          hint={`${summary.chunk_count} chunk${summary.chunk_count === 1 ? '' : 's'} · ${summary.model_name}`}
        />
      </div>

      <section className="card mb-2">
        <div className="card__header">
          <div className="card__title">
            <h3>Generated summary</h3>
            <span>Produced by {summary.model_name}</span>
          </div>
        </div>
        <div className="summary-output">{summary.summary_text}</div>
      </section>

      <div className="grid grid--2">
        <section className="card">
          <div className="card__header">
            <div className="card__title">
              <h3>Rate this summary</h3>
              <span>Ratings feed the quality metrics on the admin dashboard</span>
            </div>
          </div>
          <div className="stack">
            <StarRating value={rating} onChange={handleFeedback} size={28} />
            <div className="field">
              <label htmlFor="comment">Comment (optional)</label>
              <textarea
                id="comment"
                className="textarea"
                style={{ minHeight: 96 }}
                maxLength={1000}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="What worked or did not work about this summary?"
              />
              <p className="field__hint">{comment.length}/1000</p>
            </div>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!rating || savingFeedback}
              onClick={() => handleFeedback(rating)}
            >
              {savingFeedback ? 'Saving…' : 'Save rating'}
            </button>
          </div>
        </section>

        <section className="card">
          <div className="card__header">
            <div className="card__title">
              <h3>Source text</h3>
              <span>First 600 characters of the input</span>
            </div>
          </div>
          <div className="summary-output summary-output--muted">{summary.input_preview}</div>
        </section>
      </div>
    </div>
  );
}

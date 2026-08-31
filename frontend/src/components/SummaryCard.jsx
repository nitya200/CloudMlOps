import { Link } from 'react-router-dom';

import { formatNumber, formatPercent, formatRelative, formatSeconds } from '../utils/format.js';
import { DownloadIcon, TrashIcon } from './Icons.jsx';
import StarRating from './StarRating.jsx';

/** One history entry. */
export default function SummaryCard({ item, onDelete, onDownload, busy = false }) {
  const compression = item.input_word_count
    ? item.word_count / item.input_word_count
    : null;

  return (
    <article className="card card--interactive summary-card fade-in">
      <div className="summary-card__title">
        <h3>
          <Link to={`/summaries/${item.id}`}>{item.title}</Link>
        </h3>
        <span className="badge badge--brand">{item.summary_length}</span>
        <span className="badge">{item.source_type === 'document' ? 'Document' : 'Text'}</span>
        {item.my_rating ? (
          <span className="badge badge--warning">{item.my_rating}/5 rated</span>
        ) : null}
      </div>

      <p className="summary-card__preview">{item.summary_preview}</p>

      <div className="meta-list">
        <span>{formatRelative(item.created_at)}</span>
        <span>
          <strong>{formatNumber(item.input_word_count)}</strong> words in
        </span>
        <span>
          <strong>{formatNumber(item.word_count)}</strong> words out
        </span>
        {compression !== null ? <span>{formatPercent(compression)} of original</span> : null}
        <span>{formatSeconds(item.processing_time_seconds)}</span>
        {item.document_filename ? <span className="truncate">{item.document_filename}</span> : null}
      </div>

      <div className="row row--between">
        <StarRating value={item.my_rating ?? 0} readOnly size={16} />
        <div className="row">
          <Link className="btn btn--ghost btn--sm" to={`/summaries/${item.id}`}>
            Open
          </Link>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => onDownload(item)}
            disabled={busy}
          >
            <DownloadIcon size={15} />
            <span className="hide-sm">Download</span>
          </button>
          <button
            type="button"
            className="btn btn--danger btn--sm"
            onClick={() => onDelete(item)}
            disabled={busy}
            aria-label={`Delete ${item.title}`}
          >
            <TrashIcon size={15} />
          </button>
        </div>
      </div>
    </article>
  );
}

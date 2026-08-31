import { ChevronLeftIcon, ChevronRightIcon } from './Icons.jsx';

export default function Pagination({ page, pages, total, pageSize, onChange, noun = 'items' }) {
  if (!total) return null;
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  const totalPages = Math.max(pages, 1);

  return (
    <div className="pagination">
      <span className="pagination__info">
        Showing {first}-{last} of {total} {noun}
      </span>
      <div className="pagination__controls">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeftIcon size={15} />
          Previous
        </button>
        <span className="pagination__page">
          {page} / {totalPages}
        </span>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          Next
          <ChevronRightIcon size={15} />
        </button>
      </div>
    </div>
  );
}

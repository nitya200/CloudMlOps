import { useState } from 'react';

import { StarIcon } from './Icons.jsx';

/** 1-5 star control. Pass readOnly to render a static rating. */
export default function StarRating({ value = 0, onChange, readOnly = false, size = 22 }) {
  const [hovered, setHovered] = useState(0);
  const active = hovered || value;

  return (
    <span
      className={`stars ${readOnly ? 'stars--readonly' : ''}`}
      role={readOnly ? 'img' : 'radiogroup'}
      aria-label={readOnly ? `Rated ${value} out of 5` : 'Rate this summary'}
      onMouseLeave={() => setHovered(0)}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={star <= active ? 'is-filled' : ''}
          disabled={readOnly}
          onMouseEnter={() => !readOnly && setHovered(star)}
          onClick={() => !readOnly && onChange?.(star)}
          aria-label={`${star} star${star > 1 ? 's' : ''}`}
          aria-checked={!readOnly && star === value}
          role={readOnly ? undefined : 'radio'}
        >
          <StarIcon size={size} filled={star <= active} />
        </button>
      ))}
    </span>
  );
}

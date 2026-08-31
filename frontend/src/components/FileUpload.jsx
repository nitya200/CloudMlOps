import { useRef, useState } from 'react';

import { formatBytes } from '../utils/format.js';
import { DocumentIcon, TrashIcon, UploadIcon } from './Icons.jsx';

const ACCEPTED = '.pdf,.docx,.txt';
const ACCEPTED_EXTENSIONS = ['pdf', 'docx', 'txt'];

/** Drag-and-drop file picker with client-side pre-validation. */
export default function FileUpload({ file, onSelect, onClear, maxSizeMb = 10, disabled = false }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState('');

  const validateAndSelect = (candidate) => {
    if (!candidate) return;
    const extension = candidate.name.split('.').pop()?.toLowerCase();
    // Fail fast in the browser; the API repeats these checks authoritatively.
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setLocalError(`Only ${ACCEPTED_EXTENSIONS.join(', ')} files are supported.`);
      return;
    }
    if (candidate.size > maxSizeMb * 1024 * 1024) {
      setLocalError(`That file is ${formatBytes(candidate.size)}; the limit is ${maxSizeMb} MB.`);
      return;
    }
    setLocalError('');
    onSelect(candidate);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    validateAndSelect(event.dataTransfer.files?.[0]);
  };

  if (file) {
    return (
      <div className="stack">
        <div className="file-chip">
          <span className="file-chip__icon">{file.name.split('.').pop()?.toUpperCase()}</span>
          <span className="file-chip__meta">
            <strong>{file.name}</strong>
            <span>{formatBytes(file.size)}</span>
          </span>
          <button
            type="button"
            className="btn btn--subtle btn--sm"
            onClick={() => {
              setLocalError('');
              onClear();
            }}
            disabled={disabled}
            aria-label="Remove file"
          >
            <TrashIcon size={16} />
          </button>
        </div>
        {localError ? <p className="field__hint field__hint--error">{localError}</p> : null}
      </div>
    );
  }

  return (
    <div className="stack">
      <div
        className={`dropzone ${dragging ? 'is-dragging' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        aria-disabled={disabled}
      >
        <span className="dropzone__icon">
          {dragging ? <UploadIcon size={22} /> : <DocumentIcon size={22} />}
        </span>
        <strong>Drop a document here, or click to browse</strong>
        <span>PDF, DOCX or TXT &middot; up to {maxSizeMb} MB</span>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          hidden
          disabled={disabled}
          onChange={(event) => {
            validateAndSelect(event.target.files?.[0]);
            event.target.value = ''; // allows re-selecting the same file
          }}
        />
      </div>
      {localError ? <p className="field__hint field__hint--error">{localError}</p> : null}
    </div>
  );
}

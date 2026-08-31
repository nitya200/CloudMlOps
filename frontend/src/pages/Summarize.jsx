import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage.jsx';
import FileUpload from '../components/FileUpload.jsx';
import { CopyIcon, DownloadIcon, SparkIcon } from '../components/Icons.jsx';
import { Spinner } from '../components/LoadingSpinner.jsx';
import StarRating from '../components/StarRating.jsx';
import SummaryLengthPicker from '../components/SummaryLengthPicker.jsx';
import TextInput from '../components/TextInput.jsx';
import { readError } from '../services/api.js';
import summaryService from '../services/summaryService.js';
import { formatNumber, formatPercent, formatSeconds } from '../utils/format.js';

const MIN_CHARS = 200;

export default function Summarize() {
  const [mode, setMode] = useState('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [length, setLength] = useState('medium');
  const [title, setTitle] = useState('');

  const [options, setOptions] = useState(null);
  const [limits, setLimits] = useState({ max_size_mb: 10 });
  const [status, setStatus] = useState('idle'); // idle | uploading | generating
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [rating, setRating] = useState(0);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    summaryService
      .options()
      .then(setOptions)
      .catch(() => setOptions(null));
    summaryService
      .supportedTypes()
      .then(setLimits)
      .catch(() => setLimits({ max_size_mb: 10 }));
  }, []);

  const busy = status !== 'idle';
  const canSubmit =
    mode === 'text' ? text.trim().length >= MIN_CHARS : Boolean(file);

  const handleGenerate = async (event) => {
    event.preventDefault();
    setError('');
    setNotice('');
    setResult(null);
    setRating(0);

    try {
      if (mode === 'text') {
        setStatus('generating');
        const summary = await summaryService.summarizeText({
          text: text.trim(),
          summary_length: length,
          title: title.trim() || null,
        });
        setResult(summary);
      } else {
        setStatus('uploading');
        setProgress(0);
        const document = await summaryService.uploadDocument(file, setProgress);
        setStatus('generating');
        const summary = await summaryService.summarizeDocument(document.id, {
          summary_length: length,
          title: title.trim() || document.filename,
        });
        setResult({ ...summary, source_filename: document.filename });
        setNotice(
          `Extracted ${formatNumber(document.word_count)} words from ${document.filename}.`,
        );
      }
    } catch (requestError) {
      setError(readError(requestError));
    } finally {
      setStatus('idle');
      setProgress(0);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.summary_text);
      setNotice('Summary copied to the clipboard.');
    } catch {
      setError('Your browser blocked clipboard access. Select the text and copy it manually.');
    }
  };

  const handleRate = async (stars) => {
    setRating(stars);
    try {
      await summaryService.rate(result.id, stars);
      setNotice(`Thanks — rated ${stars} out of 5.`);
    } catch (requestError) {
      setError(readError(requestError));
      setRating(0);
    }
  };

  const handleReset = () => {
    setText('');
    setFile(null);
    setTitle('');
    setResult(null);
    setRating(0);
    setError('');
    setNotice('');
  };

  return (
    <div className="page fade-in">
      <div className="page-header">
        <div className="page-header__text">
          <span className="eyebrow">Summarize</span>
          <h1>Generate a summary</h1>
          <p className="page-subtitle">
            Paste text or upload a document, choose how much detail you want, and the model will
            produce an abstractive summary. Everything is saved to your history.
          </p>
        </div>
        {result ? (
          <button type="button" className="btn btn--ghost" onClick={handleReset}>
            Start another
          </button>
        ) : null}
      </div>

      <div className="grid grid--2">
        {/* ---- Input ---- */}
        <form className="card stack" onSubmit={handleGenerate}>
          <div className="card__header" style={{ marginBottom: 0 }}>
            <div className="card__title">
              <h3>1. Choose your source</h3>
              <span>Both paths run through the same summarization service</span>
            </div>
          </div>

          <div className="segmented" role="group" aria-label="Input mode">
            <button
              type="button"
              aria-pressed={mode === 'text'}
              onClick={() => setMode('text')}
              disabled={busy}
            >
              Paste text
            </button>
            <button
              type="button"
              aria-pressed={mode === 'file'}
              onClick={() => setMode('file')}
              disabled={busy}
            >
              Upload document
            </button>
          </div>

          {mode === 'text' ? (
            <TextInput value={text} onChange={setText} disabled={busy} minChars={MIN_CHARS} />
          ) : (
            <FileUpload
              file={file}
              onSelect={setFile}
              onClear={() => setFile(null)}
              maxSizeMb={limits.max_size_mb ?? 10}
              disabled={busy}
            />
          )}

          <div className="panel-divider" />

          <div className="card__title">
            <h3>2. Configure the output</h3>
          </div>

          <SummaryLengthPicker
            value={length}
            onChange={setLength}
            options={options?.lengths}
            disabled={busy}
          />

          <div className="field">
            <label htmlFor="summary-title">Title (optional)</label>
            <input
              id="summary-title"
              className="input"
              value={title}
              maxLength={255}
              disabled={busy}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Defaults to the filename or the first line of text"
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary btn--lg btn--block"
            disabled={busy || !canSubmit}
          >
            {busy ? <Spinner /> : <SparkIcon size={18} />}
            {status === 'uploading'
              ? `Uploading… ${progress}%`
              : status === 'generating'
                ? 'Generating summary…'
                : 'Generate summary'}
          </button>

          {!canSubmit && !busy ? (
            <p className="field__hint">
              {mode === 'text'
                ? `Add at least ${MIN_CHARS} characters of text to continue.`
                : 'Select a PDF, DOCX or TXT file to continue.'}
            </p>
          ) : null}
        </form>

        {/* ---- Output ---- */}
        <section className="card stack">
          <div className="card__header" style={{ marginBottom: 0 }}>
            <div className="card__title">
              <h3>Generated summary</h3>
              <span>
                {result
                  ? `${result.backend} · ${result.model_name}`
                  : 'The result will appear here'}
              </span>
            </div>
            {result ? <span className="badge badge--success">Saved to history</span> : null}
          </div>

          <ErrorMessage message={error} onDismiss={() => setError('')} />
          <ErrorMessage message={notice} variant="success" onDismiss={() => setNotice('')} />

          {busy ? (
            <div className="loading-block">
              <Spinner large />
              <div>
                <strong>
                  {status === 'uploading' ? 'Uploading and extracting text' : 'Summarizing'}
                </strong>
                <p className="loading-block__hint">
                  Long documents are split into chunks, summarized separately and then merged. On
                  CPU this can take up to a couple of minutes.
                </p>
              </div>
            </div>
          ) : null}

          {!busy && !result ? (
            <div className="empty">
              <div className="empty__icon">
                <SparkIcon size={24} />
              </div>
              <h3>Nothing generated yet</h3>
              <p>
                Pick a source on the left and press <strong>Generate summary</strong>.
              </p>
            </div>
          ) : null}

          {!busy && result ? (
            <div className="stack fade-in">
              <div className="summary-output">{result.summary_text}</div>

              <div className="meta-list">
                <span>
                  <strong>{formatNumber(result.word_count)}</strong> words
                </span>
                <span>{formatPercent(result.compression_ratio)} of the original</span>
                <span>{formatSeconds(result.processing_time_seconds)}</span>
                <span>
                  {result.chunk_count} chunk{result.chunk_count === 1 ? '' : 's'}
                </span>
              </div>

              <div className="panel-divider" />

              <div className="row row--between">
                <div className="row">
                  <span className="text-sm text-muted">Rate this summary</span>
                  <StarRating value={rating} onChange={handleRate} size={20} />
                </div>
                <div className="row">
                  <button type="button" className="btn btn--ghost btn--sm" onClick={handleCopy}>
                    <CopyIcon size={15} />
                    Copy
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => summaryService.download(result.id, title || 'summary')}
                  >
                    <DownloadIcon size={15} />
                    Download
                  </button>
                  <Link className="btn btn--ghost btn--sm" to={`/summaries/${result.id}`}>
                    Details
                  </Link>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

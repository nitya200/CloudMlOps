const MIN_CHARS = 200;

/** Textarea for pasted source text, with a live length budget. */
export default function TextInput({ value, onChange, disabled = false, minChars = MIN_CHARS }) {
  const characters = value.trim().length;
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  const short = characters > 0 && characters < minChars;

  return (
    <div className="field">
      <label htmlFor="source-text">Paste the text you want summarized</label>
      <textarea
        id="source-text"
        className="textarea"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        placeholder={`Paste an article, report or set of notes here. At least ${minChars} characters are needed for a meaningful summary.`}
        spellCheck="false"
      />
      <p className={`field__hint ${short ? 'field__hint--error' : ''}`}>
        {characters.toLocaleString()} characters &middot; {words.toLocaleString()} words
        {short ? ` — ${minChars - characters} more characters needed` : ''}
      </p>
    </div>
  );
}

const FALLBACK = [
  { value: 'short', label: 'Short (2-3 sentences)', target_words: 55 },
  { value: 'medium', label: 'Medium (one paragraph)', target_words: 130 },
  { value: 'long', label: 'Long (detailed)', target_words: 260 },
];

/** Maps to the backend's Strategy objects, fetched from /api/summaries/options. */
export default function SummaryLengthPicker({ value, onChange, options, disabled = false }) {
  const choices = options?.length ? options : FALLBACK;

  return (
    <div className="field">
      <label id="summary-length-label">Summary length</label>
      <div className="option-cards" role="group" aria-labelledby="summary-length-label">
        {choices.map((choice) => (
          <button
            key={choice.value}
            type="button"
            className="option-card"
            aria-pressed={value === choice.value}
            disabled={disabled}
            onClick={() => onChange(choice.value)}
          >
            <strong>{choice.label.split(' (')[0]}</strong>
            <span>~{choice.target_words} words</span>
          </button>
        ))}
      </div>
    </div>
  );
}

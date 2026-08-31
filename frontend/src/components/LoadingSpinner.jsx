export function Spinner({ large = false }) {
  return <span className={large ? 'spinner spinner--lg' : 'spinner'} role="status" />;
}

export default function LoadingSpinner({ label = 'Loading', hint }) {
  return (
    <div className="loading-block" role="status" aria-live="polite">
      <Spinner large />
      <div>
        <strong>{label}</strong>
        {hint ? <p className="loading-block__hint text-muted">{hint}</p> : null}
      </div>
    </div>
  );
}

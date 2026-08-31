import { AlertIcon, CheckIcon } from './Icons.jsx';

/** Inline alert used for both failures and confirmations. */
export default function ErrorMessage({ message, title, variant = 'error', onDismiss }) {
  if (!message) return null;
  const Icon = variant === 'success' ? CheckIcon : AlertIcon;
  return (
    <div className={`alert alert--${variant} fade-in`} role={variant === 'error' ? 'alert' : 'status'}>
      <Icon size={17} />
      <div className="alert__body">
        {title ? <strong>{title}</strong> : null}
        {message}
      </div>
      {onDismiss ? (
        <button type="button" className="btn btn--subtle btn--sm" onClick={onDismiss}>
          Dismiss
        </button>
      ) : null}
    </div>
  );
}

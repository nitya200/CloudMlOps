/** Presentation-only formatting helpers. */

export function formatNumber(value) {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat().format(value);
}

export function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / 1024 ** exponent;
  return `${size >= 10 || exponent === 0 ? Math.round(size) : size.toFixed(1)} ${units[exponent]}`;
}

export function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  if (seconds < 60) return `${seconds.toFixed(2)} s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

export function formatPercent(ratio, digits = 0) {
  if (ratio === null || ratio === undefined) return '-';
  return `${(ratio * 100).toFixed(digits)}%`;
}

export function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelative(value) {
  if (!value) return '-';
  const diffSeconds = (Date.now() - new Date(value).getTime()) / 1000;
  const steps = [
    [60, 'second', 1],
    [3600, 'minute', 60],
    [86400, 'hour', 3600],
    [604800, 'day', 86400],
    [2629800, 'week', 604800],
    [31557600, 'month', 2629800],
  ];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  for (const [limit, unit, divisor] of steps) {
    if (Math.abs(diffSeconds) < limit) {
      return formatter.format(-Math.round(diffSeconds / divisor), unit);
    }
  }
  return formatter.format(-Math.round(diffSeconds / 31557600), 'year');
}

export function initials(name) {
  if (!name) return '?';
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export function readingTime(words) {
  if (!words) return '-';
  const minutes = Math.max(1, Math.round(words / 220));
  return `${minutes} min read`;
}

/**
 * Detect hosted deployments with strict HTTP timeouts or cross-origin API calls.
 * App Runner enforces ~120s on the request path; FLAN-T5 on long docs often exceeds that.
 */
export function isProductionCloudHost() {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (
      host.includes('awsapprunner.com') ||
      host.includes('netlify.app') ||
      host.includes('onrender.com')
    ) {
      return true;
    }
  }
  const apiBase = import.meta.env.VITE_API_BASE_URL || '';
  return apiBase.includes('awsapprunner.com') || apiBase.includes('onrender.com');
}

/** Rough guidance shown in the Summarize UI on cloud hosts. */
export const CLOUD_SUMMARIZE_HINT =
  'On AWS, each request must finish within about 2 minutes. Use Concise style and Short or Medium length for larger documents. Abstractive + Long works best locally or on shorter text.';

export function isHeavyCloudSummarize(style, length) {
  return style === 'abstractive' && (length === 'long' || length === 'medium');
}

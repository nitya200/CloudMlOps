/**
 * Inline SVG icons.
 * Keeping them local avoids shipping an entire icon package for a dozen glyphs.
 */

const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function Svg({ size = 18, children, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      {...base}
      {...rest}
    >
      {children}
    </svg>
  );
}

export const SparkIcon = (props) => (
  <Svg {...props}>
    <path d="M12 3v4M12 17v4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M3 12h4M17 12h4M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
  </Svg>
);

export const UploadIcon = (props) => (
  <Svg {...props}>
    <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" />
    <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
  </Svg>
);

export const DownloadIcon = (props) => (
  <Svg {...props}>
    <path d="M12 4v12m0 0 4.5-4.5M12 16l-4.5-4.5" />
    <path d="M4 18v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1" />
  </Svg>
);

export const CopyIcon = (props) => (
  <Svg {...props}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M15 5H6a2 2 0 0 0-2 2v9" />
  </Svg>
);

export const TrashIcon = (props) => (
  <Svg {...props}>
    <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" />
    <path d="M10 11v6M14 11v6" />
  </Svg>
);

export const SearchIcon = (props) => (
  <Svg {...props}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4.5 4.5" />
  </Svg>
);

export const HistoryIcon = (props) => (
  <Svg {...props}>
    <path d="M3.5 12a8.5 8.5 0 1 0 2.8-6.3" />
    <path d="M3 4v4h4" />
    <path d="M12 8v4.5l3 1.8" />
  </Svg>
);

export const StarIcon = ({ size = 20, filled = false }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    aria-hidden="true"
    fill={filled ? 'currentColor' : 'none'}
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3.6l2.6 5.3 5.9.85-4.25 4.15 1 5.9L12 17l-5.25 2.8 1-5.9L3.5 9.75l5.9-.85z" />
  </svg>
);

export const DocumentIcon = (props) => (
  <Svg {...props}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5M9 13h6M9 17h4" />
  </Svg>
);

export const UsersIcon = (props) => (
  <Svg {...props}>
    <circle cx="9" cy="8" r="3.2" />
    <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
    <path d="M16 5.3a3.2 3.2 0 0 1 0 6.2M17.5 20a5.5 5.5 0 0 0-2-4.3" />
  </Svg>
);

export const ChartIcon = (props) => (
  <Svg {...props}>
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
  </Svg>
);

export const LogoutIcon = (props) => (
  <Svg {...props}>
    <path d="M14 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
    <path d="M10 12H3m0 0 3.5-3.5M3 12l3.5 3.5" />
  </Svg>
);

export const AlertIcon = (props) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v4.5M12 16h.01" />
  </Svg>
);

export const CheckIcon = (props) => (
  <Svg {...props}>
    <path d="M5 12.5l4.5 4.5L19 7" />
  </Svg>
);

export const ArrowLeftIcon = (props) => (
  <Svg {...props}>
    <path d="M19 12H5m0 0 6-6M5 12l6 6" />
  </Svg>
);

export const ChevronLeftIcon = (props) => (
  <Svg {...props}>
    <path d="M14.5 5.5 8 12l6.5 6.5" />
  </Svg>
);

export const ChevronRightIcon = (props) => (
  <Svg {...props}>
    <path d="M9.5 5.5 16 12l-6.5 6.5" />
  </Svg>
);

export const TextIcon = (props) => (
  <Svg {...props}>
    <path d="M5 6h14M5 12h14M5 18h8" />
  </Svg>
);

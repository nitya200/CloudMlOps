const PIPELINE = [
  'Upload a PDF, DOCX or TXT file, or paste raw text',
  'FastAPI extracts the text and picks a summary strategy',
  'FLAN-T5 generates an abstractive summary',
  'Everything is stored in PostgreSQL for search and rating',
];

const STACK = [
  'React',
  'FastAPI',
  'PostgreSQL',
  'FLAN-T5',
  'Docker',
  'GitHub Actions',
  'AWS App Runner',
];

/** Shared split-screen shell for the login and register screens. */
export default function AuthLayout({ children }) {
  return (
    <div className="auth">
      <aside className="auth__aside">
        <div>
          <div className="brand" style={{ marginBottom: 44 }}>
            <span className="brand__mark">CM</span>
            <span className="brand__text">
              CloudMLOps
              <small>Document AI</small>
            </span>
          </div>
          <h1 className="auth__headline">Turn long documents into short answers.</h1>
          <p className="auth__lede">
            An AI summarization platform built on a three-tier architecture: a React interface, a
            FastAPI business tier running FLAN-T5, and a PostgreSQL data tier that keeps every
            summary searchable.
          </p>
          <div className="pipeline">
            {PIPELINE.map((step, index) => (
              <div className="pipeline__step" key={step}>
                <span>{index + 1}</span>
                {step}
              </div>
            ))}
          </div>
        </div>
        <div className="tech-list">
          {STACK.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </aside>

      <main className="auth__main">{children}</main>
    </div>
  );
}

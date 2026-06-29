// LangSwitcher.jsx — globe-glyph toggle with dropdown.

function LangSwitcher({ lang, onChange, languages = [['en','English'], ['sv','Svenska']] }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);

  React.useEffect(() => {
    function handle(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('click', handle);
    return () => document.removeEventListener('click', handle);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '6px 10px', borderRadius: 7,
          fontSize: '0.8rem', fontWeight: 600, fontFamily: 'inherit',
          cursor: 'pointer', border: 'none',
          background: open ? 'var(--surface-2)' : 'transparent',
          color: open ? 'var(--ink)' : 'var(--ink-soft)',
          transition: 'all 0.15s ease',
        }}
        aria-label="Change language"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.7 }}>
          <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/>
        </svg>
        {lang.toUpperCase()}
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', right: 0,
          background: '#fff', borderRadius: 9,
          boxShadow: '0 4px 20px oklch(0.14 0.015 240 / 0.14), 0 0 0 1px var(--ink-line)',
          overflow: 'hidden', minWidth: 140, zIndex: 200,
        }}>
          {languages.map(([code, label]) => (
            <button
              key={code}
              onClick={() => { onChange(code); setOpen(false); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 9,
                padding: '9px 14px', width: '100%',
                fontSize: '0.85rem', fontWeight: 600,
                cursor: 'pointer', border: 'none',
                background: 'transparent', fontFamily: 'inherit',
                color: code === lang ? 'var(--ink)' : 'var(--ink-soft)',
                textAlign: 'left',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span>{label}</span>
              <span style={{ marginLeft: 'auto', color: 'var(--brand-accent)', fontSize: '0.7rem', opacity: code === lang ? 1 : 0 }}>✓</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

window.LangSwitcher = LangSwitcher;

// EyebrowLabel + Pill + StatusBadge.

function EyebrowLabel({ children, color = 'var(--brand-primary)', center = false }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      justifyContent: center ? 'center' : undefined,
      fontSize: '0.78rem', fontWeight: 700,
      letterSpacing: '0.08em', textTransform: 'uppercase',
      color, marginBottom: 16,
    }}>
      <span style={{ display: 'block', width: 20, height: 2, background: color, borderRadius: 2 }} />
      {children}
    </div>
  );
}

function Pill({ children, dot = true }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      background: 'var(--brand-accent-tint)', color: 'var(--brand-accent)',
      fontSize: '0.78rem', fontWeight: 700,
      letterSpacing: '0.06em', textTransform: 'uppercase',
      padding: '5px 12px', borderRadius: 100,
    }}>
      {dot && <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--brand-accent)' }} />}
      {children}
    </span>
  );
}

function StatusBadge({ icon = '✓', children }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      background: '#fff', borderRadius: 12, padding: '10px 14px',
      boxShadow: 'var(--shadow-md)', fontSize: '0.8rem', fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      <span style={{
        width: 28, height: 28, borderRadius: 8,
        background: 'var(--brand-accent-tint)', color: 'var(--brand-accent)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>{icon}</span>
      {children}
    </span>
  );
}

window.EyebrowLabel = EyebrowLabel;
window.Pill = Pill;
window.StatusBadge = StatusBadge;

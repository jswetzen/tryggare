// ComparisonRow.jsx — ✓/✗ row used in the self-hosted pitch.

function ComparisonRow({ yes = true, title, sub }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14,
      background: '#fff', borderRadius: 10, padding: '14px 18px',
      boxShadow: 'var(--shadow-xs)',
    }}>
      <div style={{
        width: 26, height: 26, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '0.75rem', flexShrink: 0,
        background: yes ? 'var(--brand-accent-tint)' : 'var(--danger-tint)',
        color:      yes ? 'var(--brand-accent)'     : 'var(--danger)',
      }}>
        {yes ? '✓' : '✗'}
      </div>
      <div>
        <div style={{ fontSize: '0.875rem', fontWeight: 600, color: yes ? 'var(--ink)' : 'var(--ink-soft)' }}>{title}</div>
        <div style={{ fontSize: '0.78rem', color: 'var(--ink-faint)' }}>{sub}</div>
      </div>
    </div>
  );
}

window.ComparisonRow = ComparisonRow;

// FeatureCard.jsx — icon-tile, h3, body. Hover lifts 2px with soft shadow.

function FeatureCard({ icon, title, children, tone = 'blue' }) {
  const [hovered, setHovered] = React.useState(false);
  const tintBg = tone === 'green' ? 'var(--brand-accent-tint)' : 'var(--brand-primary-tint)';
  const iconColor = tone === 'green' ? 'var(--brand-accent)' : 'var(--brand-primary)';
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--ink-line)',
        borderRadius: 'var(--radius-lg)',
        padding: '28px 28px 24px',
        transition: 'box-shadow 0.2s ease, transform 0.2s ease',
        boxShadow: hovered ? 'var(--shadow-sm)' : 'none',
        transform: hovered ? 'translateY(-2px)' : 'none',
      }}
    >
      <div style={{
        width: 44, height: 44, borderRadius: 11,
        background: tintBg, color: iconColor,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 18,
      }}>
        {icon}
      </div>
      <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 7, letterSpacing: '-0.01em' }}>{title}</h3>
      <p style={{ fontSize: '0.875rem', color: 'var(--ink-soft)', lineHeight: 1.55 }}>{children}</p>
    </div>
  );
}

window.FeatureCard = FeatureCard;

// Button.jsx — five variants × two sizes. Matches production exactly.

const buttonBase = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 7,
  fontFamily: 'inherit',
  fontWeight: 600,
  textDecoration: 'none',
  cursor: 'pointer',
  border: 'none',
  transition: 'all 0.15s ease',
  whiteSpace: 'nowrap',
};
const buttonSizes = {
  md: { padding: '9px 18px', fontSize: '0.875rem', borderRadius: 8 },
  lg: { padding: '14px 28px', fontSize: '1rem',    borderRadius: 10 },
};
const buttonVariants = {
  primary: {
    background: 'var(--brand-primary)', color: '#fff',
    hover: { background: 'var(--brand-primary-mid)', transform: 'translateY(-1px)', boxShadow: 'var(--shadow-cta)' },
  },
  outline: {
    background: 'transparent', color: 'var(--brand-primary)',
    border: '1.5px solid oklch(0.80 0.08 232)',
    hover: { background: 'var(--brand-primary-tint)' },
  },
  ghost: {
    background: 'transparent', color: 'var(--ink-soft)',
    hover: { background: 'var(--surface-2)', color: 'var(--ink)' },
  },
  white: {
    background: '#fff', color: 'var(--ink)',
    hover: { background: 'var(--surface-2)', transform: 'translateY(-1px)' },
  },
  outlineWhite: {
    background: 'transparent', color: '#fff',
    border: '1.5px solid oklch(0.35 0.010 240)',
    hover: { background: 'oklch(0.20 0.010 240)' },
  },
};

function Button({ children, variant = 'primary', size = 'md', href, onClick, ...rest }) {
  const [hovered, setHovered] = React.useState(false);
  const v = buttonVariants[variant] || buttonVariants.primary;
  const style = {
    ...buttonBase,
    ...buttonSizes[size],
    ...v,
    ...(hovered ? v.hover : {}),
  };
  delete style.hover;
  const Tag = href ? 'a' : 'button';
  return (
    <Tag
      href={href}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={style}
      target={href && href.startsWith('http') ? '_blank' : undefined}
      rel={href && href.startsWith('http') ? 'noopener' : undefined}
      {...rest}
    >
      {children}
    </Tag>
  );
}

// GitHub mark — the one filled icon allowed in the design.
function GitHubMark({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/>
    </svg>
  );
}

window.Button = Button;
window.GitHubMark = GitHubMark;

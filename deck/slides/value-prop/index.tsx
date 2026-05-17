import type { DesignSystem, Page, SlideMeta } from '@open-slide/core';

export const design: DesignSystem = {
  palette: { bg: '#0a0e17', text: '#e8edf5', accent: '#22c55e' },
  fonts: {
    display: 'system-ui, -apple-system, sans-serif',
    body: 'system-ui, -apple-system, sans-serif',
  },
  typeScale: { hero: 120, body: 28 },
  radius: 12,
};

const muted = '#64748b';
const green = '#22c55e';
const fill = { width: '100%', height: '100%', fontFamily: 'var(--osd-font-body)' } as const;

const Title: Page = () => (
  <div
    style={{
      ...fill,
      background: 'var(--osd-bg)',
      color: 'var(--osd-text)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      padding: '0 120px',
      position: 'relative',
      overflow: 'hidden',
    }}
  >
    {/* Decorative accent bar */}
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: 8,
        height: '100%',
        background: `linear-gradient(180deg, ${green}, #06b6d4)`,
      }}
    />
    <div style={{ fontSize: 22, color: green, letterSpacing: '0.15em', marginBottom: 16 }}>
      MICHA STOCKS
    </div>
    <h1
      style={{
        fontFamily: 'var(--osd-font-display)',
        fontSize: 'var(--osd-size-hero)',
        fontWeight: 900,
        margin: 0,
        lineHeight: 1.05,
      }}
    >
      Learn to Trade
    </h1>
    <h1
      style={{
        fontFamily: 'var(--osd-font-display)',
        fontSize: 'var(--osd-size-hero)',
        fontWeight: 900,
        margin: 0,
        lineHeight: 1.05,
        color: green,
      }}
    >
      Like Micha
    </h1>
    <p
      style={{
        fontSize: 'var(--osd-size-body)',
        color: muted,
        maxWidth: 900,
        marginTop: 32,
        lineHeight: 1.5,
      }}
    >
      An AI-powered decision tool that applies Micha's reasoning framework
      to help you make smarter stock decisions — backed by 20 sourced patterns
      and live market data.
    </p>
    <div style={{ display: 'flex', gap: 20, marginTop: 40 }}>
      {['20 Trading Patterns', '1,400+ Transcripts', 'Live Market Data', 'AI Reasoning'].map(
        (label, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 20px',
              background: 'rgba(34,197,94,0.08)',
              borderRadius: 8,
              border: '1px solid rgba(34,197,94,0.2)',
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: green,
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: 20, color: '#94a3b8' }}>{label}</span>
          </div>
        )
      )}
    </div>
  </div>
);

// ─── Value Proposition ─────────────────────────────────────────────────────────

const ValueProp: Page = () => {
  const items = [
    {
      icon: '🎯',
      label: 'Pattern-Based Reasoning',
      desc: 'Every recommendation is grounded in one of 20 verified trading patterns extracted from Micha\'s actual YouTube content.',
    },
    {
      icon: '🔗',
      label: 'Source-Verified',
      desc: 'Each pattern links to a specific video + chunk — you can verify the source with one click.',
    },
    {
      icon: '📊',
      label: 'Live Market Context',
      desc: 'Real-time yfinance data (price, PE, volume, range) feeds the analysis alongside Micha\'s logic.',
    },
    {
      icon: '🧠',
      label: 'AI-Powered Reasoning',
      desc: 'DeepSeek v4 Pro applies Micha\'s patterns to your specific situation — not generic advice.',
    },
    {
      icon: '🔍',
      label: 'Semantic + Keyword Search',
      desc: 'Find the right pattern even if you use different words. Hebrew and English queries both work.',
    },
    {
      icon: '📋',
      label: 'Audit Trail',
      desc: 'Every recommendation is logged with patterns used, market data, and AI output — full traceability.',
    },
  ];

  return (
    <div
      style={{
        ...fill,
        background: 'var(--osd-bg)',
        color: 'var(--osd-text)',
        padding: 80,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ fontSize: 22, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>
        WHY THIS EXISTS
      </div>
      <h2
        style={{
          fontFamily: 'var(--osd-font-display)',
          fontSize: 60,
          fontWeight: 800,
          margin: 0,
          lineHeight: 1.1,
        }}
      >
        From Videos to Decisions
      </h2>
      <p style={{ fontSize: 26, color: muted, marginTop: 12, maxWidth: 1400, lineHeight: 1.4 }}>
        Micha has 2,500+ videos. No one can watch them all before making a trade.
        This tool extracts the reasoning patterns and applies them to your situation in seconds.
      </p>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 24,
          marginTop: 32,
        }}
      >
        {items.map((item, i) => (
          <div
            key={i}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 12,
              padding: '24px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ fontSize: 32 }}>{item.icon}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--osd-text)' }}>
              {item.label}
            </div>
            <div style={{ fontSize: 18, color: muted, lineHeight: 1.4 }}>{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const meta: SlideMeta = { title: 'Value Proposition' };
export default [Title, ValueProp] satisfies Page[];

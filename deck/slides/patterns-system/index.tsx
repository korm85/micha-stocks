import type { DesignSystem, Page, SlideMeta } from '@open-slide/core';

export const design: DesignSystem = {
  palette: { bg: '#0a0e17', text: '#e8edf5', accent: '#22c55e' },
  fonts: {
    display: 'system-ui, -apple-system, sans-serif',
    body: 'system-ui, -apple-system, sans-serif',
  },
  typeScale: { hero: 100, body: 26 },
  radius: 12,
};

const muted = '#64748b';
const green = '#22c55e';
const fill = { width: '100%', height: '100%', fontFamily: 'var(--osd-font-body)' } as const;

// ─── Pattern System Overview ────────────────────────────────────────────────────

const PatternOverview: Page = () => {
  const origPatterns = [
    { name: 'trade_with_trend', desc: 'Trend is your friend' },
    { name: 'entry_timing_dip', desc: '4 rules for buying dips' },
    { name: 'exit_strategy_stop_loss', desc: '25% max loss, thesis-based exits' },
    { name: 'sell_in_may', desc: 'Reduce size, don\'t blindly sell' },
    { name: 'earnings_analysis', desc: 'No such thing as good earnings' },
    { name: 'market_breadth', desc: 'Breadth divergence warnings' },
    { name: 'overtrading', desc: '72% of traders lose this way' },
    { name: 'sector_rotation', desc: 'Tracking the great rotation' },
    { name: 'position_sizing', desc: 'Core 5-7%, max 10% per position' },
    { name: 'compounding_math', desc: 'Time in market beats timing' },
    { name: 'fear_greed_index', desc: 'Be greedy when others are fearful' },
    { name: 'simple_chart_reading', desc: 'Price + volume + trend + MAs' },
  ];

  const newPatterns = [
    { name: 'fed_rate_impact', desc: 'Fed pivot signals flip markets in 72h' },
    { name: 'crypto_market_cycle', desc: 'Bitcoin 4-year cycle + institutional adoption' },
    { name: 'support_resistance_trading', desc: 'Role reversal: broken support = resistance' },
    { name: 'taking_profits_strategy', desc: 'Trailing stop vs fixed target' },
    { name: 'dollar_cost_averaging', desc: 'Fixed monthly investment, no timing risk' },
    { name: 'trading_psychology_fear', desc: 'Fear as contrarian indicator' },
    { name: 'market_cycle_positioning', desc: 'Late cycle is always scary — don\'t panic' },
    { name: 'cash_position_strategy', desc: 'Cash is a position, not wasted capital' },
  ];

  return (
    <div
      style={{
        ...fill,
        background: 'var(--osd-bg)',
        color: 'var(--osd-text)',
        padding: 100,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ fontSize: 24, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>
        KNOWLEDGE BASE
      </div>
      <h2
        style={{
          fontFamily: 'var(--osd-font-display)',
          fontSize: 64,
          fontWeight: 800,
          margin: 0,
          lineHeight: 1.1,
        }}
      >
        20 Trading Patterns
      </h2>
      <p style={{ fontSize: 28, color: muted, marginTop: 8, maxWidth: 1400, lineHeight: 1.4 }}>
        Each pattern is source-linked to a real Micha video with chunk ID and video ID.
        All Arabic/English terms work via multilingual embeddings.
      </p>

      <div style={{ display: 'flex', gap: 32, marginTop: 24, flex: 1, minHeight: 0 }}>
        {/* Original 12 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: green, marginBottom: 12 }}>
            Original — 12 Patterns
          </div>
          <div
            style={{
              flex: 1,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}
          >
            {origPatterns.map((p, i) => (
              <div
                key={i}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 8,
                  padding: '8px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ fontSize: 18, fontWeight: 600 }}>{p.name.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: 16, color: muted }}>{p.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* New 8 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#06b6d4', marginBottom: 12 }}>
            New — 8 Patterns
          </div>
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}
          >
            {newPatterns.map((p, i) => (
              <div
                key={i}
                style={{
                  background: 'rgba(6,182,212,0.05)',
                  border: '1px solid rgba(6,182,212,0.2)',
                  borderRadius: 8,
                  padding: '8px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ fontSize: 18, fontWeight: 600 }}>{p.name.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: 16, color: muted }}>{p.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Score confidence legend */}
      <div
        style={{
          display: 'flex',
          gap: 24,
          marginTop: 16,
          padding: '12px 20px',
          background: 'rgba(255,255,255,0.02)',
          borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <span style={{ fontSize: 18, color: muted }}>Confidence indicator:</span>
        <ScoreDot label="≥ 0.85 High" color={green} />
        <ScoreDot label="≥ 0.80 Good" color="#a3e635" />
        <ScoreDot label="≥ 0.78 Moderate" color="#f59e0b" />
        <ScoreDot label="< 0.78 Low" color="#ef4444" />
      </div>
    </div>
  );
};

const ScoreDot = ({ label, color }: { label: string; color: string }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
    <span style={{ fontSize: 17, color: muted }}>{label}</span>
  </div>
);

// ─── Dashboard Walkthrough ──────────────────────────────────────────────────────

const DashboardUI: Page = () => (
  <div
    style={{
      ...fill,
      background: 'var(--osd-bg)',
      color: 'var(--osd-text)',
      padding: 100,
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div style={{ fontSize: 24, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>
      USER EXPERIENCE
    </div>
    <h2
      style={{
        fontFamily: 'var(--osd-font-display)',
        fontSize: 64,
        fontWeight: 800,
        margin: 0,
        lineHeight: 1.1,
      }}
    >
      Dashboard Walkthrough
    </h2>

    <div style={{ display: 'flex', gap: 32, marginTop: 28, flex: 1 }}>
      {/* Left: steps */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <StepCard
          num="1"
          title="Ask a Question"
          desc={'Type "Should I buy NVDA?" or "My portfolio is down 10%" — natural language works.'}
        />
        <StepCard
          num="2"
          title="Ticker Detection"
          desc="Regex extracts ticker (NVDA, AAPL, TSLA) → yfinance fetches live price, PE, volume, 52-week range."
        />
        <StepCard
          num="3"
          title="KB Search"
          desc="Semantic search ranks 20 patterns + 17K chunks. Fallbacks: FTS keyword → all patterns."
        />
        <StepCard
          num="4"
          title="AI Reasoning"
          desc="DeepSeek v4 Pro analyzes market data + patterns to produce a structured recommendation."
        />
        <StepCard
          num="5"
          title="Audit & Citation"
          desc="Every recommendation logged. Sources shown as clickable YouTube links with chunk IDs."
        />
      </div>

      {/* Right: key features */}
      <div
        style={{
          flex: 1,
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: 12,
          padding: '28px 32px',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div style={{ fontSize: 24, fontWeight: 700 }}>Key Features</div>
        <FeatureRow icon="📈" text="Live market data via yfinance" />
        <FeatureRow icon="🧠" text="DeepSeek v4 Pro reasoning with pattern citations" />
        <FeatureRow icon="🎯" text="Semantic match badges (score: 0.857)" />
        <FeatureRow icon="🔗" text="Clickable YouTube source links per pattern" />
        <FeatureRow icon="📋" text="Full audit trail (recommendation_audit table)" />
        <FeatureRow icon="🔍" text="Keyword + semantic + fallback search layers" />
        <FeatureRow icon="⚠️" text="Confidence guardrails + regulatory disclaimer" />
        <FeatureRow icon="🌐" text="Hebrew + English queries (multilingual model)" />

        <div
          style={{
            marginTop: 'auto',
            padding: '16px 20px',
            background: 'rgba(34,197,94,0.06)',
            border: '1px solid rgba(34,197,94,0.2)',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 22, fontWeight: 700, color: green }}>📊 Quick Access</div>
          <div style={{ fontSize: 18, color: muted, marginTop: 4 }}>
            🌐 <a href="https://nuc-server.tail8cfaa2.ts.net" style={{ color: green, textDecoration: 'underline' }} target="_blank">Dashboard</a>
            {' · '}
            <a href="https://nuc-server.tail8cfaa2.ts.net/db/" style={{ color: '#06b6d4', textDecoration: 'underline' }} target="_blank">Database Browser</a>
            {' · '}
            <span style={{ color: '#64748b' }}>Tailscale Funnel</span>
          </div>
        </div>
      </div>
    </div>
  </div>
);

const StepCard = ({
  num,
  title,
  desc,
}: {
  num: string;
  title: string;
  desc: string;
}) => (
  <div
    style={{
      display: 'flex',
      gap: 16,
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 10,
      padding: '14px 20px',
      alignItems: 'flex-start',
    }}
  >
    <div
      style={{
        width: 32,
        height: 32,
        borderRadius: '50%',
        background: green,
        color: '#0a0e17',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 16,
        fontWeight: 800,
        flexShrink: 0,
        marginTop: 2,
      }}
    >
      {num}
    </div>
    <div>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{title}</div>
      <div style={{ fontSize: 20, color: muted, lineHeight: 1.4, marginTop: 2 }}>{desc}</div>
    </div>
  </div>
);

const FeatureRow = ({ icon, text }: { icon: string; text: string }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
    <span style={{ fontSize: 24 }}>{icon}</span>
    <span style={{ fontSize: 22, color: muted }}>{text}</span>
  </div>
);

export const meta: SlideMeta = { title: 'Patterns & Dashboard' };
export default [PatternOverview, DashboardUI] satisfies Page[];

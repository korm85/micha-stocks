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

// ─── Search Pipeline ───────────────────────────────────────────────────────────

const SearchPipeline: Page = () => {
  const steps = [
    {
      label: 'User Query',
      desc: '"My stock dropped 15%, should I sell it?"',
      arrow: true,
    },
    {
      label: 'Step 1: Semantic Pattern Search',
      desc: 'Embed query (384-dim) → cosine similarity with 20 pattern vectors → return all ranked by score.',
      score: 'Top-1: 75% | Top-5: 90%',
      arrow: true,
    },
    {
      label: 'Step 2: Semantic Chunk Search',
      desc: 'Same embed → compare with 17,286 chunk vectors → return chunks above 0.84 confidence gate.',
      score: 'Gate 0.84: ~8 chunks/query',
      arrow: true,
    },
    {
      label: 'Step 3: FTS Keyword Fallback',
      desc: 'SQLite FTS5 exact keyword matching on patterns + chunks. Used when semantic returns nothing.',
      score: 'Always available',
      arrow: true,
    },
    {
      label: 'Step 4: All Patterns Fallback',
      desc: 'Return all 20 patterns unranked. Guarantees the dashboard always shows something.',
      score: 'Last resort',
      arrow: false,
    },
  ];

  return (
    <div
      style={{
        ...fill,
        background: 'var(--osd-bg)',
        color: 'var(--osd-text)',
        padding: '40px 80px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ fontSize: 18, color: green, letterSpacing: '0.15em', marginBottom: 4 }}>
        SEARCH
      </div>
      <h2
        style={{
          fontFamily: 'var(--osd-font-display)',
          fontSize: 44,
          fontWeight: 800,
          margin: 0,
          lineHeight: 1.1,
        }}
      >
        Search Pipeline
      </h2>
      <p style={{ fontSize: 20, color: muted, marginTop: 4, maxWidth: 1200, lineHeight: 1.3 }}>
        Four-tier search strategy ensures the dashboard always returns relevant results,
        from most precise to broad fallback.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginTop: 12, flex: 1 }}>
        {steps.map((step, i) => (
          <div key={i}>
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 16,
                background: i === 0 ? 'rgba(34,197,94,0.06)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${i === 0 ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.06)'}`,
                borderRadius: 10,
                padding: '12px 20px',
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: i === 0 ? green : muted,
                  color: '#0a0e17',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 14,
                  fontWeight: 800,
                  flexShrink: 0,
                  marginTop: 2,
                }}
              >
                {i + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{step.label}</div>
                <div style={{ fontSize: 17, color: muted, lineHeight: 1.4, marginTop: 3 }}>
                  {step.desc}
                </div>
                {step.score && (
                  <div
                    style={{
                      fontSize: 16,
                      color: green,
                      marginTop: 4,
                      padding: '2px 12px',
                      background: 'rgba(34,197,94,0.08)',
                      borderRadius: 4,
                      display: 'inline-block',
                    }}
                  >
                    {step.score}
                  </div>
                )}
              </div>
            </div>
            {step.arrow && <div style={{ textAlign: 'center', padding: '3px 0', color: muted, fontSize: 16 }}>↓</div>}
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Confidence Calibration ────────────────────────────────────────────────────

const Calibration: Page = () => (
  <div
    style={{
      ...fill,
      background: 'var(--osd-bg)',
      color: 'var(--osd-text)',
      padding: '40px 80px',
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div style={{ fontSize: 18, color: green, letterSpacing: '0.15em', marginBottom: 4 }}>
      CALIBRATION
    </div>
    <h2
      style={{
        fontFamily: 'var(--osd-font-display)',
        fontSize: 44,
        fontWeight: 800,
        margin: 0,
        lineHeight: 1.1,
      }}
    >
      Confidence Gate: 0.84
    </h2>
    <p style={{ fontSize: 20, color: muted, marginTop: 4, maxWidth: 1200, lineHeight: 1.4 }}>
      Tested against 20 calibration queries with known ground-truth patterns.
      The gate balances precision vs recall.
    </p>

    {/* Gate comparison */}
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24, marginTop: 20 }}>
      <GateCard
        gate="0.82"
        verdict="Too loose"
        desc="19/20 queries return results but avg 171 chunks — too noisy"
        color="#f59e0b"
      />
      <GateCard
        gate="0.84"
        verdict="Sweet spot"
        desc="14/20 queries return results, avg 8 chunks — clean signal"
        color={green}
      />
      <GateCard
        gate="0.86"
        verdict="Too strict"
        desc="Only 9/20 queries return results, avg 0.7 chunks — misses too much"
        color="#ef4444"
      />
    </div>

    {/* Pattern accuracy */}
    <div style={{ marginTop: 20 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 10 }}>Pattern Search Accuracy</div>
      <div style={{ display: 'flex', gap: 32 }}>
        <MetricBox label="Top-1" value="75%" desc="Correct pattern ranked #1" />
        <MetricBox label="Top-3" value="90%" desc="Correct pattern in top 3" />
        <MetricBox label="Top-5" value="90%" desc="Correct pattern in top 5" />
        <MetricBox label="Backtest" value="100%" desc="10/10 historical scenarios" />
      </div>
    </div>
  </div>
);

const GateCard = ({
  gate,
  verdict,
  desc,
  color,
}: {
  gate: string;
  verdict: string;
  desc: string;
  color: string;
}) => (
  <div
    style={{
      background: 'rgba(255,255,255,0.03)',
      border: `1px solid ${color}44`,
      borderRadius: 12,
      padding: '20px 16px',
      textAlign: 'center',
    }}
  >
    <div style={{ fontSize: 36, fontWeight: 900, color, lineHeight: 1 }}>{gate}</div>
    <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6 }}>{verdict}</div>
    <div style={{ fontSize: 16, color: muted, marginTop: 6, lineHeight: 1.4 }}>{desc}</div>
  </div>
);

const MetricBox = ({
  label,
  value,
  desc,
}: {
  label: string;
  value: string;
  desc: string;
}) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{ fontSize: 40, fontWeight: 900, color: green, lineHeight: 1 }}>{value}</div>
    <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{label}</div>
    <div style={{ fontSize: 16, color: muted, marginTop: 2 }}>{desc}</div>
  </div>
);

export const meta: SlideMeta = { title: 'Search & Calibration' };
export default [SearchPipeline, Calibration] satisfies Page[];

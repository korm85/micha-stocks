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
const accent2 = '#06b6d4';
const fill = { width: '100%', height: '100%', fontFamily: 'var(--osd-font-body)' } as const;

// ─── Architecture Overview ─────────────────────────────────────────────────────

const Overview: Page = () => (
  <div
    style={{
      ...fill,
      background: 'var(--osd-bg)',
      color: 'var(--osd-text)',
      padding: '60px 80px',
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div style={{ fontSize: 20, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>
      SYSTEM DESIGN
    </div>
    <h2
      style={{
        fontFamily: 'var(--osd-font-display)',
        fontSize: 48,
        fontWeight: 800,
        margin: 0,
        lineHeight: 1.1,
      }}
    >
      Architecture Overview
    </h2>
    <p style={{ fontSize: 22, color: muted, marginTop: 8, maxWidth: 1200, lineHeight: 1.4 }}>
      Four layers that turn raw YouTube content into actionable stock recommendations.
    </p>

    {/* Layer cards */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 24, flex: 1 }}>
      <LayerCard
        num="1"
        title="Data Ingestion"
        desc="Scraper downloads transcripts from all 2,502 YouTube videos. 1,395 have auto-captions → 17,286 chunks stored in SQLite with FTS5 index."
        color={green}
      />
      <LayerCard
        num="2"
        title="Embedding Pipeline"
        desc="Multilingual-e5-small model generates 384-dim vectors for every chunk (132MB) and each pattern. Node.js runtime via @xenova/transformers."
        color={accent2}
      />
      <LayerCard
        num="3"
        title="Search Engine"
        desc="Two-tier: semantic (cosine similarity over vectors) as primary, FTS5 keyword as fallback. Calibrated confidence gate of 0.84 for chunk results."
        color="#a78bfa"
      />
      <LayerCard
        num="4"
        title="Application Layer"
        desc="Streamlit dashboard on port 8501. yfinance for live market data. DeepSeek v4 Pro for AI reasoning. All recommendations logged to audit trail."
        color="#f59e0b"
      />
    </div>
  </div>
);

const LayerCard = ({
  num,
  title,
  desc,
  color,
}: {
  num: string;
  title: string;
  desc: string;
  color: string;
}) => (
  <div
    style={{
      display: 'flex',
      gap: 16,
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 12,
      padding: '16px 24px',
      alignItems: 'flex-start',
    }}
  >
    <div
      style={{
        width: 36,
        height: 36,
        borderRadius: '50%',
        background: color,
        color: '#0a0e17',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 18,
        fontWeight: 800,
        flexShrink: 0,
      }}
    >
      {num}
    </div>
    <div>
      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--osd-text)' }}>{title}</div>
      <div style={{ fontSize: 20, color: muted, lineHeight: 1.4, marginTop: 4 }}>{desc}</div>
    </div>
  </div>
);

// ─── Data Flow ──────────────────────────────────────────────────────────────────

const DataFlow: Page = () => (
  <div
    style={{
      ...fill,
      background: 'var(--osd-bg)',
      color: 'var(--osd-text)',
      padding: '60px 80px',
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div style={{ fontSize: 20, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>
      PIPELINE
    </div>
    <h2
      style={{
        fontFamily: 'var(--osd-font-display)',
        fontSize: 48,
        fontWeight: 800,
        margin: 0,
        lineHeight: 1.1,
      }}
    >
      Data Flow
    </h2>

    {/* Flow diagram */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginTop: 24 }}>
      <FlowBox label="YouTube" desc="@micha.stocks 2,502 videos" color={green} />
      <ArrowDown />
      <FlowBox label="Scraper" desc="youtube-transcript-api + rate limiting" color={green} />
      <ArrowDown />
      <SplitRow
        left={<FlowBox label="SQLite DB" desc="videos + chunks + patterns + FTS5" color={accent2} />}
        right={<FlowBox label="Embeddings" desc="multilingual-e5-small 384-dim" color={accent2} />}
      />
      <ArrowDown />
      <FlowBox label="Search Engine" desc="cosine similarity + FTS5 keyword fallback" color="#a78bfa" />
      <ArrowDown />
      <FlowBox label="Streamlit Dashboard" desc="semantic patterns + chunks + market data → DeepSeek → recommendation" color="#f59e0b" />
    </div>
  </div>
);

const FlowBox = ({
  label,
  desc,
  color,
}: {
  label: string;
  desc: string;
  color: string;
}) => (
  <div
    style={{
      background: 'rgba(255,255,255,0.03)',
      border: `1px solid ${color}44`,
      borderRadius: 12,
      padding: '12px 24px',
      textAlign: 'center',
    }}
  >
    <div style={{ fontSize: 24, fontWeight: 700, color }}>{label}</div>
    <div style={{ fontSize: 18, color: muted, marginTop: 2 }}>{desc}</div>
  </div>
);

const ArrowDown = () => (
  <div style={{ textAlign: 'center', padding: '4px 0', color: muted, fontSize: 20 }}>
    ↓
  </div>
);

const SplitRow = ({
  left,
  right,
}: {
  left: JSX.Element;
  right: JSX.Element;
}) => (
  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
    {left}
    {right}
  </div>
);

export const meta: SlideMeta = { title: 'Architecture' };
export default [Overview, DataFlow] satisfies Page[];

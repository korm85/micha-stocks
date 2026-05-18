import type { DesignSystem, Page, SlideMeta } from '@open-slide/core';

export const design: DesignSystem = {
  palette: { bg: '#0a0e17', text: '#e8edf5', accent: '#f59e0b' },
  fonts: {
    display: 'system-ui, -apple-system, sans-serif',
    body: 'system-ui, -apple-system, sans-serif',
  },
  typeScale: { hero: 120, body: 28 },
  radius: 12,
};

const muted = '#64748b';
const amber = '#f59e0b';
const green = '#22c55e';
const red = '#ef4444';
const blue = '#3b82f6';
const violet = '#a78bfa';
const teal = '#22d3ee';

const fill = { width: '100%', height: '100%', fontFamily: 'var(--osd-font-body)' } as const;

const styles = `
  @keyframes jl-fadeUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes jl-fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes jl-scaleIn {
    from { opacity: 0; transform: scale(.96); }
    to   { opacity: 1; transform: scale(1); }
  }
  @keyframes jl-slideRight {
    from { opacity: 0; transform: translateX(-30px); }
    to   { opacity: 1; transform: translateX(0); }
  }
  @keyframes jl-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(245,158,11,0); }
    50%      { box-shadow: 0 0 0 12px rgba(245,158,11,0.15); }
  }
  @keyframes jl-shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  .jl-fu { opacity: 0; animation: jl-fadeUp 0.7s cubic-bezier(.2,.7,.2,1) forwards; }
  .jl-fi { opacity: 0; animation: jl-fadeIn 0.9s ease forwards; }
  .jl-si { opacity: 0; animation: jl-scaleIn 0.6s cubic-bezier(.2,.7,.2,1) forwards; }
  .jl-sr { opacity: 0; animation: jl-slideRight 0.6s cubic-bezier(.2,.7,.2,1) forwards; }
  .jl-pulse { animation: jl-pulse 2s ease-in-out infinite; }
`;

const Styles = () => <style>{styles}</style>;
const Box = ({ children, delay = 0, style }: any) => (
  <div
    className="jl-si"
    style={{
      animationDelay: `${delay}s`,
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 12,
      padding: '20px 24px',
      ...style,
    }}
  >
    {children}
  </div>
);
const Tag = ({ color = amber, children }: any) => (
  <span
    style={{
      fontFamily: '"JetBrains Mono", monospace',
      fontSize: 20,
      color,
      background: `${color}14`,
      border: `1px solid ${color}30`,
      padding: '2px 10px',
      borderRadius: 6,
    }}
  >
    {children}
  </span>
);

// ─── Slide 1: Cover ──────────────────────────────────────────────────────────
const Cover: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
    <Styles />
    {/* Grid bg */}
    <div style={{
      position: 'absolute', inset: 0,
      backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
      backgroundSize: '80px 80px',
    }} />
    <div style={{ position: 'relative', textAlign: 'center', padding: '0 120px' }}>
      <div className="jl-fu" style={{ fontSize: 22, color: amber, letterSpacing: '0.18em', marginBottom: 20 }}>MICHA STOCKS</div>
      <h1 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 'var(--osd-size-hero)', fontWeight: 900, margin: 0, lineHeight: 1.03, animationDelay: '0.1s' }}>
        Journey Log
      </h1>
      <h1 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 'var(--osd-size-hero)', fontWeight: 900, margin: 0, lineHeight: 1.03, color: amber, animationDelay: '0.2s' }}>
        How Agents Work
      </h1>
      <p className="jl-fu" style={{ fontSize: 'var(--osd-size-body)', color: muted, maxWidth: 1100, margin: '32px auto 0', lineHeight: 1.4, animationDelay: '0.35s' }}>
        A visual guide to the traceability system — how every agent action is logged,
        how handoffs work, and how to spot bad workflows at a glance.
      </p>
      <div className="jl-fu" style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 48, animationDelay: '0.5s' }}>
        {['traceable', 'readable', 'optimizable'].map(t => (
          <span key={t} style={{ padding: '8px 20px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.08)', fontSize: 18, color: muted }}>
            {t}
          </span>
        ))}
      </div>
    </div>
  </div>
);

// ─── Slide 2: The Problem ────────────────────────────────────────────────────
const Problem: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: red, letterSpacing: '0.15em', marginBottom: 8 }}>THE PROBLEM</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      Agents Work in the Dark
    </h2>
    <p className="jl-fu" style={{ fontSize: 26, color: muted, maxWidth: 1400, marginTop: 16, lineHeight: 1.4, animationDelay: '0.2s' }}>
      When multiple AI agents touch the same repo, you lose the plot.
    </p>
    <div style={{ display: 'flex', gap: 24, marginTop: 36 }}>
      {[
        { icon: '👁️', title: 'No Visibility', desc: 'What did the last agent do? What decisions were made? You have to read git blame and guess.', color: red },
        { icon: '🤝', title: 'No Handoff', desc: 'Agent A finishes. Agent B starts from zero. Context is lost. Rework happens.', color: amber },
        { icon: '🔄', title: 'Invisible Bad Flows', desc: 'Tasks that ping-pong between agents, rework, confusion — you never see the pattern.', color: violet },
      ].map((item, i) => (
        <div key={i} className="jl-si" style={{ animationDelay: `${0.3 + i * 0.12}s`, flex: 1, background: 'rgba(255,255,255,0.02)', border: `1px solid rgba(255,255,255,0.06)`, borderRadius: 12, padding: '28px 24px' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>{item.icon}</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: item.color }}>{item.title}</div>
          <div style={{ fontSize: 18, color: muted, marginTop: 8, lineHeight: 1.45 }}>{item.desc}</div>
        </div>
      ))}
    </div>
  </div>
);

// ─── Slide 3: The Solution ───────────────────────────────────────────────────
const Solution: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>THE SOLUTION</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      One File. Append-Only.
    </h2>
    <p className="jl-fu" style={{ fontSize: 26, color: muted, maxWidth: 1400, marginTop: 16, lineHeight: 1.4, animationDelay: '0.2s' }}>
      <strong style={{ color: amber }}>JOURNEY.md</strong> sits at the repo root. Every agent writes here as they work.
    </p>
    <div style={{ display: 'flex', gap: 40, marginTop: 40, alignItems: 'center' }}>
      <div className="jl-si" style={{ animationDelay: '0.3s', flex: 1.3, fontFamily: '"JetBrains Mono", monospace', background: '#0f1219', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, padding: '24px 28px', fontSize: 16, lineHeight: 1.7 }}>
        <div style={{ color: muted, marginBottom: 12 }}># 🗺️ Journey Log — micha-stocks</div>
        <div style={{ color: '#94a3b8' }}>A timeline of every agent action on this repo.<br />Open this file to see how work flows.</div>
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '16px 0', paddingTop: 16 }}>
          <div style={{ color: green }}>## #001 🟢 START — 2026-05-14 13:00 UTC</div>
          <div style={{ color: muted }}>  Task: Create journey log system</div>
          <div style={{ color: '#64748b', marginLeft: 20 }}>• Design logging format → JOURNEY.md</div>
          <div style={{ color: '#64748b', marginLeft: 20 }}>• Flow tags reveal bad workflows</div>
          <div style={{ color: '#64748b', marginLeft: 20 }}>• Handoff entries carry state between agents</div>
        </div>
        <div style={{ color: '#94a3b8', fontSize: 14 }}>... scrolls on as work happens ...</div>
      </div>
      <div className="jl-si" style={{ animationDelay: '0.45s', flex: 0.9, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px', background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)', borderRadius: 10 }}>
          <span style={{ fontSize: 24 }}>✅</span>
          <div><div style={{ fontSize: 18, fontWeight: 600, color: green }}>Append-Only</div><div style={{ fontSize: 14, color: muted }}>Never edit old entries</div></div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px', background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)', borderRadius: 10 }}>
          <span style={{ fontSize: 24 }}>📖</span>
          <div><div style={{ fontSize: 18, fontWeight: 600, color: blue }}>Self-Teaching</div><div style={{ fontSize: 14, color: muted }}>Header has the full legend</div></div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: 10 }}>
          <span style={{ fontSize: 24 }}>📊</span>
          <div><div style={{ fontSize: 18, fontWeight: 600, color: amber }}>Reveals Bad Flows</div><div style={{ fontSize: 14, color: muted }}>Rework, bounces, confusion are tagged</div></div>
        </div>
      </div>
    </div>
  </div>
);

// ─── Slide 4: Reading the Log ───────────────────────────────────────────────
const ReadingTheLog: Page = () => {
  const parts = [
    { label: '#042', desc: 'Entry number (sequential)', color: violet },
    { label: '🟢', desc: 'Phase emoji — tells you what kind of step', color: green },
    { label: 'START', desc: 'Phase name — matches the emoji', color: green },
    { label: '2026-05-14 14:30 UTC', desc: 'When it happened', color: muted },
    { label: '`smooth`', desc: 'Flow tag — how well the step went', color: amber },
  ];
  return (
    <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div className="jl-sr" style={{ fontSize: 22, color: teal, letterSpacing: '0.15em', marginBottom: 8 }}>HOW TO READ IT</div>
      <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
        Anatomy of an Entry
      </h2>
      <p className="jl-fu" style={{ fontSize: 24, color: muted, marginTop: 12, animationDelay: '0.15s' }}>
        One entry tells you everything about one step.
      </p>
      <div style={{ display: 'flex', gap: 32, marginTop: 32, alignItems: 'flex-start' }}>
        {/* Annotated entry */}
        <div className="jl-si" style={{ animationDelay: '0.25s', flex: 1.3, fontFamily: '"JetBrains Mono", monospace', background: '#0f1219', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, padding: '28px 32px', fontSize: 18, lineHeight: 2 }}>
          <div style={{ color: green }}>## <span style={{ background: '#a78bfa22', padding: '0 4px', borderRadius: 3 }}>#042</span> <span style={{ background: '#22c55e22', padding: '0 4px', borderRadius: 3 }}>🟢</span> <span style={{ background: '#22c55e22', padding: '0 4px', borderRadius: 3 }}>START</span> — <span style={{ background: '#64748b22', padding: '0 4px', borderRadius: 3 }}>2026-05-14 14:30 UTC</span></div>
          <div style={{ color: amber }}>  **Agent:** Hermes Agent · **Flow:** `<span style={{ background: '#f59e0b22', padding: '0 4px', borderRadius: 3 }}>smooth</span>`</div>
          <div style={{ color: '#94a3b8' }}>  **Task:** Add audit trail visualization</div>
          <div style={{ color: '#64748b', marginLeft: 20 }}>  • Created render_audit_trail() → app.py</div>
          <div style={{ color: '#64748b', marginLeft: 20 }}>  • Shows last 20 entries with timestamps</div>
        </div>
        {/* Labels */}
        <div className="jl-si" style={{ animationDelay: '0.4s', flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {parts.map((p, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: 8 }}>
              <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 14, color: p.color, padding: '2px 8px', background: `${p.color}18`, borderRadius: 4 }}>{p.label}</div>
              <div style={{ fontSize: 16, color: muted }}>{p.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ─── Slide 5: Phases at a Glance ─────────────────────────────────────────────
const Phases: Page = () => {
  const phases = [
    { emoji: '🟢', name: 'START', desc: 'New task begins', detail: 'Goal, scope, approach declared upfront', color: green },
    { emoji: '⚡', name: 'EXECUTE', desc: 'Work in progress', detail: 'Files changed, decisions made', color: blue },
    { emoji: '🔄', name: 'HANDOFF', desc: 'Passed to another agent', detail: 'Current state + explicit next steps', color: teal },
    { emoji: '🔴', name: 'BLOCKED', desc: 'Hit a blocker', detail: 'What went wrong + how it was resolved', color: red },
    { emoji: '✅', name: 'DONE', desc: 'Task completed', detail: 'Summary + verification taken', color: green },
    { emoji: '♻️', name: 'REWORK', desc: 'Redid something (⚠️)', detail: 'Context was lost — bad handoff signal', color: amber },
    { emoji: '↔️', name: 'BOUNCE', desc: 'A→B→A ping-pong (🔴)', detail: 'Unnecessary cycles — restructure needed', color: red },
    { emoji: '🌀', name: 'EXPLORE', desc: 'Investigation', detail: 'Uncertain outcome, research mode', color: violet },
  ];
  return (
    <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '60px 80px', display: 'flex', flexDirection: 'column' }}>
      <div className="jl-sr" style={{ fontSize: 22, color: amber, letterSpacing: '0.15em', marginBottom: 8 }}>PHASES</div>
      <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
        Every Entry Has a Phase
      </h2>
      <p className="jl-fu" style={{ fontSize: 22, color: muted, marginTop: 8, animationDelay: '0.15s' }}>
        The emoji + phase name tells you the <em>kind</em> of step at a glance.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginTop: 24 }}>
        {phases.map((p, i) => (
          <div key={i} className="jl-si" style={{ animationDelay: `${0.2 + i * 0.08}s`, background: 'rgba(255,255,255,0.02)', border: `1px solid rgba(255,255,255,0.06)`, borderRadius: 10, padding: '18px 16px' }}>
            <div style={{ fontSize: 32, marginBottom: 6 }}>{p.emoji}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: p.color }}>{p.name}</div>
            <div style={{ fontSize: 16, color: muted, marginTop: 4 }}>{p.desc}</div>
            <div style={{ fontSize: 13, color: '#475569', marginTop: 6, lineHeight: 1.4 }}>{p.detail}</div>
          </div>
        ))}
      </div>
      <div className="jl-fi" style={{ animationDelay: '0.9s', marginTop: 16, textAlign: 'center', fontSize: 18, color: '#475569' }}>
        ⚠️ <span style={{ color: amber }}>REWORK</span> and <span style={{ color: red }}>BOUNCE</span> are anti-pattern markers — they flag bad workflows
      </div>
    </div>
  );
};

// ─── Slide 6: Flow Tags ─────────────────────────────────────────────────────
const FlowTags: Page = () => {
  const tags = [
    { tag: 'smooth', icon: '⚡', meaning: 'Clean execution', good: true },
    { tag: 'handoff', icon: '🤝', meaning: 'Clean agent switch', good: true },
    { tag: 'blocked', icon: '⛔', meaning: 'External blocker', good: false, note: 'Monitor frequency' },
    { tag: 'rework', icon: '♻️', meaning: 'Had to redo something', good: false, note: '🔴 Context lost' },
    { tag: 'confused', icon: '🌀', meaning: 'Unclear requirements', good: false, note: '🔴 Poor task def' },
    { tag: 'bounced', icon: '↔️', meaning: 'A→B→A ping-pong', good: false, note: '🔴 Bad workflow' },
    { tag: 'overhead', icon: '🐌', meaning: 'Too many iterations', good: false, note: '🔴 Split it up' },
    { tag: 'rewrite', icon: '♻️', meaning: 'Full code rewrite', good: false, note: '🔴 Wrong approach first' },
  ];
  return (
    <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '60px 80px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div className="jl-sr" style={{ fontSize: 22, color: amber, letterSpacing: '0.15em', marginBottom: 8 }}>FLOW TAGS</div>
      <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
        Flow Tags Reveal Quality
      </h2>
      <p className="jl-fu" style={{ fontSize: 22, color: muted, marginTop: 8, animationDelay: '0.15s' }}>
        Every entry has a <Tag color={amber}>flow tag</Tag> — one word that tells you how well that step went.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginTop: 28 }}>
        {tags.map((t, i) => (
          <div key={i} className="jl-si" style={{ animationDelay: `${0.2 + i * 0.07}s`, background: t.good ? 'rgba(34,197,94,0.03)' : 'rgba(239,68,68,0.03)', border: `1px solid ${t.good ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)'}`, borderRadius: 10, padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 24 }}>{t.icon}</span>
              <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 24, fontWeight: 700, color: t.good ? green : red }}>{t.tag}</span>
            </div>
            <div style={{ fontSize: 16, color: muted, lineHeight: 1.4 }}>{t.meaning}</div>
            {t.note && <div style={{ fontSize: 13, color: t.good ? '#475569' : amber, marginTop: 6 }}>{t.note}</div>}
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Slide 7: The Handoff Protocol ──────────────────────────────────────────
const HandoffProtocol: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: teal, letterSpacing: '0.15em', marginBottom: 8 }}>THE PROTOCOL</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      What Every Agent Does
    </h2>
    <p className="jl-fu" style={{ fontSize: 24, color: muted, marginTop: 12, animationDelay: '0.15s' }}>
      Five steps. No exceptions. This is how context survives across agents.
    </p>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 32 }}>
      {[
        { num: '01', phase: '📖', title: 'Read the Log', desc: 'Read last 10 entries of JOURNEY.md + AGENTS.md for architecture', color: blue },
        { num: '02', phase: '🟢', title: 'Declare Intent', desc: 'Write a START entry: what you are doing, why, and the approach', color: green },
        { num: '03', phase: '⚡', title: 'Trace as You Go', desc: 'Write EXECUTE entries at milestones. Include files changed and decisions.', color: blue },
        { num: '04', phase: '🔴', title: 'Flag Problems', desc: 'Write BLOCKED when stuck. Write REWORK if redoing something.', color: red },
        { num: '05', phase: '✅🔄', title: 'Close or Hand Off', desc: 'DONE = task complete with verification. HANDOFF = explicit state + next steps.', color: green },
      ].map((step, i) => (
        <div key={i} className="jl-sr" style={{ animationDelay: `${0.2 + i * 0.1}s`, display: 'flex', alignItems: 'center', gap: 20, padding: '16px 24px', background: 'rgba(255,255,255,0.02)', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 28, fontWeight: 800, color: step.color, minWidth: 44 }}>{step.num}</div>
          <div style={{ fontSize: 32, minWidth: 48 }}>{step.phase}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{step.title}</div>
            <div style={{ fontSize: 18, color: muted }}>{step.desc}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ─── Slide 8: Spotting Bad Workflows ────────────────────────────────────────
const BadWorkflows: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: red, letterSpacing: '0.15em', marginBottom: 8 }}>FLOW DIAGNOSTICS</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      Spotting Bad Workflows
    </h2>
    <p className="jl-fu" style={{ fontSize: 24, color: muted, marginTop: 12, animationDelay: '0.15s' }}>
      Scan JOURNEY.md for these patterns to find what needs fixing.
    </p>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24, marginTop: 32 }}>
      {[
        {
          title: '♻️ REWORK entries',
          signal: 'Context was lost',
          example: 'Agent B rewrites something Agent A already wrote',
          fix: 'Improve handoff — state what was done and what state it is in',
          color: amber,
        },
        {
          title: '↔️ BOUNCE pattern',
          signal: 'Agent ping-pong',
          example: 'A→B→A on the same task in 3 entries',
          fix: 'Restructure: assign clear ownership per task',
          color: red,
        },
        {
          title: '🔴 BLOCKED frequency',
          signal: 'Missing pre-checks',
          example: 'Multiple entries blocked by the same issue (DB not running, missing API key)',
          fix: 'Add pre-flight checklist before starting tasks',
          color: violet,
        },
        {
          title: '🌀 CONFUSED tags',
          signal: 'Poor task definition',
          example: 'Agent spends half the entries investigating what to do',
          fix: 'Write clearer START entries with scope boundaries',
          color: teal,
        },
      ].map((item, i) => (
        <div key={i} className="jl-si" style={{ animationDelay: `${0.2 + i * 0.1}s`, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12, padding: '24px' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: item.color }}>{item.title}</div>
          <div style={{ fontSize: 16, color: muted, marginTop: 4 }}>Signals: <strong style={{ color: item.color }}>{item.signal}</strong></div>
          <div style={{ marginTop: 12, padding: '10px 14px', background: '#0f1219', borderRadius: 8, fontFamily: '"JetBrains Mono", monospace', fontSize: 14, color: '#94a3b8', lineHeight: 1.5 }}>
            {item.example}
          </div>
          <div style={{ fontSize: 15, color: muted, marginTop: 10 }}>
            <span style={{ color: green }}>→</span> {item.fix}
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ─── Slide 9: Flow Health Dashboard ─────────────────────────────────────────
const FlowHealth: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: green, letterSpacing: '0.15em', marginBottom: 8 }}>ANALYSIS</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      Flow Health Report
    </h2>
    <p className="jl-fu" style={{ fontSize: 24, color: muted, marginTop: 8, animationDelay: '0.15s' }}>
      A script can analyze JOURNEY.md and generate this. Scan manually too.
    </p>
    <div className="jl-si" style={{ animationDelay: '0.25s', fontFamily: '"JetBrains Mono", monospace', background: '#0f1219', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, padding: '28px 32px', marginTop: 28, fontSize: 16, lineHeight: 1.8 }}>
      <div style={{ color: '#f7f8f8', fontSize: 20, fontWeight: 700, marginBottom: 16 }}>📊 Flow Health — micha-stocks</div>
      <div style={{ color: muted }}>Period: 2026-05-01 → 2026-05-14 · Entries: 42 total</div>
      <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 32px' }}>
        <div>smooth    <span style={{ color: green }}>████████████████</span>  25 (60%)</div>
        <div>handoff   <span style={{ color: blue }}>██████</span>  8 (19%)</div>
        <div>blocked   <span style={{ color: amber }}>███</span>  4 (10%)</div>
        <div style={{ color: amber }}>rework    ██  3 (7%)</div>
        <div style={{ color: red }}>confused  █  2 (5%)</div>
      </div>
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', marginTop: 16, paddingTop: 16 }}>
        <div style={{ color: amber }}>⚠️ Issues detected:</div>
        <div style={{ color: '#94a3b8', marginLeft: 16 }}>• Bounce on entries #12→#13→#14 (same task, 2 agents, 3 handoffs)</div>
        <div style={{ color: '#94a3b8', marginLeft: 16 }}>• Blocked ratio 10% — consider pre-flight checks</div>
      </div>
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', marginTop: 12, paddingTop: 12 }}>
        <div style={{ color: green }}>📈 Trend: Smooth ↑ 55% → 82%</div>
      </div>
    </div>
  </div>
);

// ─── Slide 10: Live Example ─────────────────────────────────────────────────
const LiveExample: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '60px 80px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: amber, letterSpacing: '0.15em', marginBottom: 8 }}>LIVE EXAMPLE</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      A Real Workflow in the Log
    </h2>
    <p className="jl-fu" style={{ fontSize: 22, color: muted, marginTop: 8, animationDelay: '0.15s' }}>
      Here is how the journey log system <em>itself</em> was built — from start to shipping.
    </p>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 28 }}>
      {[
        { num: '#001', phase: '🟢', name: 'START', desc: 'Design the system', tag: 'smooth', tagColor: green },
        { num: '#002', phase: '⚡', name: 'EXECUTE', desc: 'Write JOURNEY.md', tag: 'smooth', tagColor: green },
        { num: '#003', phase: '⚡', name: 'EXECUTE', desc: 'Update AGENTS.md', tag: 'smooth', tagColor: green },
        { num: '#004', phase: '⚡', name: 'EXECUTE', desc: 'Update CLAUDE.md', tag: 'smooth', tagColor: green },
        { num: '#005', phase: '✅', name: 'DONE', desc: 'Commit & push', tag: 'smooth', tagColor: green },
      ].map((e, i) => (
        <div key={i} className="jl-si" style={{ animationDelay: `${0.2 + i * 0.1}s`, flex: '1 0 calc(20% - 10px)', minWidth: 160, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 10, padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 16, color: violet }}>{e.num}</span>
            <span style={{ fontSize: 18 }}>{e.phase}</span>
            <span style={{ fontSize: 16, fontWeight: 700, color: e.tagColor }}>{e.name}</span>
          </div>
          <div style={{ fontSize: 14, color: muted, marginTop: 6 }}>{e.desc}</div>
          <div style={{ marginTop: 8 }}><Tag color={e.tagColor}>{e.tag}</Tag></div>
        </div>
      ))}
    </div>
    <div className="jl-fi" style={{ animationDelay: '0.8s', marginTop: 20, fontFamily: '"JetBrains Mono", monospace', background: '#0f1219', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, padding: '12px 16px', fontSize: 14, color: '#94a3b8' }}>
      <span style={{ color: muted }}>$ git log --oneline</span><br />
      <span style={{ color: green }}>ffb31c8</span> feat: add journey log system for agent traceability<br />
      <span style={{ color: green }}>480c0ac</span> feat: initial commit with AGENTS.md, CLAUDE.md, README
    </div>
  </div>
);

// ─── Slide 11: Summary ─────────────────────────────────────────────────────
const Summary: Page = () => (
  <div style={{ ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)', padding: '80px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div className="jl-sr" style={{ fontSize: 22, color: amber, letterSpacing: '0.15em', marginBottom: 8 }}>SUMMARY</div>
    <h2 className="jl-fu" style={{ fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 800, margin: 0, lineHeight: 1.1, animationDelay: '0.1s' }}>
      One File. Full Visibility.
    </h2>
    <p className="jl-fu" style={{ fontSize: 26, color: muted, maxWidth: 1400, marginTop: 12, lineHeight: 1.4, animationDelay: '0.15s' }}>
      JOURNEY.md turns invisible agent work into a readable story.
    </p>
    <div style={{ display: 'flex', gap: 24, marginTop: 40 }}>
      {[
        { icon: '📖', title: 'Readable', items: ['Self-teaching header legend', 'Append-only timeline', 'Git-tracked, travels with repo'], color: blue },
        { icon: '🔍', title: 'Diagnostic', items: ['Flow tags = quality signals', 'Scan for rework, bounce, confusion', 'Trend tracking over time'], color: amber },
        { icon: '🤝', title: 'Handoff-Ready', items: ['Agents read before starting', 'HANDOFF entries carry state', 'No more context loss'], color: green },
      ].map((col, i) => (
        <div key={i} className="jl-si" style={{ animationDelay: `${0.25 + i * 0.12}s`, flex: 1, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12, padding: '28px 24px' }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>{col.icon}</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: col.color, marginBottom: 12 }}>{col.title}</div>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {col.items.map((item, j) => (
              <li key={j} style={{ fontSize: 17, color: '#94a3b8', padding: '4px 0', lineHeight: 1.5 }}>
                <span style={{ color: col.color, marginRight: 8 }}>→</span>{item}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
    <div className="jl-fu" style={{ animationDelay: '0.65s', marginTop: 32, textAlign: 'center', fontSize: 20, color: muted }}>
      Open <span style={{ fontFamily: '"JetBrains Mono", monospace', color: amber }}>JOURNEY.md</span> to see the full story →{' '}
      <a href="https://github.com/korm85/micha-stocks/blob/main/JOURNEY.md" style={{ color: blue }}>github.com/korm85/micha-stocks</a>
    </div>
  </div>
);

// ─── Export ─────────────────────────────────────────────────────────────────
export const meta: SlideMeta = { title: 'Journey Log Workflow Guide' };
export default [Cover, Problem, Solution, ReadingTheLog, Phases, FlowTags, HandoffProtocol, BadWorkflows, FlowHealth, LiveExample, Summary] satisfies Page[];

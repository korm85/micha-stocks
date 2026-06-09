# Global Claude Code Instructions

## Model Tag
Every response MUST begin with [Model: Haiku], [Model: Sonnet], or [Model: Opus].

## Subagent Routing
| Task | Model |
|---|---|
| Search / read / grep / glob | Haiku |
| Code writing / editing (default) | Sonnet |
| Architecture / planning / design | Opus |

Model IDs: haiku=claude-haiku-4-5-20251001, sonnet=claude-sonnet-4-6, opus=claude-opus-4-8

## Agent Announcements
Before every Agent call output: "Spawning [type] on [Model] — [task]"

## Superpowers Skill Invocation Rules
`using-superpowers` is injected at session start via hook — do NOT invoke it again via Skill tool.

Before each response, check if a task-specific skill applies:
- Complex feature / UI work → `superpowers:brainstorming`
- Bug / test failure → `superpowers:systematic-debugging`
- New feature implementation → `superpowers:test-driven-development`
- Multi-step plan execution → `superpowers:executing-plans`
- Completing branch work → `superpowers:finishing-a-development-branch`
- Trivial tasks (auth, config, short Q&A) → no skill invocation needed

## Superpowers Hard Gate — Non-Negotiable Sequence

For ANY new feature or project, this exact sequence is MANDATORY. No step can be skipped for any reason:

1. **Invoke `superpowers:brainstorming`** — explore project context, list explicit assumptions, clarify intent
2. **State assumptions** — if user cannot answer questions, list assumptions taken and say "proceeding unless you push back"
3. **Present 2-3 approaches** with trade-offs and recommendation — wait for user acknowledgement
4. **Write design doc** → `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` — commit it
5. **Invoke `superpowers:writing-plans`** — create implementation plan
6. **Write plan** → `docs/superpowers/plans/YYYY-MM-DD-<topic>-plan.md` — commit it
7. **Invoke `superpowers:executing-plans`** — load plan, mark tasks in_progress/completed as you go
8. **Invoke `superpowers:finishing-a-development-branch`** — verify, commit, PR

### Quick-build shortcut (user says "just build it" or is in a hurry)
Still follow the sequence — just compress it:
- Skip visual companion
- State assumptions explicitly as a bullet list: "I'm assuming X, Y, Z — proceeding in 30s unless you push back"
- Propose one recommended approach with brief trade-off note
- Write a short spec (can be 1 page) before any code
- Plan can be inline task list (no need for full doc if scope is tiny)
- Gate hook will block code writes if no plan file exists

### What is enforced by hook
The `superpowers-gate.sh` PreToolUse hook blocks all Write calls to `.ts/.tsx/.js/.jsx/.py/.go/.rs` files unless `docs/superpowers/plans/*.md` exists in the git root. This cannot be bypassed without modifying settings.json.

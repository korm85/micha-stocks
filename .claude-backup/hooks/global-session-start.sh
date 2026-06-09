#!/usr/bin/env bash

CLAUDE_PROJECTS="$HOME/.claude/projects"
GLOBAL_MEM="$CLAUDE_PROJECTS/global/memory"

BASE="GLOBAL: Start every response with [Model: Haiku/Sonnet/Opus]. Route subagents: Haiku=search/reads, Sonnet=code (default), Opus=architecture. Announce every Agent spawn."

inject_dir() {
    local dir="$1" label="$2" out=""
    [[ -d "$dir" ]] || return
    for f in "$dir"/*.md; do
        [[ -f "$f" ]] || continue
        [[ "$(basename "$f")" == "MEMORY.md" ]] && continue  # index only, skip
        out+=$'\n\n--- '"$label/$(basename "$f")"$' ---\n'"$(cat "$f")"
    done
    echo "$out"
}

MEMORY_CONTENT=$(inject_dir "$GLOBAL_MEM" "global")

if [[ "$PWD" == "$HOME/projects/work"* ]]; then
    CONTEXT_LABEL="work"
    echo "work" > "$HOME/.claude/.session-context"
    MEMORY_CONTENT+=$(inject_dir "$CLAUDE_PROJECTS/work/memory" "work")
elif [[ "$PWD" == "$HOME/projects/personal"* ]]; then
    CONTEXT_LABEL="personal"
    echo "personal" > "$HOME/.claude/.session-context"
    MEMORY_CONTENT+=$(inject_dir "$CLAUDE_PROJECTS/personal/memory" "personal")
else
    CONTEXT_LABEL="none (launched outside work/ or personal/ — only global memory loaded)"
    echo "none" > "$HOME/.claude/.session-context"
fi

MEMORY_CONTENT+=$'\n\n--- session-context ---\nCWD: '"$PWD"$'\nLoaded context: '"$CONTEXT_LABEL"

if [[ -n "$MEMORY_CONTENT" ]]; then
    FULL="$BASE"$'\n\nMEMORY:'"$MEMORY_CONTENT"
else
    FULL="$BASE"
fi

jq -n --arg ctx "$FULL" '{"hookSpecificOutput":{"additionalContext":$ctx}}'

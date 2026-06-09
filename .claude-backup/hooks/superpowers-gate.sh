#!/bin/bash
# superpowers-gate.sh — PreToolUse hook
# Blocks writing source code files when no implementation plan exists in the project.
# Forces brainstorming → spec → plan workflow before any code is written for new features.

INPUT=$(cat)

# Extract the file path from the tool input JSON
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    inp = d.get('tool_input', {})
    print(inp.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null)

# Only gate on source code files
if ! echo "$FILE_PATH" | grep -qE '\.(ts|tsx|js|jsx|py|go|rs|vue|svelte)$'; then
    exit 0
fi

# Allow writing spec and plan files themselves (the gate artifacts)
if echo "$FILE_PATH" | grep -q "docs/superpowers"; then
    exit 0
fi

# Resolve the git root from the file's directory
DIR=$(dirname "$FILE_PATH")
if [ ! -d "$DIR" ]; then
    # New file — try parent directory
    DIR=$(dirname "$DIR")
fi

GIT_ROOT=$(cd "$DIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)

# Not in a git repo — skip gate (can't determine project root)
if [ -z "$GIT_ROOT" ]; then
    exit 0
fi

# Count plan files
PLAN_COUNT=$(find "$GIT_ROOT/docs/superpowers/plans" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

if [ "$PLAN_COUNT" -eq 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  SUPERPOWERS GATE — SOURCE CODE BLOCKED                      ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  No implementation plan found in:                            ║"
    echo "║  $GIT_ROOT/docs/superpowers/plans/                          ║"
    echo "║                                                              ║"
    echo "║  Required workflow BEFORE writing source code:               ║"
    echo "║  1. Skill: superpowers:brainstorming                         ║"
    echo "║     → Write spec to docs/superpowers/specs/YYYY-MM-DD-*.md  ║"
    echo "║  2. Skill: superpowers:writing-plans                         ║"
    echo "║     → Write plan to docs/superpowers/plans/YYYY-MM-DD-*.md  ║"
    echo "║  3. Skill: superpowers:executing-plans                       ║"
    echo "║     → Load plan, then proceed with implementation            ║"
    echo "║                                                              ║"
    echo "║  File blocked: $FILE_PATH"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 2
fi

exit 0

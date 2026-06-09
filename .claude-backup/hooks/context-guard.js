#!/usr/bin/env node
const fs = require('fs');
const os = require('os');
const path = require('path');

const CONTEXT_FILE = path.join(os.homedir(), '.claude', '.session-context');

const WORK_SIGNALS = [
  'gavan', 'dental', 'shade', 'coloring instruction', 'lab', 'clinic',
  'matan', 'roy sterenthal', 'yael', 'yuli', 'rehovot', 'marketplace',
  'detection model', 'mvp', 'pre-seed', 'beta launch'
];
const PERSONAL_SIGNALS = [
  'portfolio', 'stocks', 'resume', 'micha-stocks', 'michael-korenevsky'
];

let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const prompt = (data.prompt || '').toLowerCase();

    let currentContext = 'none';
    try { currentContext = fs.readFileSync(CONTEXT_FILE, 'utf8').trim(); } catch (e) {}

    if (currentContext === 'none') {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: "CONTEXT WARNING: Session launched from outside ~/projects/work/ or ~/projects/personal/. Before responding to the user's request, ask them: which context are they working in (work or personal)? Suggest restarting Claude from the correct directory first."
        }
      }));
      return;
    }

    const hasWorkSignal = WORK_SIGNALS.some(s => prompt.includes(s));
    const hasPersonalSignal = PERSONAL_SIGNALS.some(s => prompt.includes(s));

    if (currentContext === 'personal' && hasWorkSignal) {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: "CONTEXT MISMATCH: Currently in personal context but prompt appears work-related (Gavan AI / dental domain). Before proceeding, ask the user: 'This looks like work — did you mean to launch Claude from ~/projects/work/? Should I proceed here or do you want to restart from the correct directory?'"
        }
      }));
    } else if (currentContext === 'work' && hasPersonalSignal) {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: "CONTEXT MISMATCH: Currently in work context but prompt appears personal (portfolio / stocks / resume). Before proceeding, ask the user: 'This looks personal — did you mean to launch Claude from ~/projects/personal/? Should I proceed here or do you want to restart from the correct directory?'"
        }
      }));
    }

  } catch (e) { /* silent fail */ }
});

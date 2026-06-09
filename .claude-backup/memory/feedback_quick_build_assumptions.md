---
name: feedback-quick-build-assumptions
description: "When user asks for a quick build without detailed answers, state explicit assumptions and give brief window to push back before proceeding"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1e6ed041-09f5-4cd8-b68f-44b70b465ce8
---

For quick app builds where the user hasn't answered all clarifying questions: still follow the superpowers planning flow, but list the assumptions being taken explicitly. Tell the user "proceeding unless you push back" — do not wait indefinitely for answers. If they don't push back, treat silence as approval and move forward.

**Why:** User does not want to babysit the planning process, but also doesn't want planning skipped. The compromise is explicit assumptions + brief push-back window.

**How to apply:** In the brainstorming step, after exploring context, output something like: "Assumptions I'm taking: [list]. Proceeding in ~30 seconds unless you push back." Then proceed with the plan. Never skip the spec/plan files even on quick builds — just make them concise (1 page is fine).

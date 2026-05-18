#!/usr/bin/env python3
"""
Post-process the open-slide build output for serving behind Tailscale Funnel.

open-slide uses Vite with configFile: false, so we can't set base via vite.config.ts.
Tailscale Funnel serves at /deck/ and strips the prefix before forwarding.
This script patches the build so:
  - index.html: asset paths are RELATIVE (resolved by <base href="/deck/">)
  - CSS: font paths use /deck/assets/ (CSS url() doesn't respect <base>)
"""
import os, re

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
INDEX = os.path.join(DIST, 'index.html')

# ── Step 1: Patch index.html ────────────────────────────────────────────────
with open(INDEX, 'r') as f:
    html = f.read()

# Add <base href="/deck/" />
if '<base href="/deck/"' not in html:
    html = html.replace('<head>', '<head>\n    <base href="/deck/" />')

# Convert absolute asset paths to relative (so <base> resolves them)
html = re.sub(r'(src|href)="/assets/', r'\1="assets/', html)

with open(INDEX, 'w') as f:
    f.write(html)
print(f"✓ Patched {INDEX}")

# ── Step 2: Patch CSS font paths ────────────────────────────────────────────
assets_dir = os.path.join(DIST, 'assets')
for fname in os.listdir(assets_dir):
    if not fname.endswith('.css'):
        continue
    fpath = os.path.join(assets_dir, fname)
    with open(fpath, 'r') as f:
        css = f.read()
    
    new_css = css.replace('/assets/', '/deck/assets/')
    if new_css != css:
        with open(fpath, 'w') as f:
            f.write(new_css)
        count = new_css.count('/deck/assets/')
        print(f"✓ Patched {fname}: {count} font paths rewritten")

print("✅ Deck build ready for /deck/ serving")

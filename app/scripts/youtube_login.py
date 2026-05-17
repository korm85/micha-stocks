#!/usr/bin/env python3.14
"""
YouTube Login via Chrome DevTools Protocol
Logs into YouTube, extracts cookies for yt-dlp
"""
import json
import os
import sys
import time
import urllib.request
import websocket

DEBUG_URL = "http://localhost:9222"
EMAIL = "mikclaw463@gmail.com"
PASSWORD = "Mik_Claw!1"
COOKIE_FILE = os.path.expanduser("~/youtube_cookies.txt")

def ws_send(ws, method, params=None):
    """Send a CDP command and return the result."""
    msg_id = int(time.time() * 1000) % 100000
    payload = {"id": msg_id, "method": method}
    if params:
        payload["params"] = params
    ws.send(json.dumps(payload))
    # Wait for response
    while True:
        resp = json.loads(ws.recv())
        if resp.get("id") == msg_id:
            return resp.get("result")

def main():
    # Step 1: Get a page target
    print("🔧 Connecting to Chromium...")
    resp = urllib.request.urlopen(f"{DEBUG_URL}/json")
    targets = json.loads(resp.read())
    
    # Find or create a page
    page = None
    for t in targets:
        if t.get("type") == "page":
            page = t
            break
    
    if not page:
        # Create new page
        resp = urllib.request.urlopen(f"{DEBUG_URL}/json/new")
        page = json.loads(resp.read())
    
    ws_url = page["webSocketDebuggerUrl"]
    print(f"📄 Connected to page: {page.get('title', '?')}")
    
    # Step 2: Connect via websocket
    ws = websocket.create_connection(ws_url, timeout=60)
    
    # Enable necessary domains
    ws_send(ws, "Page.enable")
    ws_send(ws, "Network.enable")
    ws_send(ws, "Runtime.enable")
    
    # Step 3: Navigate to YouTube
    print("🌐 Navigating to YouTube...")
    ws_send(ws, "Page.navigate", {"url": "https://www.youtube.com"})
    time.sleep(4)
    
    # Step 4: Click "Sign in" button
    print("🔑 Clicking Sign In...")
    # Find sign-in button via JavaScript
    result = ws_send(ws, "Runtime.evaluate", {
        "expression": """
        (() => {
            const buttons = document.querySelectorAll('a[aria-label*=\"Sign\"], a[href*=\"ServiceLogin\"]');
            if (buttons.length > 0) {
                buttons[0].click();
                return 'clicked sign in button';
            }
            // Try top bar sign in
            const tp = document.querySelector('tp-yt-paper-button[aria-label*=\"Sign\"]');
            if (tp) { tp.click(); return 'clicked paper button'; }
            // Force navigate to login
            window.location.href = 'https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com';
            return 'redirected to login';
        })()
        """,
        "awaitPromise": False
    })
    print(f"  -> {result}")
    time.sleep(5)
    
    # Step 5: Fill in email
    print("📧 Entering email...")
    result = ws_send(ws, "Runtime.evaluate", {
        "expression": f"""
        (() => {{
            const emailInput = document.querySelector('input[type=\"email\"], input[name=\"identifier\"]');
            if (emailInput) {{
                emailInput.focus();
                emailInput.value = '{EMAIL}';
                emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                emailInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                // Click Next
                const nextBtn = document.querySelector('#identifierNext button, [jsname=\"V67aGc\"]');
                if (nextBtn) nextBtn.click();
                return 'email entered and next clicked';
            }}
            return 'no email input found - ' + document.title;
        }})()
        """,
        "awaitPromise": False
    })
    print(f"  -> {result}")
    time.sleep(4)
    
    # Step 6: Fill in password
    print("🔒 Entering password...")
    result = ws_send(ws, "Runtime.evaluate", {
        "expression": f"""
        (() => {{
            const pwInput = document.querySelector('input[type=\"password\"], input[name=\"password\"]');
            if (pwInput) {{
                pwInput.focus();
                pwInput.value = '{PASSWORD}';
                pwInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                pwInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                // Click Next
                const nextBtn = document.querySelector('#passwordNext button, [jsname=\"V67aGc\"]');
                if (nextBtn) nextBtn.click();
                return 'password entered and next clicked';
            }}
            return 'no password input found - ' + document.title + ' | URL: ' + window.location.href;
        }})()
        """,
        "awaitPromise": False
    })
    print(f"  -> {result}")
    
    # Step 7: Wait for login to complete
    print("⏳ Waiting for login to complete...")
    max_wait = 30
    for i in range(max_wait):
        time.sleep(2)
        result = ws_send(ws, "Runtime.evaluate", {
            "expression": "window.location.href",
            "awaitPromise": False
        })
        url = result.get("result", {}).get("value", "")
        print(f"  [{i*2}s] URL: {url[:80]}")
        
        # Check if we're back on YouTube
        if "youtube.com" in url and "ServiceLogin" not in url and "signin" not in url.lower():
            print("✅ Logged in! Back on YouTube.")
            break
        if "myaccount" in url or "myaccount.google.com" in url:
            print("✅ Login successful (landed on account page, redirecting to YouTube)")
            # Navigate to YouTube
            ws_send(ws, "Page.navigate", {"url": "https://www.youtube.com"})
            time.sleep(3)
            break
    
    # Step 8: Navigate to YouTube and extract cookies
    print("🍪 Extracting cookies...")
    ws_send(ws, "Page.navigate", {"url": "https://www.youtube.com"})
    time.sleep(3)
    
    result = ws_send(ws, "Network.getCookies", {"urls": ["https://www.youtube.com", "https://accounts.google.com"]})
    cookies = result.get("cookies", []) if result else []
    
    print(f"📦 Got {len(cookies)} cookies")
    
    # Step 9: Save in Netscape format for yt-dlp
    with open(COOKIE_FILE, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
        f.write("# This file was generated by YouTube Login Script\n\n")
        
        for c in cookies:
            domain = c.get("domain", "")
            # Skip non-youtube cookies
            if "youtube.com" not in domain and "google.com" not in domain and ".ytimg.com" not in domain:
                continue
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure", False) else "FALSE"
            expiry = str(int(c.get("expires", 0)))
            name = c.get("name", "")
            value = c.get("value", "")
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
    
    print(f"✅ Cookies saved to {COOKIE_FILE}")
    
    # Step 10: Test with yt-dlp
    print("\n🧪 Testing with yt-dlp...")
    import subprocess
    result = subprocess.run([
        "yt-dlp", "--cookies", COOKIE_FILE,
        "--write-auto-subs", "--sub-langs", "iw,en,he",
        "--skip-download", "--convert-subs", "srt",
        "--sleep-interval", "2",
        "-o", "/tmp/test_sub",
        "https://www.youtube.com/watch?v=ojw17-H8ptw"
    ], capture_output=True, text=True, timeout=60)
    
    print(result.stdout[-500:] if result.stdout else "")
    if result.stderr:
        print("STDERR:", result.stderr[-500:])
    
    if "ERROR" not in result.stderr and result.returncode == 0:
        print("\n✅ SUCCESS! Transcripts are accessible.")
    else:
        print("\n⚠️  Had issues. Check the cookie file and try again.")
    
    # Cleanup
    ws.close()
    print("🔌 Done")

if __name__ == "__main__":
    main()

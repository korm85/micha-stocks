#!/usr/bin/env python3.14
"""
Micha Stocks — Query Engine
============================
Takes a trading question, retrieves relevant reasoning patterns from the KB,
and generates a recommendation using DeepSeek V4 Pro.

Usage:
  python3 query.py "Should I buy NVDA right now?"
  python3 query.py --stock AAPL "What does Micha say about Apple at current PE?"
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "micha.db")
OPENCODE_API = "https://opencode.ai/zen/go/v1/chat/completions"
API_KEY_ENV = "OPENCODE_GO_API_KEY"
MAX_PATTERNS = 10  # Top patterns to pass to the reasoning model

# ── Database ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def search_patterns(conn, query, limit=MAX_PATTERNS):
    """Search reasoning patterns by keyword relevance."""
    # Step 1: FTS5 keyword search on patterns
    # Escape special FTS5 characters
    fts_query = ' OR '.join(
        f'"{w}"' for w in query.split() 
        if len(w) > 2 and w not in {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'was'}
    )
    if not fts_query:
        fts_query = query
    
    try:
        cur = conn.execute("""
            SELECT rp.*, v.title as video_title
            FROM patterns_fts fts
            JOIN reasoning_patterns rp ON fts.rowid = rp.id
            JOIN videos v ON rp.video_id = v.id
            WHERE patterns_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit * 3))  # Get more for reranking
        results = [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        # Fallback if FTS5 query fails
        cur = conn.execute("""
            SELECT rp.*, v.title as video_title
            FROM reasoning_patterns rp
            JOIN videos v ON rp.video_id = v.id
            LIMIT ?
        """, (limit,))
        results = [dict(r) for r in cur.fetchall()]
    
    # Step 2: Also search transcript chunks for direct mentions
    try:
        cur = conn.execute("""
            SELECT tc.text, v.title as video_title, v.id as video_id
            FROM chunks_fts fts
            JOIN transcript_chunks tc ON fts.rowid = tc.id
            JOIN videos v ON tc.video_id = v.id
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT 5
        """, (fts_query,))
        chunks = [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        chunks = []
    
    return results, chunks

def get_all_patterns(conn):
    """Get all reasoning patterns for comprehensive analysis."""
    cur = conn.execute("""
        SELECT rp.*, v.title as video_title
        FROM reasoning_patterns rp
        JOIN videos v ON rp.video_id = v.id
        ORDER BY rp.pattern_type
    """)
    return [dict(r) for r in cur.fetchall()]

# ── Market Data ───────────────────────────────────────────────────────

def get_stock_data(ticker):
    """Get current stock data using yfinance."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        return {
            'ticker': ticker.upper(),
            'price': price,
            'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
            'market_cap': info.get('marketCap'),
            '52w_high': info.get('fiftyTwoWeekHigh'),
            '52w_low': info.get('fiftyTwoWeekLow'),
            'volume': info.get('volume'),
            'avg_volume': info.get('averageVolume'),
            'dividend_yield': info.get('dividendYield'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'revenue_growth': info.get('revenueGrowth'),
            'profit_margins': info.get('profitMargins'),
            'recommendation': info.get('recommendationKey'),
            'target_mean_price': info.get('targetMeanPrice'),
            'description': info.get('longBusinessSummary', '')[:500],
        }
    except ImportError:
        return {'ticker': ticker.upper(), 'error': 'yfinance not installed'}
    except Exception as e:
        return {'ticker': ticker.upper(), 'error': str(e)[:200]}

# ── OpenCode API ──────────────────────────────────────────────────────

def call_opencode(model, messages, max_tokens=4096, temperature=0.5):
    """Call the OpenCode Go API."""
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        return {"error": f"{API_KEY_ENV} not set"}
    
    import requests
    try:
        resp = requests.post(
            OPENCODE_API,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=180
        )
        data = resp.json()
        if 'choices' in data:
            content = data['choices'][0]['message'].get('content', '')
            reasoning = data['choices'][0]['message'].get('reasoning_content', '')
            return {'content': content, 'reasoning': reasoning}
        else:
            return {'error': json.dumps(data, ensure_ascii=False)[:300]}
    except Exception as e:
        return {'error': str(e)[:300]}

# ── Query Pipeline ────────────────────────────────────────────────────

def extract_tickers(query):
    """Simple ticker extraction from query."""
    import re
    # Common stock tickers are 1-5 uppercase letters
    potential = re.findall(r'\b[A-Z]{1,5}\b', query.upper())
    return potential[:3]  # Return up to 3 tickers

def query_engine(user_query, use_reasoning_model=True):
    """Main query pipeline."""
    start = time.time()
    
    print(f"🔍 Query: {user_query}\n")
    
    # Phase 1: Extract intent (using simple logic for now)
    tickers = extract_tickers(user_query)
    print(f"📊 Detected tickers: {tickers if tickers else 'none (general query)'}")
    
    # Phase 2: Get market data for detected tickers
    market_data = {}
    if tickers:
        for t in tickers[:1]:  # Just the first ticker for now
            data = get_stock_data(t)
            market_data[t] = data
            print(f"   {t}: ${data.get('price', 'N/A')} | PE: {data.get('pe_ratio', 'N/A')} | "
                  f"52w: {data.get('52w_low', '?')}-{data.get('52w_high', '?')}")
    
    # Phase 3: Search knowledge base
    conn = get_db()
    patterns, chunks = search_patterns(conn, user_query)
    all_patterns = get_all_patterns(conn)
    conn.close()
    
    print(f"\n📚 KB patterns found: {len(patterns)} relevant, {len(chunks)} direct mentions")
    print(f"   Total patterns in KB: {len(all_patterns)}")
    
    # Phase 4: Format context for the reasoning model
    if patterns:
        context = "## Micha's Relevant Reasoning Patterns\n\n"
        for i, p in enumerate(patterns[:MAX_PATTERNS], 1):
            context += f"### {i}. {p['pattern_type'].replace('_', ' ').title()}\n"
            context += f"**Trigger:** {p['trigger_context']}\n"
            context += f"**Reasoning:** {p['reasoning']}\n"
            context += f"**Conditions:** {p.get('conditions', 'None')}\n"
            context += f"**Signal:** {p['confidence_signal']}\n\n"
    else:
        context = "## Micha's Reasoning Framework\n\n"
        for i, p in enumerate(all_patterns, 1):
            context += f"### {i}. {p['pattern_type'].replace('_', ' ').title()}\n"
            context += f"**Reasoning:** {p['reasoning']}\n\n"
    
    if chunks:
        context += "## Direct Mentions from Videos\n\n"
        for c in chunks[:3]:
            context += f"> {c['text'][:300]}...\n\n"
    
    # Format market data
    market_context = ""
    if market_data:
        for ticker, data in market_data.items():
            market_context += f"## {ticker} Current Data\n"
            for k, v in data.items():
                if v and k not in ('ticker', 'error', 'description'):
                    market_context += f"- {k}: {v}\n"
            if 'error' in data:
                market_context += f"- Error fetching data: {data['error']}\n"
            market_context += "\n"
    
    # Phase 5: Call the model
    print(f"\n🧠 Calling reasoning model...")
    
    if use_reasoning_model:
        model = "deepseek-v4-pro"
    else:
        model = "deepseek-v4-flash"
    
    system_prompt = """You are a stock market analyst applying Micha's reasoning framework to current market data.
Given a user's trading question, Micha's relevant reasoning patterns from his YouTube channel, and current market data:
1. Analyze how Micha's logic applies to the current situation
2. Identify which patterns are most relevant
3. Make a clear recommendation with confidence level
4. List key conditions to watch that would change the recommendation
5. Be honest about uncertainty — say "Micha's framework doesn't directly address this" if applicable"""

    user_prompt = f"""## User Question
{user_query}

{market_context}
{context}
## Task
Apply Micha's reasoning framework to answer the user's question.
- Which of Micha's patterns apply here?
- What would his judgment be given current data?
- What's your recommendation and confidence level?
- What conditions would change the recommendation?"""
    
    result = call_opencode(model, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    elapsed = time.time() - start
    print(f"\n⏱️  Total time: {elapsed:.0f}s")
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
        return None
    
    output = result.get('content', '')
    reasoning = result.get('reasoning', '')
    
    if reasoning:
        print(f"\n🧠 DeepSeek's reasoning:\n{reasoning}\n")
    print(f"\n{'='*60}")
    print(output)
    print(f"{'='*60}")
    
    return output

def interactive_mode():
    """Interactive query loop."""
    print("Micha Stocks KB Query Engine")
    print("Type 'exit' to quit, '--flash' to use DeepSeek V4 Flash instead of Pro\n")
    
    use_pro = True
    
    while True:
        try:
            q = input("\n❓ ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not q:
            continue
        if q.lower() == 'exit':
            break
        if q == '--flash':
            use_pro = False
            print("Switched to DeepSeek V4 Flash")
            continue
        if q == '--pro':
            use_pro = True
            print("Switched to DeepSeek V4 Pro")
            continue
        
        query_engine(q, use_reasoning_model=use_pro)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != '--interactive':
        query = ' '.join(sys.argv[1:])
        use_pro = '--flash' not in sys.argv
        query_engine(query, use_reasoning_model=use_pro)
    else:
        interactive_mode()

#!/usr/bin/env python3
"""Mine transcript chunks for new pattern topics not covered by existing 12 patterns."""

import sqlite3
import re
import sys

conn = sqlite3.connect("/home/nuc/micha-stocks-app/data/micha.db")
cur = conn.cursor()

# Topic keyword sets - Hebrew
topics = {
    "technical_analysis": {
        "keywords": ["RSI", "MACD", "תמיכה", "התנגדות", "חוזק יחסי", "מדד חוזק", 
                     "ממוצע נע", "ניע", "בולינגר", "נפילת סכין", "דוג'י", "פמוט",
                     "רמת תמיכה", "רמת התנגדות"],
        "desc": "Technical indicators (RSI, MACD, support/resistance, moving averages)"
    },
    "volume_analysis": {
        "keywords": ["ווליום", "נפח", "נפח מסחר", "נפח גדול"],
        "desc": "Volume analysis"
    },
    "fundamental_analysis": {
        "keywords": ["מכפיל", "רווח", "הון", "חוב", "דוח כספי", "מאזן", "תזרים", 
                     "מכירות", "הכנסות", "שווי", "מכפיל רווח", "שווי שוק"],
        "desc": "Fundamental analysis (P/E, earnings, balance sheet, cash flow)"
    },
    "portfolio_rebalancing": {
        "keywords": ["איזון מחדש", "חלוקה", "פיזור", "תיק השקעות", "הקצאת נכסים", 
                     "בניית תיק", "גיוון", "פיזור סיכונים"],
        "desc": "Portfolio management / rebalancing"
    },
    "risk_management": {
        "keywords": ["ניהול סיכונים", "סיכון", "סיכונים", "גידור", "הגנה"],
        "desc": "Risk management"
    },
    "crypto_bitcoin": {
        "keywords": ["ביטקוין", "קריפטו", "ביטקויין", "אתריום", "את'ריום",
                     "מטבע דיגיטלי", "בלוקצ'יין"],
        "desc": "Crypto / Bitcoin"
    },
    "options_leverage": {
        "keywords": ["אופציות", "מינוף", "ממנף", "מנוף", "כתיבת אופציות"],
        "desc": "Options / leverage"
    },
    "shorting": {
        "keywords": ["שורט", "פוט", "מכירה בחסר", "שורטים", "שורטינג"],
        "desc": "Shorting"
    },
    "taking_profits": {
        "keywords": ["לקחת רווחים", "רווחים", "מימוש רווחים", "מימוש", "מכירה חלקית"],
        "desc": "Taking profits / scaling out"
    },
    "dollar_cost_averaging": {
        "keywords": ["ממוצע", "דולר קוסט", "השקעה קבועה", "הפקדה חודשית", "תוכנית חיסכון"],
        "desc": "Dollar-cost averaging"
    },
    "news_trading": {
        "keywords": ["חדשות", "אירוע", "הודעה", "דיווח", "הכרזה", "עדכון", "קונצנזוס", "הפתעה"],
        "desc": "News trading / events"
    },
    "market_regime": {
        "keywords": ["שוק שור", "שוק דוב", "מחזור", "סייקל", "מחזוריות", "מגמה", 
                     "שוק דובי", "מגמת עלייה", "מגמת ירידה"],
        "desc": "Market regime / cycle"
    },
    "bonds_rates": {
        "keywords": ["אגח", "ריבית", "פד", "פדרל", "אינפלציה", "תשואה", "אגרות חוב"],
        "desc": "Bonds / interest rates / Fed"
    },
    "institutional": {
        "keywords": ["מוסדי", "פנים", "קרן", "קרנות", "בנק", "בנקים", "מנהל תיקים", 
                     "מוסדיים", "השקעות מוסדיות"],
        "desc": "Insider / institutional"
    },
    "cash_position": {
        "keywords": ["מזומן", "קאש", "שמרני", "מזומנים", "נזילות", "עתודה"],
        "desc": "Capital preservation / cash position"
    },
    "conviction_thesis": {
        "keywords": ["תזה", "אמונה", "שינוי סיפור", "סיפור השקעה", "תזת השקעה"],
        "desc": "Conviction / investment thesis"
    },
    "psychology_discipline": {
        "keywords": ["פסיכולוגיה", "משמעת", "רגש", "פחד", "תאוות בצע", "חמדנות", 
                     "סבלנות", "דיסציפלינה", "שליטה עצמית", "אמוציות"],
        "desc": "Psychology / discipline / emotions"
    },
    "tax_planning": {
        "keywords": ["מס", "מיסוי", "תכנון מס", "מס רווחי הון"],
        "desc": "Tax / planning"
    }
}

# First, get titles for video lookup
video_titles = {}
cur.execute("SELECT id, title FROM videos")
for vid, title in cur.fetchall():
    video_titles[vid] = title or "Unknown"

# Check each topic
for topic_name, topic_info in topics.items():
    keywords = topic_info["keywords"]
    desc = topic_info["desc"]
    
    # Build SQL condition
    like_clauses = []
    params = []
    for kw in keywords:
        like_clauses.append("text LIKE ?")
        params.append(f"%{kw}%")
    
    where_clause = " OR ".join(like_clauses)
    
    # Count matches
    cur.execute(f"SELECT COUNT(*) FROM transcript_chunks WHERE char_count > 100 AND ({where_clause})", params)
    count = cur.fetchone()[0]
    
    if count == 0:
        print(f"[{topic_name}] ({desc}): 0 matches\n")
        continue
    
    print(f"\n{'='*80}")
    print(f"[{topic_name}] ({desc}): {count} chunks match")
    print(f"{'='*80}")
    
    # Get matching chunks, limit to top 100 by char_count to find substantive ones
    cur.execute(f"""
        SELECT id, video_id, text, char_count 
        FROM transcript_chunks 
        WHERE char_count > 100 AND ({where_clause})
        ORDER BY char_count DESC
        LIMIT 100
    """, params)
    
    chunks = cur.fetchall()
    
    # Score by keyword density
    scored = []
    for c in chunks:
        chunk_id, vid, text, char_count = c
        score = 0
        for kw in keywords:
            score += len(re.findall(re.escape(kw), text, re.IGNORECASE))
        density = score / max(char_count, 1) * 1000  # per 1000 chars
        
        # Bonus for multiple different keyword types matching
        unique_kw = set()
        for kw in keywords:
            if re.search(re.escape(kw), text, re.IGNORECASE):
                unique_kw.add(kw.lower())
        diversity_bonus = len(unique_kw) * 0.5
        
        final_score = density * (1 + diversity_bonus)
        scored.append((final_score, density, score, char_count, chunk_id, vid, text))
    
    scored.sort(reverse=True)
    
    # Show top 5
    for idx, (final_score, density, kw_count, char_count, chunk_id, vid, text) in enumerate(scored[:5]):
        title = video_titles.get(vid, "Unknown")
        print(f"\n  --- Candidate #{idx+1} (Score: {final_score:.2f}, Density: {density:.2f}/1K, Hits: {kw_count}) ---")
        print(f"  Chunk ID: {chunk_id} | Video: {vid}")
        print(f"  Title: {title[:80]}")
        print(f"  Text excerpt: {text[:250]}")
    
    # Suggest pattern_type based on best chunk
    if scored:
        best = scored[0]
        final_score, density, kw_count, char_count, chunk_id, vid, text = best
        print(f"\n  >>> Suggested pattern_type: {topic_name}")
        print(f"  >>> Source chunk: {chunk_id} (video {vid})")
        
        # Try to derive reasoning from text
        print(f"  >>> Potential reasoning (derived from text):")
        # Get first sentence or meaningful segment
        sentences = re.split(r'[.!?\n]', text)
        meaningful = [s.strip() for s in sentences if len(s.strip()) > 15]
        for s in meaningful[:3]:
            print(f"      - {s[:150]}")

conn.close()
print("\n\nDone!")

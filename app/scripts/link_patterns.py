#!/usr/bin/env python3
"""
Source-link all 12 reasoning patterns to specific video transcript chunks.

For each reasoning pattern, this script:
1. Searches transcript_chunks.text using English AND Hebrew keywords
2. Finds the best matching chunk (highest keyword score)
3. Updates the pattern record with video_id, video_title, source_quote, chunk_id
4. Rebuilds FTS triggers/index afterward
5. Reports results
"""

import sqlite3
import re
import sys
from collections import defaultdict

DB_PATH = '/home/nuc/micha-stocks-app/data/micha.db'

# ============================================================
# Keyword definitions per pattern (English + Hebrew)
# ============================================================
PATTERN_KEYWORDS = {
    'trade_with_trend': {
        'en': ['trend is your friend', 'uptrend', 'downtrend', 'trend', 'trendline',
               'trend following', 'with the trend', 'falling knife', 'against the trend',
               'prevailing trend', 'trend direction', 'moving average', '200 ma',
               'higher high', 'higher low', 'lower high', 'lower low'],
        'he': ['מגמה', 'טרנד', 'עולה', 'יורד', 'ממוצע', '200', 'מגמת', 'המגמה',
               'עלייה', 'ירידה', 'תומך', 'מתנגד']
    },
    'entry_timing_dip': {
        'en': ['buy the dip', 'buying dip', 'buy dip', 'dip buying', 'falling knife',
               'catch a falling knife', 'buy the pullback', 'buying opportunity',
               'entry point', 'entry timing', 'when to buy', 'stabilize',
               'green candle', 'higher low', 'confirmation', 'wait for'],
        'he': ['דיפ', 'נפילה', 'קניה', 'הזדמנות', 'תחתית', 'קונים', 'לקנות',
               'צניחה', 'ירידה חדה', 'כניסה', 'לרדת']
    },
    'exit_strategy_stop_loss': {
        'en': ['stop loss', 'exit strategy', 'exit', 'sell', 'cut losses',
               '25%', 'max loss', 'take profit', 'cut your losses',
               'know when to sell', 'know when to exit', 'risk management',
               'protective stop', 'trailing stop', 'sell too early',
               'thesis broken', 'fundamentals changed'],
        'he': ['סטופ לוס', 'יציאה', 'למכור', 'הפסד', 'תפסיק להפסיד',
               'סטופ', 'לצאת', 'מכירה', 'הפסדים', 'לחתוך הפסדים',
               'אחוז', 'הגבלת הפסד']
    },
    'sell_in_may': {
        'en': ['sell in may', 'sell in may and go away', 'may',
               'seasonal', 'seasonality', 'summer', 'may effect',
               'may to october', 'summer months', 'may indicator',
               'sell in may strategy', 'seasonal pattern'],
        'he': ['מאי', 'למכור הכל', 'עונתיות', 'עונתי', 'קיץ',
               'מאי ולצאת', 'למכור במאי', 'חופשה', 'מיי']
    },
    'earnings_analysis': {
        'en': ['earnings', 'earnings report', 'earnings season', 'quarterly',
               'earnings beat', 'earnings miss', 'guidance', 'forward guidance',
               'conference call', 'no such thing as a good earnings report',
               'earnings trap', 'next quarter', 'revenue', 'profit',
               'eps', 'earnings per share', 'q1', 'q2', 'q3', 'q4',
               'financial report', 'results'],
        'he': ['דוח', 'דוחות', 'תוצאות', 'רווח', 'רבעון', 'הכנסות',
               'ריווחיות', 'דו"ח', 'רבע', 'הרבעון', 'תחזיות',
               'עונת הדוחות', 'עונת הרווחים']
    },
    'market_breadth': {
        'en': ['market breadth', 'breadth', 'advance decline', 'advance-decline',
               'above average', 'below average', 'percent of stocks',
               'stocks above ma', 'participation', 'market participation',
               'narrow market', 'divergence', 'breadth divergence',
               'rsp', 'equal weight', '62%', 'stocks red',
               'all-time high', 'new high', 'a/d line', 'advance decline line',
               'sector breadth'],
        'he': ['רוחב שוק', 'מדד', 'מניות', 'עולה', 'יורדות', 'רוחב',
               'אחוז המניות', 'מעל הממוצע', 'מתחת לממוצע', 'רוחב השוק',
               'דיברגנס', 'התבדרות', '62%', 'מניות אדומות']
    },
    'overtrading': {
        'en': ['overtrading', 'over trading', 'over-trade', 'quality vs quantity',
               'too many trades', 'trade quality', 'high conviction',
               '72%', 'cash is a position', 'best trade is no trade',
               'wait for setup', 'discipline', 'trading plan',
               'fomo', 'fear of missing out', 'chase', 'revenge trading',
               'silent killer', 'trading addiction'],
        'he': ['מסחר יתר', 'קנייה ומכירה', 'סוחר', 'הפסד', 'לסחור',
               'מסחר', 'איכות על כמות', 'המסחר', 'ממתין', 'סבלנות',
               'משמעת', 'תוכנית מסחר']
    },
    'sector_rotation': {
        'en': ['sector rotation', 'rotation', 'sector', 'sectors',
               'chips', 'software', 'energy', 'semi', 'semiconductor',
               'great rotation', 'relative strength', 'sector analysis',
               'money flow', 'growth to value', 'yield curve',
               'xlk', 'xle', 'xlv', 'xli', 'xlf', 'xlp', 'xlu', 'xlre',
               'sector performance', 'sector etf', 'sector strength',
               '89%', '100%'],
        'he': ['סקטור', 'רוטציה', 'שבבים', 'אנרגיה', 'תוכנה', 'סקטורים',
               'רוטציית סקטורים', 'מגזר', 'מגזרים', 'שבב', 'נפט',
               'אנרגיה ירוקה', 'סקטור הטכנולוגיה', 'סקטור הפיננסים']
    },
    'position_sizing': {
        'en': ['position size', 'position sizing', 'position', 'sizing',
               'portfolio allocation', 'allocation', 'conviction',
               'diversify', 'diversification', 'risk per trade',
               'percent', 'percentage', 'portfolio weight',
               'core position', 'swing trade', 'day trade',
               '1% risk', '2% risk', 'tier', 'three tier', '3 tier',
               'community tier', 'involvement level', 'stock portfolio',
               'portfolio management', 'risk management'],
        'he': ['תיק', 'פוזיציה', 'אחוז', 'השקעה', 'פיזור', 'גודל פוזיציה',
               'הקצאה', 'גיוון', 'תיק השקעות', 'ניהול תיק', 'סיכון']
    },
    'compounding_math': {
        'en': ['compounding', 'compound', 'compound interest', 'time in market',
               'time in the market beats timing', 'consistent',
               'small amounts', 'life-changing wealth', 'wealth',
               '200 shekels per month', '12 million',
               'exponential', 'growth', 'time horizon', 'long term',
               'invest regularly', 'dollar cost averaging', 'dca',
               'miracle of compounding', 'snowball', 'power of compounding',
               'year after year', 'over time', 'retirement'],
        'he': ['ריבית', 'דריבית', 'כפל', 'זמן', 'שנה', 'חודש',
               'ריבית דריבית', 'הרכבה', 'צמיחה', 'עושר', 'השקעה קבועה',
               'חודשי', 'שקלים', '200 שקלים', '12 מיליון', 'עתיד',
               'כסף', 'חיסכון', 'פנסיה']
    },
    'fear_greed_index': {
        'en': ['fear and greed', 'fear & greed', 'fear index', 'greed index',
               'vix', 'volatility', 'market sentiment', 'sentiment',
               'investor sentiment', 'retail sentiment',
               'be greedy when others are fearful', 'fearful when others are greedy',
               'weekly buzz', 'buzz index', 'market fear', 'panic',
               'extreme fear', 'extreme greed', 'bullish', 'bearish',
               'caution', 'opportunity', 'warren buffett', 'smart money'],
        'he': ['פחד', 'חמדנות', 'ויקס', 'VIX', 'סנטימנט', 'באזז',
               'מדד הפחד', 'מדד החמדנות', 'שוק', 'תחושת שוק',
               'אופטימיות', 'פסימיות', 'פוחד', 'להיות חמדן', 'באזז אינדקס',
               'פוזה', 'שוריים', 'דוביים', 'משקיעים']
    },
    'simple_chart_reading': {
        'en': ['simple chart', 'chart reading', 'reading charts', 'price action',
               'support', 'resistance', 'support and resistance',
               'trendline', 'moving average', 'moving averages',
               '150 ma', '200 ma', 'volume', 'volume confirmation',
               'simplicity', 'chart pattern', 'technical analysis',
               'price', 'trend direction', 'key level', 'breakout',
               'splitting the red sea', 'not like splitting the red sea',
               'simply reading charts', 'read charts simply'],
        'he': ['גרף', 'תרשים', 'תמיכה', 'התנגדות', 'ממוצע', 'מחיר',
               'גרפים', 'תרשים פשוט', 'קריאת גרפים', 'תמיכות', 'התנגדויות',
               'ממוצע נע', 'פשוט לקרוא גרפים', 'ניתוח טכני']
    }
}


def clean_text(text):
    """Remove repeated segments common in auto-generated captions."""
    if not text:
        return text
    parts = re.split(r'(?<=[.!?])\s+', text)
    seen = set()
    unique = []
    for p in parts:
        key = p[:60].strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return ' '.join(unique)


def score_chunk(chunk_text, keywords_en, keywords_he):
    """
    Score a chunk text against keyword lists.
    Returns a score (int) based on number of keyword hits.
    """
    text_lower = chunk_text.lower()
    score = 0
    matched = set()

    for kw in keywords_en:
        if kw.lower() in text_lower:
            score += 2
            matched.add(kw)

    for kw in keywords_he:
        if kw in chunk_text:
            score += 3
            matched.add(kw)

    return score, matched


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Add chunk_id column if needed
    cursor.execute("PRAGMA table_info(reasoning_patterns)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'chunk_id' not in cols:
        print("Adding chunk_id column to reasoning_patterns...")
        cursor.execute("ALTER TABLE reasoning_patterns ADD COLUMN chunk_id INTEGER REFERENCES transcript_chunks(id)")
        conn.commit()

    # Save FTS triggers and drop them temporarily (they block updates due to column mismatch)
    cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'patterns_ai'")
    trigger_ai = cursor.fetchone()
    cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'patterns_ad'")
    trigger_ad = cursor.fetchone()
    cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'patterns_au'")
    trigger_au = cursor.fetchone()

    if trigger_ai:
        cursor.execute("DROP TRIGGER IF EXISTS patterns_ai")
    if trigger_ad:
        cursor.execute("DROP TRIGGER IF EXISTS patterns_ad")
    if trigger_au:
        cursor.execute("DROP TRIGGER IF EXISTS patterns_au")
    conn.commit()
    print("Dropped FTS triggers for update phase.")

    # Get all patterns
    cursor.execute("SELECT id, pattern_type, reasoning FROM reasoning_patterns ORDER BY id")
    patterns = cursor.fetchall()

    print(f"Found {len(patterns)} reasoning patterns\n")
    print("=" * 96)
    print(f"{'#':3s} {'Pattern':25s} | {'Linked Video':40s} | {'Chunk':6s} | {'Score':5s}")
    print("=" * 96)

    results = []

    for pat in patterns:
        pid = pat['id']
        ptype = pat['pattern_type']
        reasoning = pat['reasoning'] or ''

        if ptype not in PATTERN_KEYWORDS:
            print(f"  WARNING: No keywords defined for pattern type '{ptype}'")
            continue

        kw = PATTERN_KEYWORDS[ptype]
        keywords_en = kw['en']
        keywords_he = kw['he']

        # Add meaningful words from reasoning as extra English keywords
        reasoning_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', reasoning.lower()))
        extra_en = [w for w in reasoning_words
                    if w not in ('the', 'and', 'for', 'are', 'not', 'that', 'this',
                                 'with', 'from', 'have', 'has', 'his', 'she', 'its',
                                 'was', 'but', 'all', 'can', 'don', 'out', 'you')][:10]
        all_en = keywords_en + extra_en

        # Search through ALL transcript chunks
        cursor.execute("""
            SELECT tc.id, tc.video_id, tc.text, v.title as video_title
            FROM transcript_chunks tc
            JOIN videos v ON tc.video_id = v.id
            ORDER BY tc.id
        """)
        chunks = cursor.fetchall()

        best_chunk = None
        best_score = 0
        best_matched = set()

        for chunk in chunks:
            chunk_text = chunk['text'] or ''
            chunk_text_clean = clean_text(chunk_text)
            score, matched = score_chunk(chunk_text_clean, all_en, keywords_he)

            if score > best_score:
                best_score = score
                best_chunk = chunk
                best_matched = matched

        # Fallback: try with just original keywords
        if best_score == 0:
            for chunk in chunks:
                chunk_text = chunk['text'] or ''
                chunk_text_clean = clean_text(chunk_text)
                score, matched = score_chunk(chunk_text_clean, keywords_en, keywords_he)
                if score > best_score:
                    best_score = score
                    best_chunk = chunk
                    best_matched = matched

        # Update pattern record if we found a match
        if best_chunk and best_score > 0:
            chunk_id = best_chunk['id']
            video_id = best_chunk['video_id']
            video_title = best_chunk['video_title'] or video_id
            chunk_text = best_chunk['text'] or ''

            clean_chunk_text = clean_text(chunk_text)
            source_quote = clean_chunk_text[:500]

            new_title = f"{video_title} [chunk_{chunk_id}]"

            cursor.execute("""
                UPDATE reasoning_patterns
                SET video_id = ?,
                    video_title = ?,
                    source_quote = ?,
                    chunk_id = ?
                WHERE id = ?
            """, (video_id, new_title, source_quote, chunk_id, pid))

            matched_summary = ', '.join(list(best_matched)[:6])

            print(f"{pid:<3d} {ptype:25s} | {new_title[:40]:40s} | {chunk_id:<6d} | {best_score:<5d}")
        else:
            print(f"{pid:<3d} {ptype:25s} | {'--- NO MATCH FOUND ---':40s} | {'N/A':6s} | 0")

        results.append({
            'pattern_id': pid,
            'pattern_type': ptype,
            'chunk_id': best_chunk['id'] if best_chunk else None,
            'video_id': best_chunk['video_id'] if best_chunk else None,
            'video_title': best_chunk['video_title'] if best_chunk else None,
            'score': best_score,
            'matched_keywords': list(best_matched)[:20] if best_matched else []
        })

    conn.commit()
    print("\n" + "=" * 96)

    # Rebuild FTS index
    print("\nRebuilding FTS index...")
    cursor.execute("DELETE FROM patterns_fts")
    cursor.execute("""
        INSERT INTO patterns_fts(rowid, pattern_type, trigger_context, reasoning, conditions, source_quote, video_title)
        SELECT id, pattern_type, trigger_context, reasoning, conditions, source_quote, video_title
        FROM reasoning_patterns
    """)
    conn.commit()

    # Recreate FTS triggers
    if trigger_ai:
        cursor.execute(trigger_ai[0])
    if trigger_ad:
        cursor.execute(trigger_ad[0])
    if trigger_au:
        cursor.execute(trigger_au[0])
    conn.commit()
    print("FTS triggers recreated and index rebuilt.")

    # Summary
    print("\n" + "=" * 96)
    print("SUMMARY")
    print("=" * 96)

    matches = [r for r in results if r['score'] > 0]
    no_matches = [r for r in results if r['score'] == 0]
    print(f"Linked: {len(matches)}/{len(patterns)} patterns")
    print(f"No match found: {len(no_matches)}/{len(patterns)} patterns")

    if no_matches:
        print("\nUnlinked patterns:")
        for r in no_matches:
            print(f"  - {r['pattern_type']} (ID: {r['pattern_id']})")

    print("\nDetailed results:")
    for r in results:
        print(f"\n--- {r['pattern_type']} (ID: {r['pattern_id']}) ---")
        if r['score'] > 0:
            print(f"  Chunk ID: {r['chunk_id']}")
            print(f"  Video ID: {r['video_id']}")
            print(f"  Video Title: {r['video_title']}")
            print(f"  Score: {r['score']}")
            print(f"  Matched keywords: {', '.join(r['matched_keywords'][:15])}")
        else:
            print(f"  [NO MATCH FOUND]")

    conn.close()

    match_count = len(matches)
    total = len(patterns)
    print(f"\n{'=' * 96}")
    print(f"RESULT: {match_count}/{total} patterns linked to transcript chunks.")

    return results


if __name__ == '__main__':
    results = main()
    sys.exit(0)

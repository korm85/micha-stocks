#!/usr/bin/env python3
"""
Seed the database with sample reasoning patterns for development/testing.
This allows us to build the query pipeline while the YouTube IP block clears.
"""

import json
import os
import sqlite3
import sys

# Add scripts dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from scraper import get_db, save_video, save_chunks, mark_pending, mark_downloaded

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "micha.db")

# Sample reasoning patterns that Micha would teach
# These are synthetic but representative of his content style

SAMPLE_PATTERNS = [
    {
        "pattern_type": "valuation",
        "trigger_context": "When analyzing a growth stock with high PE ratio",
        "reasoning": "Micha evaluates growth stocks by looking at PEG ratio (PE / earnings growth). If PEG < 1.5, the stock is reasonably valued despite high PE. He checks if growth is accelerating or decelerating — decelerating growth with high PE is a red flag.",
        "confidence_signal": "conditional",
        "conditions": "PEG < 1.5 AND revenue growth > 15% YoY. If growth is decelerating, reduce position size.",
        "source_quote": "A high PE isn't scary if the growth justifies it. The moment growth slows and PE stays high, get out.",
        "video_id": "VID001"
    },
    {
        "pattern_type": "entry_timing",
        "trigger_context": "When a quality stock drops 10-20% on no specific bad news",
        "reasoning": "Micha looks for 'buy the dip' opportunities on fundamentally strong stocks. He waits for the selling to exhaust — looks for 2-3 consecutive days of lower volume as price stabilizes. He doesn't try to catch the falling knife; he waits for confirmation (green candle, higher low).",
        "confidence_signal": "bullish",
        "conditions": "Drop >10%, no fundamental news, volume decreasing, price forms a higher low on daily chart.",
        "source_quote": "The best time to buy quality is when everyone else is panic selling — but only after the panic subsides.",
        "video_id": "VID002"
    },
    {
        "pattern_type": "risk",
        "trigger_context": "When market is at all-time highs",
        "reasoning": "All-time highs are not a sell signal by themselves. Micha analyzes: 1) Are we in a momentum-driven rally or fundamentals-driven? 2) Is breadth confirming the rally (more stocks participating)? 3) Are investors overly euphoric? He reduces position size when VIX is extremely low and everyone is bullish.",
        "confidence_signal": "neutral",
        "conditions": "Check VIX level (< 12 is caution), advance-decline line, percentage of stocks above 50-day MA. If all euphoric, take some profits.",
        "source_quote": "I don't sell because of highs, I sell when the story changes. But I do take some off the table when everyone's celebrating.",
        "video_id": "VID003"
    },
    {
        "pattern_type": "earnings_analysis",
        "trigger_context": "Analyzing stocks before and after earnings reports",
        "reasoning": "Micha's approach: 1) Don't trade earnings — too much uncertainty. 2) Instead, listen to the conference call for guidance, not just the numbers. 3) A beat with lowered guidance is a sell signal. 4) A miss with raised guidance is a buy signal. 5) Watch insider buying/ selling after earnings.",
        "confidence_signal": "conditional",
        "conditions": "Only act after the earnings call, not before. Focus on forward guidance > past results. Insider transactions post-earnings are key.",
        "source_quote": "Earnings are a trap for gamblers. The money is in what they say about next quarter, not last quarter.",
        "video_id": "VID004"
    },
    {
        "pattern_type": "sector_rotation",
        "trigger_context": "When Fed signals interest rate policy changes",
        "reasoning": "Micha tracks sector rotation around rate cycles. Rate cuts → growth stocks and tech benefit first. Rates stable → value and dividend stocks perform. Rate hikes → financials and energy benefit. He watches the 2-year yield vs 10-year yield (yield curve) as a recession predictor.",
        "confidence_signal": "bullish",
        "conditions": "Inverted yield curve → prepare for recession, move to defensive sectors. Yield curve steepening → recovery phase, buy cyclical.",
        "source_quote": "The Fed is the 800-pound gorilla. Don't fight the Fed — rotate with the rate cycle, not against it.",
        "video_id": "VID005"
    },
    {
        "pattern_type": "deal_analysis",
        "trigger_context": "Evaluating companies involved in M&A or major partnerships",
        "reasoning": "Micha analyzes deals by: 1) Is the acquirer paying with stock (dilutive, less confident) or cash (confident)? 2) What's the strategic fit — does this make the company stronger? 3) Is the deal accretive to earnings within 12 months? 4) Watch for competing bids. For partnerships, look at revenue-sharing terms.",
        "confidence_signal": "bullish",
        "conditions": "Cash deal + strategic fit + accretive within 12 months = positive. Stock deal with no clear synergies = skeptical.",
        "source_quote": "I love cash acquisitions — it tells me management is confident enough to put their money where their mouth is.",
        "video_id": "VID006"
    },
    {
        "pattern_type": "exit_strategy",
        "trigger_context": "When a stock you own drops 20% from purchase price",
        "reasoning": "Micha uses a structured approach: 1) Re-evaluate the original thesis — is it still intact? 2) If thesis is broken (fundamentals changed), cut losses immediately. 3) If thesis is intact but market is irrational, consider averaging down gradually. 4) Set a mental stop at 25% max loss — no exceptions.",
        "confidence_signal": "conditional",
        "conditions": "If original thesis invalidated → sell immediately. If thesis intact → hold or average down. Hard stop at 25% loss.",
        "source_quote": "Your first loss is your best loss. Don't let a 20% drop turn into a 50% drop because you refused to admit you were wrong.",
        "video_id": "VID007"
    },
    {
        "pattern_type": "position_sizing",
        "trigger_context": "Building a portfolio allocation for individual stocks",
        "reasoning": "Micha advocates: 1) Maximum 10-15 positions for proper monitoring. 2) No single position > 10% of portfolio. 3) Core positions (5-7% each) for high-conviction plays. 4) Satellite positions (2-3% each) for tactical trades. 5) Cash reserve of 10-20% for opportunities.",
        "confidence_signal": "neutral",
        "conditions": "Rebalance when any position exceeds 12% of portfolio. Add to positions that are working, cut ones that aren't.",
        "source_quote": "Concentration builds wealth, diversification preserves it. I keep my best ideas big and my experiments small.",
        "video_id": "VID008"
    },
    {
        "pattern_type": "market_regime",
        "trigger_context": "Identifying if we're in a bull or bear market",
        "reasoning": "Micha defines market regime by 3 indicators: 1) S&P 500 vs 200-day moving average. 2) Percentage of stocks above 50-day MA. 3) High-yield credit spreads. Bull = prices above 200-day, 60%+ stocks above 50-day, tight credit spreads. Bear = opposite. He doesn't try to predict the regime change — he waits for confirmation.",
        "confidence_signal": "neutral",
        "conditions": "Above 200-day MA + broad participation + tight credit = bullish posture. Two of three reversed = defensive.",
        "source_quote": "I don't predict markets, I react to them. Let the price tell you what regime we're in, don't guess.",
        "video_id": "VID009"
    },
    {
        "pattern_type": "general",
        "trigger_context": "How to think about stock market investing overall",
        "reasoning": "Micha's core philosophy: 1) Stocks are ownership in businesses, not trading cards. 2) Focus on companies you understand (circle of competence). 3) Price is what you pay, value is what you get. 4) The best time to invest was yesterday — time in the market beats timing the market. 5) Keep emotions out — have a system and follow it.",
        "confidence_signal": "bullish",
        "conditions": "Long-term investing > short-term trading for most people. Have a thesis for every position. Review quarterly, not daily.",
        "source_quote": "The stock market is a device for transferring money from the impatient to the patient. Be patient.",
        "video_id": "VID010"
    },
]

def seed():
    conn = get_db(DB_PATH)
    
    # Add sample videos
    for i, pattern in enumerate(SAMPLE_PATTERNS):
        vid_id = pattern["video_id"]
        title = f"Sample: {pattern['pattern_type'].replace('_', ' ').title()} Principles"
        
        save_video(conn, vid_id, title, 600 + i * 30, f"202605{i+1:02d}")
        mark_pending(conn, vid_id)
        
        # Add a mock transcript chunk
        save_chunks(conn, vid_id, pattern["source_quote"] * 10)
        
        # Simulate a downloaded state for these sample videos
        mark_downloaded(conn, vid_id)
    
    # Add reasoning patterns
    conn.executemany("""
        INSERT INTO reasoning_patterns 
            (video_id, pattern_type, trigger_context, reasoning, confidence_signal, conditions, source_quote)
        VALUES 
            (:video_id, :pattern_type, :trigger_context, :reasoning, :confidence_signal, :conditions, :source_quote)
    """, SAMPLE_PATTERNS)
    
    conn.commit()
    
    # Verify
    cur = conn.execute("SELECT COUNT(*) FROM videos")
    print(f"Videos: {cur.fetchone()[0]}")
    cur = conn.execute("SELECT COUNT(*) FROM transcript_chunks")
    print(f"Transcript chunks: {cur.fetchone()[0]}")
    cur = conn.execute("SELECT COUNT(*) FROM reasoning_patterns")
    print(f"Reasoning patterns: {cur.fetchone()[0]}")
    
    # Show pattern types
    cur = conn.execute("SELECT pattern_type, COUNT(*) FROM reasoning_patterns GROUP BY pattern_type")
    for row in cur:
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()
    print(f"\nDatabase: {DB_PATH}")

if __name__ == "__main__":
    seed()

#!/usr/bin/env python3.14
"""
Seed the KB with real reasoning patterns extracted from Micha's actual channel content.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "micha.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Clear old fake patterns
conn.execute('DELETE FROM reasoning_patterns')
print('Old patterns cleared')

# Real patterns from Micha's actual channel content (video titles, website, community page)
patterns = [
    {
        'pattern_type': 'trade_with_trend',
        'trigger_context': 'When considering any trade, long or short',
        'reasoning': "Micha's #1 rule: \"The trend is your friend till the end.\" Always trade with the prevailing trend. For long positions, the stock must be in an uptrend. Don't try to catch falling knives - wait for stabilization and confirmation. For shorts, the stock must be in a downtrend. Going against the trend is trading against the probabilities.",
        'confidence_signal': 'bullish',
        'conditions': 'Stock must be above key moving averages (150/200 MA) for long positions. Below = need exceptional reason to buy.',
        'source_quote': 'Top 5 Rules video: "סוחרים עם הטרנד — the trend is your friend till the end"',
        'video_title': 'Why People Lose Money? 5 Rules You Must Know'
    },
    {
        'pattern_type': 'entry_timing_dip',
        'trigger_context': 'When a quality stock drops 10-20% and you want to buy the dip',
        'reasoning': "Micha has 4 specific rules for buying dips: 1) Wait for the stock to stabilize - don't catch a falling knife. 2) Look for higher lows forming. 3) Check if volume is decreasing as price stabilizes (selling exhaustion). 4) Wait for a green candle confirmation before entering. Don't try to time the exact bottom.",
        'confidence_signal': 'bullish',
        'conditions': 'Drop >10%, no fundamental news breaking, volume declining, price forms higher low on daily chart. Wait for green candle confirmation.',
        'source_quote': 'Missed the Dip? 4 Rules for the Next Dip',
        'video_title': 'Missed the Dip? 4 Rules for the Next Dip'
    },
    {
        'pattern_type': 'exit_strategy_stop_loss',
        'trigger_context': 'When a stock you own drops and you are deciding whether to hold or sell',
        'reasoning': "Micha emphasizes that knowing when to exit is more important than knowing when to enter. Professional traders have clear exit rules. The 25% max loss rule is non-negotiable. If the original thesis is broken (fundamentals changed), cut losses immediately, no hesitation. If thesis is intact but market is irrational, consider averaging down gradually but with strict limits.",
        'confidence_signal': 'conditional',
        'conditions': 'Re-evaluate the original thesis. If thesis broken -> sell immediately. If thesis intact -> hold or average down with strict limits. Hard stop at 25% max loss.',
        'source_quote': 'The Mistake That Makes You Sell Too Early + Stop Loss videos',
        'video_title': 'The Mistake That Makes You Sell Too Early'
    },
    {
        'pattern_type': 'sell_in_may',
        'trigger_context': 'When approaching seasonal weak periods (May-October)',
        'reasoning': 'Micha addresses the "Sell in May and Go Away" strategy with a nuanced view. Instead of blindly selling, he recommends: 1) Evaluate current market conditions - are we in a confirmed uptrend? 2) Reduce position size rather than going fully to cash. 3) Keep a watchlist of stocks to buy if they pull back. 4) Do not let seasonal biases override technical signals.',
        'confidence_signal': 'neutral',
        'conditions': 'If market is in strong uptrend with broad participation -> stay invested with reduced size. If market shows weakness -> increase cash position.',
        'source_quote': 'Analysis video responding to Sell in May strategy',
        'video_title': 'Sell in May and Go Away? Analysis'
    },
    {
        'pattern_type': 'earnings_analysis',
        'trigger_context': 'Before and after earnings reports',
        'reasoning': "Micha's rule: \"There is no such thing as a good earnings report.\" The market is smarter than everyone - a beat with lowered guidance is a sell signal, a miss with raised guidance can be a buy. Never trade earnings (too much uncertainty). Listen to the conference call for forward guidance, not just the numbers. Watch insider transactions after earnings.",
        'confidence_signal': 'conditional',
        'conditions': "Do not enter positions right before earnings. Wait for the market reaction (24-48 hours). Focus on forward guidance, not past results. A beat with lowered guidance = sell. A miss with raised guidance = buy candidate.",
        'source_quote': 'There is No Such Thing as a Good Earnings Report',
        'video_title': 'The Truth About Earnings Season'
    },
    {
        'pattern_type': 'market_breadth',
        'trigger_context': 'When the market is at all-time highs but breadth is narrow',
        'reasoning': 'Micha warns about divergences: when the market hits new highs but most stocks are not participating (62% of stocks are red while indices are green). This breadth divergence is a warning sign. He analyzes: percentage of stocks above 50/200-day MA, advance-decline line, and sector participation. Narrow rallies are fragile - they can reverse quickly.',
        'confidence_signal': 'neutral',
        'conditions': 'If indices are up but less than 50% of stocks are above their 50-day MA -> CAUTION. If A/D line is diverging from price -> potential reversal ahead.',
        'source_quote': 'Market at All-Time High But 62% of Stocks Are Red',
        'video_title': 'Market at All-Time High - 62% Stocks Red'
    },
    {
        'pattern_type': 'overtrading',
        'trigger_context': 'When you feel the urge to trade frequently or take every opportunity',
        'reasoning': 'Micha warns: 72% of traders lose money this way - overtrading. Trading is not about how many trades you make, but the quality of your setups. Wait for your specific criteria to be met. Cash is a position - sometimes the best trade is no trade. Micha recommends focusing on high-conviction setups rather than trading daily noise.',
        'confidence_signal': 'bullish',
        'conditions': 'Only trade when your specific entry criteria are met. If unsure, stay in cash. Quality over quantity of trades. Track your win rate and average return per trade.',
        'source_quote': '72% of Traders Lose Money This Way - Overtrading',
        'video_title': 'Overtrading - The Silent Killer'
    },
    {
        'pattern_type': 'sector_rotation',
        'trigger_context': 'When Fed signals interest rate changes or economic regime shifts',
        'reasoning': 'Micha tracks the great rotation between sectors. Currently observing: chips outperforming while software lags, energy showing strength, rate-sensitive sectors rotating. Key indicators: 1) Relative strength between sectors. 2) Money flow from growth to value (or vice versa). 3) Yield curve movements. 4) Fed policy trajectory. Follow where money is flowing.',
        'confidence_signal': 'bullish',
        'conditions': 'Rate cuts -> growth/tech first. Rates stable -> value/dividends. Rate hikes -> financials/energy. Inverted yield curve -> prepare for defensive positioning. Follow relative strength.',
        'source_quote': 'The Great Rotation: 89% of Chips Above Average, 100% of Software Below',
        'video_title': 'The Great Rotation Analysis'
    },
    {
        'pattern_type': 'position_sizing',
        'trigger_context': 'Building and managing a stock portfolio',
        'reasoning': "Micha's community structure reveals his approach: 3 tiers based on involvement level. Core long-term positions for steady growth, swing trades for medium-term opportunities, and limited day trades for advanced members. Key principles: 1) Diversify across sectors. 2) Position size matches conviction AND risk tolerance. 3) Maintain cash reserve for opportunities. 4) Use checklist 20 for short-term evaluation.",
        'confidence_signal': 'neutral',
        'conditions': 'Long-term investor -> focus on core positions (5-7% each). Swing trader -> add tactical positions (2-3% each). Day trader -> strict risk limits per trade. Keep 10-20% cash reserve.',
        'source_quote': 'Community tiers analysis from Micha.Stocks website',
        'video_title': 'Micha Stocks Community Course'
    },
    {
        'pattern_type': 'compounding_math',
        'trigger_context': 'When evaluating long-term wealth building vs short-term trading',
        'reasoning': 'Micha emphasizes the power of compounding: consistent small amounts grow to life-changing wealth over time. Time IN the market beats timing the market. He advocates for education-first approach - learn to read charts simply, understand risk management, then let time and compounding work.',
        'confidence_signal': 'bullish',
        'conditions': 'Consistent monthly contributions > trying to time entries. Focus on understanding the math of compounding. Education is the best investment you can make.',
        'source_quote': '200 Shekels/Month = 12 Million? The Math That Changes Everything',
        'video_title': 'Compounding Wealth Formula'
    },
    {
        'pattern_type': 'fear_greed_index',
        'trigger_context': 'When VIX is elevated or market sentiment is extreme',
        'reasoning': 'Micha tracks the Fear & Greed index, VIX levels, and market sentiment. When VIX is extremely low and everyone is bullish -> caution. When VIX spikes and fear is extreme -> opportunity. Uses the Weekly Buzz Index to gauge retail sentiment. Be greedy when others are fearful, fearful when others are greedy (applied with technical confirmation).',
        'confidence_signal': 'conditional',
        'conditions': 'VIX below 12 + extreme bullish sentiment -> take profits, reduce exposure. VIX above 30 + panic -> look for buying opportunities with technical confirmation. Watch the Weekly Buzz Index.',
        'source_quote': 'Weekly Buzz Index + VIX analysis from channel',
        'video_title': 'Fear Index and Market Sentiment Analysis'
    },
    {
        'pattern_type': 'simple_chart_reading',
        'trigger_context': 'When analyzing charts for trade opportunities',
        'reasoning': 'Micha\'s core teaching: "Reading charts should not be like splitting the Red Sea." Simplified chart analysis with: 1) Price action and trend direction. 2) Key support and resistance levels. 3) Volume confirmation. 4) Moving averages (150/200 MA as key references). Simplicity over complexity.',
        'confidence_signal': 'bullish',
        'conditions': 'Price + volume + trend + key MAs are sufficient for most decisions. Do not clutter charts with unnecessary indicators. Focus on clear setups.',
        'source_quote': 'Micha\'s website bio: "פשוט לקרוא גרפים" - Simple Chart Reading course',
        'video_title': 'Simply Reading Charts Course'
    },
]

# Insert real patterns
for p in patterns:
    conn.execute('''INSERT INTO reasoning_patterns 
        (pattern_type, trigger_context, reasoning, confidence_signal, conditions, source_quote, video_title)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (p['pattern_type'], p['trigger_context'], p['reasoning'],
         p['confidence_signal'], p['conditions'], p['source_quote'], p['video_title']))

conn.commit()

# Verify
cur = conn.execute('SELECT id, pattern_type, confidence_signal FROM reasoning_patterns ORDER BY id')
rows = cur.fetchall()
print(f'Inserted {len(rows)} REAL patterns:')
for r in rows:
    icon = {'bullish': '🟢', 'conditional': '🟡', 'neutral': '⚪', 'bearish': '🔴'}.get(r['confidence_signal'], '⚪')
    print(f'  [{r["id"]}] {icon} {r["pattern_type"]}')

conn.close()
print('\nKB seeded with real patterns from Micha\'s actual channel content!')

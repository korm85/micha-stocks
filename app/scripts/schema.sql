-- Micha Stocks Knowledge Base Schema

-- Layer 1: Raw video metadata
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,                -- YouTube video ID
    title TEXT NOT NULL,
    duration_seconds INTEGER,
    upload_date TEXT,
    url TEXT,
    downloaded_at TEXT DEFAULT (datetime('now')),
    transcript_language TEXT DEFAULT 'en'
);

-- Layer 1: Transcript chunks (200-500 word overlapping chunks)
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL REFERENCES videos(id),
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_count INTEGER DEFAULT 0,
    UNIQUE(video_id, chunk_index)
);

-- FTS5 full-text search on chunks
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content=transcript_chunks,
    content_rowid=id
);

-- Layer 2: Extracted reasoning patterns (the brain)
CREATE TABLE IF NOT EXISTS reasoning_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT REFERENCES videos(id),
    pattern_type TEXT NOT NULL,          -- 'valuation', 'risk', 'entry_timing', 'sector_rotation',
                                        -- 'earnings_analysis', 'market_regime', 'deal_analysis',
                                        -- 'exit_strategy', 'position_sizing', 'general'
    trigger_context TEXT,               -- What situation triggers this reasoning?
    reasoning TEXT NOT NULL,             -- Micha's reasoning logic
    confidence_signal TEXT,              -- 'bullish', 'bearish', 'neutral', 'conditional'
    conditions TEXT,                     -- Conditions he attaches
    source_quote TEXT,                   -- Direct quote for reference
    created_at TEXT DEFAULT (datetime('now'))
);

-- FTS5 for reasoning patterns
CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(
    pattern_type, trigger_context, reasoning, conditions,
    content=reasoning_patterns,
    content_rowid=id
);

-- Scraper checkpoint tracking
CREATE TABLE IF NOT EXISTS scraper_state (
    video_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'downloaded', 'failed'
    error TEXT,
    attempts INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Tables to keep FTS5 in sync with content changes
-- Triggers for transcript_chunks
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON transcript_chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON transcript_chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON transcript_chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

-- Triggers for reasoning_patterns
CREATE TRIGGER IF NOT EXISTS patterns_ai AFTER INSERT ON reasoning_patterns BEGIN
    INSERT INTO patterns_fts(rowid, pattern_type, trigger_context, reasoning, conditions)
    VALUES (new.id, new.pattern_type, new.trigger_context, new.reasoning, new.conditions);
END;

CREATE TRIGGER IF NOT EXISTS patterns_ad AFTER DELETE ON reasoning_patterns BEGIN
    INSERT INTO patterns_fts(patterns_fts, rowid, pattern_type, trigger_context, reasoning, conditions)
    VALUES('delete', old.id, old.pattern_type, old.trigger_context, old.reasoning, old.conditions);
END;

CREATE TRIGGER IF NOT EXISTS patterns_au AFTER UPDATE ON reasoning_patterns BEGIN
    INSERT INTO patterns_fts(patterns_fts, rowid, pattern_type, trigger_context, reasoning, conditions)
    VALUES('delete', old.id, old.pattern_type, old.trigger_context, old.reasoning, old.conditions);
    INSERT INTO patterns_fts(rowid, pattern_type, trigger_context, reasoning, conditions)
    VALUES (new.id, new.pattern_type, new.trigger_context, new.reasoning, new.conditions);
END;

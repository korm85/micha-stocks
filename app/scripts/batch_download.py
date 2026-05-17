#!/usr/bin/env python3.14
"""
Batch download Micha's video transcripts via Tor proxy.
Runs slowly to avoid rate limits.
"""
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "micha.db")
PROXY = "socks5://127.0.0.1:9050"
DELAY = 3.0  # Seconds between requests
MAX_PER_BATCH = 50  # Videos per run

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY, title TEXT, duration_seconds INTEGER,
            upload_date TEXT, url TEXT, downloaded_at TEXT,
            transcript_language TEXT DEFAULT 'iw'
        );
        CREATE TABLE IF NOT EXISTS scraper_state (
            video_id TEXT PRIMARY KEY, status TEXT DEFAULT 'pending',
            error TEXT, attempts INTEGER DEFAULT 0, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS transcript_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL, chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL, char_count INTEGER DEFAULT 0,
            UNIQUE(video_id, chunk_index)
        );
    """)
    return conn

def ensure_video(conn, vid, title, duration):
    conn.execute("""INSERT OR IGNORE INTO videos 
        (id, title, duration_seconds, url) VALUES (?, ?, ?, ?)""",
        (vid, title, duration, f"https://youtube.com/watch?v={vid}"))
    conn.execute("""INSERT OR IGNORE INTO scraper_state 
        (video_id, status, updated_at) VALUES (?, 'pending', datetime('now'))""",
        (vid,))
    conn.commit()

def get_pending(conn, limit=50):
    cur = conn.execute("""
        SELECT v.id, v.title FROM videos v
        LEFT JOIN scraper_state s ON v.id = s.video_id
        WHERE s.status IS NULL OR s.status = 'pending'
        ORDER BY RANDOM()
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cur.fetchall()]

def download_transcript(api, video_id, title):
    try:
        transcript_list = api.list(video_id)
        t = transcript_list.find_transcript(['iw', 'he', 'en'])
        fetched = t.fetch()
        text = ' '.join(seg.text for seg in fetched)
        return text, None, t.language_code
    except Exception as e:
        return None, str(e)[:200], None

def save_chunks(conn, video_id, full_text):
    words = full_text.split()
    chunk_size = 250
    overlap = 50
    chunks_data = []
    start = 0
    chunk_idx = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)
        chunks_data.append((video_id, chunk_idx, chunk_text, len(chunk_text)))
        chunk_idx += 1
        start += chunk_size - overlap
    
    conn.executemany("""INSERT OR REPLACE INTO transcript_chunks 
        (video_id, chunk_index, text, char_count) VALUES (?, ?, ?, ?)""",
        chunks_data)
    conn.commit()
    return len(chunks_data)

def main():
    conn = get_db()
    
    # First, load video list if available
    videos_file = "/tmp/micha_videos.json"
    if os.path.exists(videos_file):
        with open(videos_file) as f:
            video_list = json.load(f)
        count = 0
        for v in video_list:
            ensure_video(conn, v['id'], v.get('title', '?'), v.get('duration', 0))
            count += 1
        print(f"Ensured {count} videos in DB")
    
    # Get pending
    pending = get_pending(conn, MAX_PER_BATCH)
    if not pending:
        total = conn.execute("SELECT COUNT(*) FROM scraper_state WHERE status='downloaded'").fetchone()[0]
        all_count = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        print(f"All done! {total}/{all_count} downloaded")
        conn.close()
        return
    
    print(f"Downloading {len(pending)} transcripts...")
    
    proxy_config = GenericProxyConfig(
        http_url=PROXY,
        https_url=PROXY,
    )
    api = YouTubeTranscriptApi(proxy_config=proxy_config)
    
    success = 0
    failed = 0
    
    for i, video in enumerate(pending, 1):
        vid = video['id']
        title = video.get('title', '?')[:60]
        
        print(f"[{i}/{len(pending)}] {vid} | {title}")
        
        text, error, lang = download_transcript(api, vid, title)
        
        if text:
            num_chunks = save_chunks(conn, vid, text)
            conn.execute("""UPDATE scraper_state SET status='downloaded', 
                error=NULL, attempts=attempts+1, updated_at=datetime('now')
                WHERE video_id=?""", (vid,))
            conn.commit()
            print(f"  ✓ {len(text.split())} words, {num_chunks} chunks")
            success += 1
        elif error and "IpBlocked" in error:
            print(f"  ✗ IP blocked! Stopping.")
            conn.execute("""UPDATE scraper_state SET status='failed', 
                error=?, attempts=attempts+1, updated_at=datetime('now')
                WHERE video_id=?""", (str(error)[:500], vid))
            conn.commit()
            failed += 1
            break
        else:
            conn.execute("""UPDATE scraper_state SET status='failed', 
                error=?, attempts=attempts+1, updated_at=datetime('now')
                WHERE video_id=?""", (str(error)[:500], vid))
            conn.commit()
            print(f"  ✗ {error[:100]}")
            failed += 1
        
        # Delay
        if i < len(pending):
            time.sleep(DELAY)
    
    total = conn.execute("SELECT COUNT(*) FROM scraper_state WHERE status='downloaded'").fetchone()[0]
    all_count = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    print(f"\n{'='*40}")
    print(f"Session: {success} OK, {failed} failed")
    print(f"Total: {total}/{all_count} downloaded")
    
    conn.close()

if __name__ == "__main__":
    main()

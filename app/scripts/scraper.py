#!/usr/bin/env python3
"""
Micha Stocks — Transcript Scraper (v2 with proxy & cooke support)
===============================================================
Handles YouTube IP blocks gracefully with fallback options.
"""

import argparse
import json
import os
import random
import sqlite3
import subprocess
import sys
import time
import re
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────

CHANNEL_URL = "https://youtube.com/@micha.stocks"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "micha.db")
MIN_DELAY = 1.8
MAX_DELAY = 4.2
BATCH_SIZE = 50
BATCH_PAUSE = 30
LARGE_BATCH = 500
LARGE_PAUSE = 300
CHUNK_SIZE = 250
CHUNK_OVERLAP = 50

def get_db(path=None):
    db_path = path or DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path) as f:
            conn.executescript(f.read())
    else:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY, title TEXT, duration_seconds INTEGER,
                upload_date TEXT, url TEXT, downloaded_at TEXT,
                transcript_language TEXT DEFAULT 'en'
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
    conn.commit()
    return conn

def get_pending_videos(conn):
    cur = conn.execute("""
        SELECT v.id, v.title, v.duration_seconds
        FROM videos v
        LEFT JOIN scraper_state s ON v.id = s.video_id
        WHERE s.status IS NULL OR s.status = 'pending' OR s.status = 'failed'
        ORDER BY v.upload_date ASC
    """)
    return [dict(r) for r in cur.fetchall()]

def get_downloaded_count(conn):
    return conn.execute("SELECT COUNT(*) FROM scraper_state WHERE status = 'downloaded'").fetchone()[0]

def mark_pending(conn, video_id):
    conn.execute("""
        INSERT OR IGNORE INTO scraper_state (video_id, status, updated_at)
        VALUES (?, 'pending', datetime('now'))
    """, (video_id,))
    conn.commit()

def mark_downloaded(conn, video_id):
    conn.execute("""
        UPDATE scraper_state SET status = 'downloaded', error = NULL, 
        attempts = attempts + 1, updated_at = datetime('now')
        WHERE video_id = ?
    """, (video_id,))
    conn.commit()

def mark_failed(conn, video_id, error):
    conn.execute("""
        UPDATE scraper_state SET status = 'failed', error = ?,
        attempts = attempts + 1, updated_at = datetime('now')
        WHERE video_id = ?
    """, (str(error)[:500], video_id))
    conn.commit()

def save_video(conn, video_id, title, duration, upload_date):
    conn.execute("""
        INSERT OR IGNORE INTO videos (id, title, duration_seconds, upload_date, url)
        VALUES (?, ?, ?, ?, ?)
    """, (video_id, title, duration, upload_date, f"https://youtube.com/watch?v={video_id}"))
    conn.commit()

def save_chunks(conn, video_id, full_text):
    words = full_text.split()
    chunks = []
    start = 0
    chunk_idx = 0
    while start < len(words):
        end = start + CHUNK_SIZE
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)
        chunks.append((video_id, chunk_idx, chunk_text, len(chunk_text)))
        chunk_idx += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
    conn.executemany("""
        INSERT OR REPLACE INTO transcript_chunks (video_id, chunk_index, text, char_count)
        VALUES (?, ?, ?, ?)
    """, chunks)
    conn.commit()
    return len(chunks)

def is_already_downloaded(conn, video_id):
    cur = conn.execute(
        "SELECT status FROM scraper_state WHERE video_id = ? AND status = 'downloaded'",
        (video_id,)
    )
    return cur.fetchone() is not None

# ── YouTube Download ──────────────────────────────────────────────────

def download_transcript_ytdlp(video_id, proxy=None, cookies_file=None, max_retries=3):
    """Download auto-generated subtitles using yt-dlp with proxy/cookie support."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, f"{video_id}")
        cmd = [
            "yt-dlp",
            "--write-auto-subs", "--sub-langs", "en,iw,he",
            "--skip-download", "--convert-subs", "srt",
            "--sleep-interval", "3", "--max-sleep-interval", "6",
            "--retries", str(max_retries),
            "--no-warnings",
            "-o", out_path,
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        if proxy:
            cmd.extend(["--proxy", proxy])
        if cookies_file and os.path.exists(cookies_file):
            cmd.extend(["--cookies", cookies_file])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        # Check for subtitle files
        for f in os.listdir(tmpdir):
            if f.endswith(('.vtt', '.srt')) and video_id in f:
                filepath = os.path.join(tmpdir, f)
                with open(filepath, encoding='utf-8', errors='replace') as fh:
                    text = fh.read()
                # Strip VTT/SRT formatting
                lines = []
                for line in text.split('\n'):
                    line = line.strip()
                    if (not line or line.isdigit() or 
                        '-->' in line or 
                        line.startswith('WEBVTT') or
                        line.startswith('Kind:') or
                        line.startswith('Language:')):
                        continue
                    lines.append(line)
                plain_text = ' '.join(lines)
                if plain_text.strip():
                    return plain_text, None
                return None, "Empty subtitle file"
        
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else ""
            if "429" in stderr or "Too Many Requests" in stderr:
                return None, f"RATE_LIMITED: {stderr[:100]}"
            if "403" in stderr or "Forbidden" in stderr:
                return None, f"BLOCKED: {stderr[:100]}"
            if "Private video" in stderr:
                return None, "PRIVATE_VIDEO"
            return None, stderr[:200] or "Unknown yt-dlp error"
        
        return None, "No subtitle files found"
    
def download_transcript_api(video_id, proxy=None, max_retries=3):
    """Fallback: use youtube-transcript-api with optional proxy."""
    for attempt in range(max_retries):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            segments = list(api.fetch(video_id, languages=['en', 'iw', 'he']))
            text = ' '.join(seg.text for seg in segments)
            if text.strip():
                return text, None
        except Exception as e:
            err = str(e)
            if "IpBlocked" in err or "429" in err:
                return None, f"RATE_LIMITED: {err[:100]}"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None, err
    return None, "Max retries"

def download_transcript(video_id, method='auto', proxy=None, cookies_file=None):
    """Try multiple download methods. Returns (text, error)."""
    
    # Method 1: yt-dlp
    text, error = download_transcript_ytdlp(video_id, proxy, cookies_file)
    if text:
        return text, None
    if error and "RATE_LIMITED" in error:
        return None, error
    if error and "PRIVATE_VIDEO" in error:
        return None, error
    
    # Method 2: youtube-transcript-api (fallback)
    text, error = download_transcript_api(video_id, proxy)
    if text:
        return text, None
    
    return None, error

# ── Channel Listing ───────────────────────────────────────────────────

def run_ytdlp(args, timeout=120):
    cmd = ["yt-dlp"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return None, result.stderr.strip()
        return result.stdout.strip(), None
    except subprocess.TimeoutExpired:
        return None, "Timeout"
    except FileNotFoundError:
        print("ERROR: yt-dlp not installed. Run: pip install yt-dlp")
        sys.exit(1)

def list_channel_videos(channel_url):
    print(f"Fetching video list from {channel_url}...")
    output, err = run_ytdlp([
        "--flat-playlist", "--dump-json", "--no-warnings",
        channel_url + "/videos"
    ], timeout=180)
    if err and not output:
        print(f"Error fetching channel: {err}")
        return []
    videos = []
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            videos.append({
                'id': data.get('id'),
                'title': data.get('title', 'Unknown'),
                'duration': data.get('duration'),
                'upload_date': data.get('upload_date'),
            })
        except json.JSONDecodeError:
            continue
    return videos

# ── Main Scrape Loop ──────────────────────────────────────────────────

def scrape_channel(channel_url, db_path=None, resume=False, proxy=None, cookies_file=None, max_videos=None):
    conn = get_db(db_path)
    
    if resume:
        print(f"Resuming from checkpoint...")
        videos = get_pending_videos(conn)
        if not videos:
            cur = conn.execute("SELECT COUNT(*) FROM videos")
            count = cur.fetchone()[0]
            if count == 0:
                print("No videos in database. Run without --resume first.")
                conn.close()
                return
            else:
                print("All videos downloaded! Nothing to resume.")
                conn.close()
                return
        print(f"Found {len(videos)} videos pending/retrying.")
    else:
        video_list = list_channel_videos(channel_url)
        if not video_list:
            print("No videos found. Check the channel URL.")
            conn.close()
            return
        print(f"Found {len(video_list)} videos on channel.")
        for v in video_list:
            save_video(conn, v['id'], v['title'], v['duration'], v['upload_date'])
            mark_pending(conn, v['id'])
        videos = get_pending_videos(conn)
    
    if max_videos:
        videos = videos[:max_videos]
        print(f"Limited to {max_videos} videos (--max-videos)")
    
    total = len(videos)
    downloaded = get_downloaded_count(conn)
    retry_after = None  # If rate limited, wait time
    
    print(f"\nStarting scrape: {total} remaining, {downloaded} already done")
    if proxy:
        print(f"Using proxy: {proxy}")
    if cookies_file:
        print(f"Using cookies: {cookies_file}")
    print(f"Delays: {MIN_DELAY}-{MAX_DELAY}s")
    print("─" * 50)
    
    start_time = time.time()
    blocked = False
    
    for idx, video in enumerate(videos, 1):
        video_id = video['id']
        title = video.get('title', '?')[:60]
        
        if is_already_downloaded(conn, video_id):
            continue
        
        # Check for rate limit backoff
        if blocked:
            print(f"  [Rate limited] Skipping remaining videos...")
            break
        
        # Polite delay
        if idx > 1:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        
        # Batch pauses
        if idx > 1 and (idx - 1) % BATCH_SIZE == 0:
            print(f"  Break {BATCH_PAUSE}s...")
            time.sleep(BATCH_PAUSE)
        if idx > 1 and (idx - 1) % LARGE_BATCH == 0:
            print(f"  Long break {LARGE_PAUSE // 60}min...")
            time.sleep(LARGE_PAUSE)
        
        # Progress
        elapsed = time.time() - start_time
        rate = idx / elapsed if elapsed > 0 else 0
        print(f"[{idx}/{total}] {video_id} | {title}")
        
        text, error = download_transcript(video_id, proxy=proxy, cookies_file=cookies_file)
        
        if text:
            num_chunks = save_chunks(conn, video_id, text)
            mark_downloaded(conn, video_id)
            words = len(text.split())
            print(f"  ✓ {words} words, {num_chunks} chunks")
        elif error and "RATE_LIMITED" in error:
            print(f"  ⚠ RATE LIMITED — YouTube is blocking requests from this IP.")
            print(f"  ⚠ Waiting until tomorrow or use --proxy/--cookies.")
            blocked = True
            mark_failed(conn, video_id, error)
        else:
            mark_failed(conn, video_id, error or "Unknown")
            print(f"  ✗ {error[:80]}")
    
    final_downloaded = get_downloaded_count(conn)
    total_time = time.time() - start_time
    print(f"\n{'=' * 50}")
    print(f"Downloaded: {final_downloaded} / {total}")
    print(f"Time: {total_time / 60:.1f} min")
    
    if blocked:
        print(f"\n⚠ YouTube rate limit detected. Options:")
        print(f"  1. Wait ~24h for the block to lift, then: python3 scripts/scraper.py --resume")
        print(f"  2. Use a proxy: python3 scripts/scraper.py --proxy http://your-proxy:8080")
        print(f"  3. Use browser cookies: python3 scripts/scraper.py --cookies cookies.txt")
    
    conn.close()

# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polite YouTube transcript scraper")
    parser.add_argument("--channel", default=CHANNEL_URL, help="YouTube channel URL")
    parser.add_argument("--db", help="Path to SQLite database (default: data/micha.db)")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted download")
    parser.add_argument("--list", action="store_true", help="List videos, don't download")
    parser.add_argument("--proxy", help="HTTP/HTTPS proxy (e.g., http://127.0.0.1:8080)")
    parser.add_argument("--cookies", help="Path to Netscape-format cookies.txt file")
    parser.add_argument("--max-videos", type=int, help="Limit to N videos (for testing)")
    args = parser.parse_args()
    
    if args.list:
        list_videos_only(args.channel)
    else:
        scrape_channel(
            args.channel, args.db, resume=args.resume,
            proxy=args.proxy, cookies_file=args.cookies,
            max_videos=args.max_videos
        )

#!/usr/bin/env python3.14
"""
Continuous batch downloader — runs batches until all transcripts are downloaded.
Reports progress after each batch.
"""
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(__file__)
BATCH_SCRIPT = os.path.join(SCRIPT_DIR, "batch_download.py")
CHECK_SCRIPT = os.path.join(SCRIPT_DIR, "check_progress.py")
PROGRESS_LOG = "/tmp/micha_progress.log"

batch_num = 0
with open(PROGRESS_LOG, "a") as log:
    log.write(f"\n{'='*50}\nContinuous downloader started at {time.strftime('%Y-%m-%d %H:%M')}\n{'='*50}\n")

while True:
    batch_num += 1
    
    # Check if we're done
    result = subprocess.run([sys.executable, CHECK_SCRIPT], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    for l in lines:
        if 'downloaded' in l:
            parts = l.split('/')
            if len(parts) >= 2:
                try:
                    done = int(parts[0].split()[-1])
                    total = int(parts[1].split()[0])
                    if done >= total:
                        with open(PROGRESS_LOG, "a") as log:
                            log.write(f"\n✅ ALL DONE at {time.strftime('%Y-%m-%d %H:%M')}\n")
                        print("✅ All transcripts downloaded!")
                        sys.exit(0)
                except:
                    pass
    
    # Run a batch
    print(f"\n🔄 Batch #{batch_num} starting at {time.strftime('%Y-%m-%d %H:%M')}")
    with open(PROGRESS_LOG, "a") as log:
        log.write(f"\nBatch #{batch_num} starting...\n")
    
    result = subprocess.run([sys.executable, BATCH_SCRIPT], capture_output=True, text=True, timeout=600)
    
    # Log output
    with open(PROGRESS_LOG, "a") as log:
        log.write(result.stdout[-1000:] if result.stdout else "No output\n")
        if result.stderr:
            log.write(f"STDERR: {result.stderr[-500:]}\n")
    
    # Report progress
    result = subprocess.run([sys.executable, CHECK_SCRIPT], capture_output=True, text=True)
    print(result.stdout)
    
    # Small pause between batches
    time.sleep(5)

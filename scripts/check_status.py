"""Script to check processing status of URLs"""
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from utils.file_utils import (
    load_json,
    get_discovered_urls_file,
    get_processing_status_file,
    get_failed_urls_file
)

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    dt = datetime.fromisoformat(timestamp_str)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def main():
    # Load all status files
    urls_data = load_json(get_discovered_urls_file())
    status = load_json(get_processing_status_file()) or {}
    failed_urls = load_json(get_failed_urls_file()) or {"urls": []}
    
    if not urls_data:
        print("No discovered URLs found.")
        return
    
    total_urls = len(urls_data["urls"])
    
    # Count URLs in each stage
    stage_counts = Counter(item.get("stage", "unknown") for item in status.values())
    status_counts = Counter(item.get("status", "unknown") for item in status.values())
    
    # Print summary
    print("\n=== Processing Status Summary ===")
    print(f"Total URLs discovered: {total_urls}")
    print(f"URLs in status file: {len(status)}")
    print(f"Failed URLs: {len(failed_urls['urls'])}")
    
    print("\n=== Status Breakdown ===")
    for status_type, count in status_counts.items():
        print(f"{status_type}: {count}")
    
    print("\n=== Stage Breakdown ===")
    for stage, count in stage_counts.items():
        print(f"{stage}: {count}")
    
    # Print recent failures
    if failed_urls["urls"]:
        print("\n=== Recent Failures ===")
        recent_failures = sorted(
            failed_urls["urls"],
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:5]  # Show last 5 failures
        
        for failure in recent_failures:
            print(f"\nURL: {failure['url']}")
            print(f"Stage: {failure['stage']}")
            print(f"Error: {failure['error']}")
            if "timestamp" in failure:
                print(f"Time: {format_timestamp(failure['timestamp'])}")
    
    # Print processing rate
    completed = [url for url, data in status.items() 
                if data.get("status") == "completed" and "last_updated" in data]
    if completed:
        latest = max(completed, key=lambda url: status[url]["last_updated"])
        earliest = min(completed, key=lambda url: status[url]["last_updated"])
        latest_time = datetime.fromisoformat(status[latest]["last_updated"])
        earliest_time = datetime.fromisoformat(status[earliest]["last_updated"])
        time_diff = latest_time - earliest_time
        if time_diff.total_seconds() > 0:
            rate = len(completed) / time_diff.total_seconds() * 3600  # URLs per hour
            print(f"\nProcessing Rate: {rate:.1f} URLs/hour")

if __name__ == "__main__":
    main() 
"""Script to discover and save all URLs from the Greenburgh website"""
import os
from pathlib import Path
import sys

# Add src directory to path so we can import our modules
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from scraper import discover_urls
from utils.file_utils import save_json, get_discovered_urls_file

def main():
    # Get URLs up to specified depth
    start_url = "https://www.greenburghny.com/"
    max_depth = int(os.getenv("MAX_DEPTH", "2"))
    
    print(f"Discovering URLs from {start_url} up to depth {max_depth}")
    discovered_urls = discover_urls(start_url, max_depth)
    
    # Save discovered URLs
    urls_file = get_discovered_urls_file()
    save_json(discovered_urls, urls_file)
    print(f"Saved {len(discovered_urls)} URLs to {urls_file}")

if __name__ == "__main__":
    main() 
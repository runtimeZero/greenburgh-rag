"""Script to scrape content from discovered URLs"""
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from scraper import scrape_single_url
from utils.file_utils import (
    load_json, save_json, 
    get_discovered_urls_file, 
    get_scraped_file_path,
    get_processing_status_file,
    get_failed_urls_file,
    DATA_DIR
)
from utils.ingest import combine_small_documents

def main():
    # Load discovered URLs
    urls_data = load_json(get_discovered_urls_file())
    if not urls_data:
        print("No discovered URLs found. Run 01_discover_urls.py first.")
        return
    
    # Load processing status
    status = load_json(get_processing_status_file()) or {}
    failed_urls = load_json(get_failed_urls_file()) or {"urls": []}
    
    # Collect all scraped content
    all_content = []
    
    for url_data in urls_data["urls"]:
        url = url_data["url"]
        if url in status and status[url]["status"] == "completed":
            # Load existing content
            content = load_json(get_scraped_file_path(url))
            if content:
                all_content.append(content)
            continue
            
        print(f"Scraping {url}")
        try:
            content = scrape_single_url(url)
            if content:
                all_content.append(content)
                # Save individual content
                save_json(content, get_scraped_file_path(url))
                # Update status
                status[url] = {"status": "completed", "stage": "scraped"}
                save_json(status, get_processing_status_file())
                print(f"Successfully scraped {url}")
            else:
                print(f"Skipping {url} - no content returned")
                
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            failed_urls["urls"].append({
                "url": url,
                "error": str(e),
                "stage": "scraping"
            })
            save_json(failed_urls, get_failed_urls_file())
    
    # Combine small documents
    print("Combining small documents...")
    combined_content = combine_small_documents(all_content)
    print(f"Reduced {len(all_content)} documents to {len(combined_content)} meaningful chunks")
    
    # Save combined content
    save_json({"documents": combined_content}, DATA_DIR / 'combined_content.json')

if __name__ == "__main__":
    main() 
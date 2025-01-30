"""Script to create chunks from scraped content"""
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from ingest import chunk_texts
from utils.file_utils import (
    load_json, save_json,
    get_discovered_urls_file,
    get_scraped_file_path,
    get_chunks_file_path,
    get_processing_status_file,
    get_failed_urls_file
)

def convert_chunks_to_dict(chunks):
    """Convert LangChain Document objects to dictionaries"""
    return [
        {
            "page_content": chunk.page_content,
            "metadata": chunk.metadata
        }
        for chunk in chunks
    ]

def main():
    # Load discovered URLs and processing status
    urls_data = load_json(get_discovered_urls_file())
    status = load_json(get_processing_status_file()) or {}
    failed_urls = load_json(get_failed_urls_file()) or {"urls": []}
    
    if not urls_data:
        print("No discovered URLs found. Run 01_discover_urls.py first.")
        return
    
    for url_data in urls_data["urls"]:
        url = url_data["url"]
        
        # Initialize status for this URL if not exists
        if url not in status:
            status[url] = {"status": "pending", "stage": "discovered"}
        
        # Check if already chunked
        if status[url].get("stage") == "chunked":
            print(f"Skipping {url} - already chunked")
            continue
            
        # Check if content was scraped
        if status[url].get("stage") != "scraped":
            print(f"Skipping {url} - not yet scraped")
            continue
        
        print(f"Creating chunks for {url}")
        try:
            # Load scraped content
            content = load_json(get_scraped_file_path(url))
            if not content:
                raise Exception("No scraped content found")
            
            # If content is wrapped in a "documents" key, extract it
            if isinstance(content, dict) and "documents" in content:
                documents = content["documents"]
            else:
                documents = [content]  # Single document case
            
            # Create chunks and convert to dictionary
            chunks = chunk_texts(documents)
            chunks_dict = convert_chunks_to_dict(chunks)
            
            # Save chunks
            save_json(chunks_dict, get_chunks_file_path(url))
            
            # Update status
            status[url].update({
                "status": "completed",
                "stage": "chunked",
                "chunks_count": len(chunks_dict),
                "last_updated": datetime.utcnow().isoformat()
            })
            save_json(status, get_processing_status_file())
            print(f"Successfully created {len(chunks_dict)} chunks for {url}")
            
        except Exception as e:
            print(f"Failed to create chunks for {url}: {e}")
            # Update status for failed URLs
            status[url].update({
                "status": "failed",
                "stage": "chunking",
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat()
            })
            failed_urls["urls"].append({
                "url": url,
                "error": str(e),
                "stage": "chunking",
                "timestamp": datetime.utcnow().isoformat()
            })
            save_json(failed_urls, get_failed_urls_file())
            
        # Save status after each URL (in case of interruption)
        save_json(status, get_processing_status_file())

if __name__ == "__main__":
    main() 
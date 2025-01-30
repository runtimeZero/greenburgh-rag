"""Script to upload embeddings to Pinecone"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from qa_chain import upload_to_pinecone
from utils.file_utils import (
    load_json,
    save_json,
    get_discovered_urls_file,
    get_embeddings_file_path,
    get_processing_status_file,
    get_failed_urls_file
)

# Load environment variables
load_dotenv()

def main():
    # Load discovered URLs and processing status
    urls_data = load_json(get_discovered_urls_file())
    status = load_json(get_processing_status_file()) or {}
    
    # Handle failed_urls file more gracefully
    try:
        failed_urls = load_json(get_failed_urls_file())
    except (json.JSONDecodeError, FileNotFoundError):
        print("Warning: Failed URLs file is corrupt or missing. Creating new one.")
        failed_urls = {"urls": []}
        save_json(failed_urls, get_failed_urls_file())
    
    if not urls_data:
        print("No discovered URLs found. Run 01_discover_urls.py first.")
        return
    
    print(f"Found {len(urls_data['urls'])} URLs in total")
    print(f"Status file contains {len(status)} entries")
    
    embedded_count = sum(1 for url in status if status[url].get("stage") == "embedded")
    print(f"Found {embedded_count} URLs marked as embedded")
    
    for url_data in urls_data["urls"]:
        url = url_data["url"]
        
        # Check if already uploaded
        if url in status and status[url].get("stage") == "uploaded":
            print(f"Skipping {url} - already uploaded to Pinecone")
            continue
            
        # Check if embeddings exist
        if url not in status or status[url].get("stage") != "embedded":
            print(f"Skipping {url} - not yet embedded")
            continue
        
        # Check if embeddings file exists
        embeddings_file = get_embeddings_file_path(url)
        if not embeddings_file.exists():
            print(f"Warning: Embeddings file not found for {url} at {embeddings_file}")
            continue
            
        print(f"Uploading embeddings for {url}")
        try:
            # Load embeddings
            embeddings = load_json(embeddings_file)
            if not embeddings:
                raise Exception("No embeddings found")
            
            print(f"Loaded {len(embeddings)} embeddings from {embeddings_file}")
            
            # Upload to Pinecone
            uploaded_count = upload_to_pinecone(embeddings)
            
            # Update status
            status[url]["stage"] = "uploaded"
            save_json(status, get_processing_status_file())
            print(f"Successfully uploaded {uploaded_count} embeddings for {url}")
            
        except Exception as e:
            print(f"Failed to upload embeddings for {url}: {e}")
            failed_urls["urls"].append({
                "url": url,
                "error": str(e),
                "stage": "uploading"
            })
            save_json(failed_urls, get_failed_urls_file())

if __name__ == "__main__":
    main() 
"""Script to create embeddings from chunks"""
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from ingest import embed_documents
from utils.file_utils import (
    load_json, save_json,
    get_discovered_urls_file,
    get_chunks_file_path,
    get_embeddings_file_path,
    get_processing_status_file,
    get_failed_urls_file
)
from langchain.docstore.document import Document

def chunks_to_documents(chunks):
    """Convert chunk dictionaries back to LangChain Documents"""
    return [
        Document(
            page_content=chunk["page_content"],
            metadata=chunk["metadata"]
        )
        for chunk in chunks
    ]

def main():
    # Load discovered URLs and processing status
    urls_data = load_json(get_discovered_urls_file())
    status = load_json(get_processing_status_file()) or {}
    failed_urls = load_json(get_failed_urls_file()) or {"urls": []}
    
    # Find latest checkpoint if it exists
    checkpoint_files = list(Path('data/embeddings').glob('embeddings_checkpoint_*.json'))
    existing_embeddings = []
    if checkpoint_files:
        latest_checkpoint = max(checkpoint_files, key=lambda x: int(x.stem.split('_')[-1]))
        print(f"Found checkpoint file: {latest_checkpoint}")
        existing_embeddings = load_json(latest_checkpoint)
        print(f"Loaded {len(existing_embeddings)} existing embeddings")
    
    # Track which chunks we've already processed
    processed_chunk_ids = {e['id'] for e in existing_embeddings}
    
    for url_data in urls_data["urls"]:
        url = url_data["url"]
        
        # Skip already completed URLs
        if url in status and status[url].get("stage") == "embedded":
            print(f"Skipping {url} - already embedded")
            continue
            
        # Check if chunks exist
        if status[url].get("stage") != "chunked":
            print(f"Skipping {url} - not yet chunked")
            continue
        
        print(f"Creating embeddings for {url}")
        try:
            # Load chunks
            chunks = load_json(get_chunks_file_path(url))
            if not chunks:
                raise Exception("No chunks found")
            
            # Filter out already processed chunks
            new_chunks = [
                chunk for chunk in chunks 
                if chunk.get('chunk_id') not in processed_chunk_ids
            ]
            
            if not new_chunks:
                print(f"All chunks already processed for {url}")
                continue
                
            print(f"Processing {len(new_chunks)} new chunks")
            
            # Convert chunks back to Documents
            documents = chunks_to_documents(new_chunks)
            
            # Create embeddings
            new_embeddings = embed_documents(documents)
            
            # Combine with existing embeddings
            all_embeddings = existing_embeddings + new_embeddings
            
            # Save all embeddings
            embeddings_file = get_embeddings_file_path(url)
            embeddings_file.parent.mkdir(parents=True, exist_ok=True)
            save_json(all_embeddings, embeddings_file)
            
            # Update status
            status[url].update({
                "status": "completed",
                "stage": "embedded", 
                "embeddings_count": len(all_embeddings),
                "last_updated": datetime.utcnow().isoformat()
            })
            save_json(status, get_processing_status_file())
            print(f"Successfully created {len(new_embeddings)} new embeddings for {url}")
            
            # Update existing embeddings for next URL
            existing_embeddings = all_embeddings
            processed_chunk_ids.update(e['id'] for e in new_embeddings)
            
        except Exception as e:
            print(f"Failed to create embeddings for {url}: {e}")
            status[url].update({
                "status": "failed",
                "stage": "embedding",
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat()
            })
            failed_urls["urls"].append({
                "url": url,
                "error": str(e),
                "stage": "embedding",
                "timestamp": datetime.utcnow().isoformat()
            })
            save_json(failed_urls, get_failed_urls_file())
        
        # Save status after each URL (in case of interruption)
        save_json(status, get_processing_status_file())

if __name__ == "__main__":
    main() 
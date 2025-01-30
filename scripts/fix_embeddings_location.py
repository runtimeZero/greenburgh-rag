import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from utils.file_utils import get_url_hash, get_embeddings_file_path, load_json, save_json, get_processing_status_file

def move_checkpoint_files():
    # Load status file
    status_file = get_processing_status_file()
    status = load_json(status_file)
    if not status:
        print("Error: Could not load status file")
        return
        
    # Find all checkpoint files
    checkpoint_files = list(Path('data/embeddings').glob('embeddings_checkpoint_*.json'))
    
    if not checkpoint_files:
        print("No checkpoint files found")
        return
        
    print(f"Found {len(checkpoint_files)} checkpoint files")
    
    # Process all checkpoint files
    url_embeddings = {}
    
    for checkpoint_file in sorted(checkpoint_files, key=lambda x: int(x.stem.split('_')[-1])):
        print(f"\nProcessing {checkpoint_file}")
        try:
            # Load the embeddings data
            embeddings = load_json(checkpoint_file)
            if not embeddings:
                print("No embeddings found in checkpoint file")
                continue
                
            print(f"Loaded {len(embeddings)} embeddings")
            
            # Group embeddings by URL
            for embedding in embeddings:
                url = embedding['metadata'].get('source')
                if url:
                    if url not in url_embeddings:
                        url_embeddings[url] = []
                    # Only add if this embedding ID isn't already present
                    if not any(e['id'] == embedding['id'] for e in url_embeddings[url]):
                        url_embeddings[url].append(embedding)
        
        except Exception as e:
            print(f"Error processing {checkpoint_file}: {e}")
    
    print(f"\nFound embeddings for {len(url_embeddings)} URLs")
    
    # Save embeddings for each URL and update status
    for url, embeddings_list in url_embeddings.items():
        try:
            # Get the URL's current status
            if url not in status:
                print(f"Warning: URL {url} not found in status file")
                continue

            # Save embeddings
            dest_path = get_embeddings_file_path(url)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            save_json(embeddings_list, dest_path)
            
            # Update status
            status[url].update({
                "status": "completed",
                "stage": "embedded",
                "embeddings_count": len(embeddings_list),
                "error": None  # Clear any previous error
            })
            print(f"Saved {len(embeddings_list)} embeddings for {url}")
        
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            status[url].update({
                "status": "failed",
                "error": str(e)
            })
    
    # Save updated status
    save_json(status, status_file)
    print("\nUpdated processing status file")

if __name__ == "__main__":
    move_checkpoint_files() 
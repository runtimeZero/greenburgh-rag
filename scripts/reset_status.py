import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from utils.file_utils import load_json, save_json, get_processing_status_file

def reset_embedding_status():
    status_file = get_processing_status_file()
    status = load_json(status_file)
    
    for url in status:
        if status[url]["status"] == "completed" and status[url]["stage"] == "chunked":
            continue
            
        status[url].update({
            "status": "completed",
            "stage": "chunked",
            "error": None
        })
        if "embeddings_count" in status[url]:
            del status[url]["embeddings_count"]
            
    save_json(status, status_file)
    print("Reset all documents back to chunked stage")

if __name__ == "__main__":
    reset_embedding_status() 
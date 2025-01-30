import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from utils.file_utils import save_json, get_failed_urls_file

def reset_failed_urls():
    # Create a fresh failed_urls file
    failed_urls = {
        "urls": []
    }
    save_json(failed_urls, get_failed_urls_file())
    print("Reset failed_urls.json file")

if __name__ == "__main__":
    reset_failed_urls() 
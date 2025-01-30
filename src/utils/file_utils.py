import os
import json
from pathlib import Path
from typing import Dict, List, Any
import hashlib

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure all data directories exist
DIRS = {
    'discovered': DATA_DIR / 'discovered',
    'scraped': DATA_DIR / 'scraped',
    'chunks': DATA_DIR / 'chunks',
    'embeddings': DATA_DIR / 'embeddings',
    'errors': DATA_DIR / 'errors'
}

def ensure_directories():
    """Ensure all required directories exist"""
    for dir_path in DIRS.values():
        dir_path.mkdir(parents=True, exist_ok=True)

def get_url_hash(url: str) -> str:
    """Create a consistent hash for a URL to use as a filename"""
    return hashlib.md5(url.encode()).hexdigest()

def save_json(data: Any, filepath: Path):
    """Save data to a JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(filepath: Path) -> Any:
    """Load data from a JSON file"""
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_discovered_urls_file() -> Path:
    """Get path to discovered URLs file"""
    return DIRS['discovered'] / 'discovered_urls.json'

def get_processing_status_file() -> Path:
    """Get path to processing status file"""
    return DIRS['discovered'] / 'processing_status.json'

def get_failed_urls_file() -> Path:
    """Get path to failed URLs file"""
    return DIRS['errors'] / 'failed_urls.json'

def get_scraped_file_path(url: str) -> Path:
    """Get path where scraped content for a URL should be stored"""
    return DIRS['scraped'] / f"{get_url_hash(url)}.json"

def get_chunks_file_path(url: str) -> Path:
    """Get path where chunks for a URL should be stored"""
    return DIRS['chunks'] / f"{get_url_hash(url)}.json"

def get_embeddings_file_path(url: str) -> Path:
    """Get path where embeddings for a URL should be stored"""
    return DIRS['embeddings'] / f"{get_url_hash(url)}.json"

# Initialize directories when module is imported
ensure_directories() 
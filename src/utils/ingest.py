from typing import List, Dict
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def combine_small_documents(documents: List[dict], min_words: int = 100) -> List[dict]:
    """
    Combine small documents into larger ones based on their URL structure
    """
    # Group documents by their URL path
    url_groups = {}
    for doc in documents:
        url = doc['url']
        path = urlparse(url).path
        base_path = '/'.join(path.split('/')[:3])  # Group by top-level sections
        
        if base_path not in url_groups:
            url_groups[base_path] = []
        url_groups[base_path].append(doc)
    
    # Combine documents in each group if they're too small
    combined_docs = []
    for base_path, docs in url_groups.items():
        current_doc = None
        
        for doc in sorted(docs, key=lambda x: x['url']):
            word_count = len(doc['text'].split())
            
            if word_count >= min_words:
                # Document is large enough on its own
                combined_docs.append(doc)
                current_doc = None
            else:
                if current_doc is None:
                    current_doc = {
                        'url': base_path,
                        'text': f"Combined content from {base_path}:\n\n",
                        'type': 'combined',
                        'metadata': {
                            'sources': [],
                            'combined': True,
                            'base_path': base_path
                        }
                    }
                
                # Add content to combined document
                current_doc['text'] += f"\nFrom {doc['url']}:\n{doc['text']}\n"
                current_doc['metadata']['sources'].append(doc['url'])
                
                # If combined document is now large enough, save it
                if len(current_doc['text'].split()) >= min_words:
                    combined_docs.append(current_doc)
                    current_doc = None
        
        # Add any remaining combined document
        if current_doc is not None:
            combined_docs.append(current_doc)
    
    return combined_docs 
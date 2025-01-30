# ingest.py

import json
from pathlib import Path
from typing import List
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse
from datetime import datetime
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import uuid

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBEDDINGS_OUTPUT = "embeddings.json"

def load_scraped_data(scraped_file: str = "scraped_data.json"):
    """Load the JSON output from your advanced scraper."""
    logger.info(f"Loading scraped data from {scraped_file}")
    with open(scraped_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} documents")
    return data

def chunk_texts(data: List[dict], chunk_size=500, chunk_overlap=50):
    """Convert each item in `data` into multiple chunked Documents."""
    logger.info(f"Chunking {len(data)} documents")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        length_function=len
    )
    
    documents = []
    for item in data:
        try:
            # Skip empty or very short texts
            if not item.get("text") or len(item["text"]) < 50:
                logger.warning(f"Skipping short/empty document: {item.get('url')}")
                continue
            
            # Create metadata with defaults for missing fields
            metadata = {
                "source": item.get("url", "unknown"),
                "type": item.get("type", "html"),
                "depth": item.get("depth", 0),  # Default depth to 0 if missing
                "last_modified": (
                    item.get("metadata", {}).get("last_modified") 
                    or datetime.utcnow().isoformat()
                )
            }
                
            chunks = text_splitter.create_documents(
                texts=[item["text"]],
                metadatas=[metadata]
            )
            
            # Log if we're creating too many chunks
            if len(chunks) > 100:
                logger.warning(f"Large number of chunks ({len(chunks)}) for {item.get('url')}")
            
            documents.extend(chunks)
            
        except Exception as e:
            logger.error(f"Error chunking document {item.get('url', 'unknown')}: {e}")
            logger.exception("Full error:")  # This will print the full stack trace
    
    logger.info(f"Created {len(documents)} chunks")
    return documents

def embed_documents(documents: List[Document]):
    """Embed documents using OpenAI embeddings with better error handling"""
    logger.info("Starting document embedding process")
    
    try:
        # Initialize embeddings with timeout
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            timeout=60,  # 60 second timeout
            max_retries=3  # Retry failed requests up to 3 times
        )
        
        # Process in batches
        upsert_data = []
        total_docs = len(documents)
        batch_size = 16
        
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}")
            
            try:
                # Get embeddings for batch with timeout
                texts = [doc.page_content for doc in batch]
                vectors = embeddings.embed_documents(texts)
                
                # Create upsert data
                for doc, vector_vals in zip(batch, vectors):
                    metadata = doc.metadata.copy()
                    metadata["text"] = doc.page_content
                    
                    upsert_data.append({
                        "id": metadata.get("chunk_id", str(uuid.uuid4())),
                        "values": vector_vals,
                        "metadata": metadata
                    })
                
                logger.info(f"Successfully embedded batch of {len(batch)} documents")
                
                # Save checkpoint every 100 batches
                if (i//batch_size + 1) % 100 == 0:
                    checkpoint_file = f"data/embeddings/embeddings_checkpoint_{i + batch_size}.json"
                    save_json(upsert_data, checkpoint_file)
                    logger.info(f"Saved checkpoint to {checkpoint_file}")
                
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                # Save checkpoint on error
                checkpoint_file = f"data/embeddings/embeddings_checkpoint_{i}.json"
                save_json(upsert_data, checkpoint_file)
                logger.info(f"Saved checkpoint to {checkpoint_file}")
                continue
        
        logger.info(f"Completed embedding. Created {len(upsert_data)} vectors")
        return upsert_data
        
    except Exception as e:
        logger.error(f"Fatal error in embedding process: {e}")
        raise

def save_embeddings(embeddings_data: List[dict], output_file: str = EMBEDDINGS_OUTPUT):
    """Save the embeddings list to a JSON file."""
    logger.info(f"Saving {len(embeddings_data)} embeddings to {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
    logger.info("Embeddings saved successfully")

def process_batch(batch_data, embeddings_file="embeddings_registry.json"):
    """Process a batch of documents and save embeddings"""
    # Load existing embeddings registry
    existing_embeddings = {}
    if os.path.exists(embeddings_file):
        with open(embeddings_file, 'r') as f:
            existing_embeddings = json.load(f)
    
    # Process only new or updated documents
    documents = []
    for item in batch_data:
        url = item['url']
        if url not in existing_embeddings or \
           existing_embeddings[url]['last_modified'] < item['metadata']['last_modified']:
            chunks = chunk_texts([item])
            documents.extend(chunks)
    
    if not documents:
        return []
    
    # Create embeddings for new/updated documents
    embedded_data = embed_documents(documents)
    
    # Update embeddings registry
    for doc in embedded_data:
        url = doc['metadata']['source']
        existing_embeddings[url] = {
            'last_modified': doc['metadata']['last_modified'],
            'vector_ids': doc['id']
        }
    
    # Save updated registry
    with open(embeddings_file, 'w') as f:
        json.dump(existing_embeddings, f, indent=2)
    
    return embedded_data

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

def main():
    logger.info("Starting ingest process")
    
    try:
        data = load_scraped_data("scraped_data.json")
        documents = chunk_texts(data)
        embedded_data = embed_documents(documents)
        save_embeddings(embedded_data, EMBEDDINGS_OUTPUT)
        logger.info("Ingest process completed successfully")
        
    except Exception as e:
        logger.error(f"Error in ingest process: {e}")
        raise

if __name__ == "__main__":
    main()
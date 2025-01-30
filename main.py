import os
from dotenv import load_dotenv
import logging
import json
from pathlib import Path
import time
from create_index import init_pinecone, create_or_get_index, upsert_embeddings

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 5  # Process 5 documents at a time

def process_in_batches(data, pinecone_index, namespace="development"):
    """Process documents in small batches"""
    from ingest import chunk_texts, embed_documents, save_embeddings
    
    total_documents = len(data)
    processed_count = 0
    
    # Process in small batches
    for i in range(0, total_documents, BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(total_documents + BATCH_SIZE - 1)//BATCH_SIZE}")
        
        try:
            # 1. Chunk the batch (with smaller chunk size)
            documents = chunk_texts(batch, chunk_size=500)  # Reduced chunk size
            logger.info(f"Created {len(documents)} chunks from {len(batch)} documents")
            
            # 2. Create embeddings
            embedded_data = embed_documents(documents)
            
            # 3. Save embeddings (append to file)
            if i == 0:
                # First batch - create new file
                save_embeddings(embedded_data, "embeddings.json")
            else:
                # Append to existing file
                with open("embeddings.json", "r+") as f:
                    existing_data = json.load(f)
                    existing_data.extend(embedded_data)
                    f.seek(0)
                    f.truncate()  # Clear the rest of the file
                    json.dump(existing_data, f)
            
            # 4. Upload to Pinecone
            pinecone_index.upsert(
                vectors=embedded_data,
                namespace=namespace
            )
            
            processed_count += len(batch)
            logger.info(f"Progress: {processed_count}/{total_documents} documents processed")
            
        except Exception as e:
            logger.error(f"Error processing batch {i//BATCH_SIZE + 1}: {str(e)}")
            logger.exception("Full error:")  # This will print the full stack trace
            continue

def main():
    # Initialize Pinecone
    pc, cloud, region = init_pinecone()
    index = create_or_get_index(os.getenv("PINECONE_ENVIRONMENT", "greenburgh"))
    
    # Check for existing files
    scraped_data_exists = Path("scraped_data.json").exists()
    
    # Ask user what to do
    if scraped_data_exists:
        rescrape = input("Scraped data already exists. Rescrape? (y/n): ").lower() == 'y'
    else:
        rescrape = True
    
    # 1. Scrape (if needed)
    if rescrape:
        from scraper import crawl_website
        logger.info("Starting web scraping...")
        data = crawl_website()
    else:
        logger.info("Loading existing scraped data...")
        with open("scraped_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    
    # 2. Process and embed in batches
    logger.info(f"Processing {len(data)} documents in batches of {BATCH_SIZE}")
    process_in_batches(data, index)
    
    # 3. Start QA interface
    from qa_chain import create_qa_chain
    logger.info("Starting QA interface...")
    chain = create_qa_chain(use_cli=True)
    
    # Interactive QA loop
    print("\nEnter your questions about Greenburgh (or 'quit' to exit):")
    while True:
        query = input("\nQuestion: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        result = chain({"query": query})
        print("\nAnswer:", result['result'])
        
        if result.get('source_documents'):
            print("\nSources:")
            for doc in result['source_documents']:
                print(f"- {doc.metadata['source']}")

if __name__ == "__main__":
    main() 
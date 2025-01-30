import os
import json
from pathlib import Path
import shutil
from scraper import crawl_website
from ingest import chunk_texts, embed_documents, save_embeddings, process_batch
from create_index import init_pinecone, create_or_get_index, upsert_embeddings
from dotenv import load_dotenv
import time
from qa_chain import create_qa_chain

# Load environment variables for Pinecone
load_dotenv()

# Test configuration
TEST_URL = "https://www.greenburghny.com/CivicAlerts.aspx?AID=2832"
TEST_MAX_DEPTH = 0  # Only scrape the single page
TEST_OUTPUT_DIR = "test_output"
TEST_SCRAPED_DATA = os.path.join(TEST_OUTPUT_DIR, "test_scraped_data.json")
TEST_EMBEDDINGS = os.path.join(TEST_OUTPUT_DIR, "test_embeddings.json")
TEST_INDEX_NAME = os.getenv("PINECONE_INDEX", "greenburgh")  # Use environment name as index
TEST_NAMESPACE = "test"  # Always use 'test' namespace for testing

def setup_test():
    """Create test directory and clean any previous test data"""
    print("\n=== Setting up test environment ===")
    # Create test output directory
    Path(TEST_OUTPUT_DIR).mkdir(exist_ok=True)

def test_scraping(force_rescrape=False):
    """Test the scraping functionality with batches"""
    print("\n=== Testing web scraping ===")
    
    total_processed = 0
    for batch in crawl_website(start_url=TEST_URL, max_depth=TEST_MAX_DEPTH):
        print(f"Processing batch of {len(batch)} pages...")
        
        # Process this batch
        embedded_data = process_batch(batch)
        if embedded_data:
            # Upload to Pinecone
            upsert_embeddings(index, embedded_data, TEST_NAMESPACE)
            print(f"Uploaded {len(embedded_data)} vectors to Pinecone")
        
        total_processed += len(batch)
    
    print(f"Total pages processed: {total_processed}")
    return total_processed

def test_ingestion(data, force_reembed=False):
    """Test the ingestion and embedding process"""
    print("\n=== Testing ingestion and embedding ===")
    
    # Check for cached embeddings
    if os.path.exists(TEST_EMBEDDINGS) and not force_reembed:
        print("Using cached embeddings...")
        with open(TEST_EMBEDDINGS, 'r', encoding='utf-8') as f:
            embedded_data = json.load(f)
        print(f"Loaded {len(embedded_data)} cached embeddings")
    else:
        print("Creating new embeddings...")
        # Create chunks
        documents = chunk_texts(data)
        print(f"Created {len(documents)} chunks")
        assert len(documents) > 0, "No chunks were created"
        
        # Create embeddings
        embedded_data = embed_documents(documents)
        print(f"Created embeddings for {len(embedded_data)} chunks")
        assert len(embedded_data) == len(documents), "Mismatch between chunks and embeddings"
        
        # Save embeddings
        save_embeddings(embedded_data, TEST_EMBEDDINGS)
        print(f"Saved embeddings to {TEST_EMBEDDINGS}")
    
    # Verify embeddings structure
    assert len(embedded_data) > 0, "No embeddings were loaded/created"
    assert "values" in embedded_data[0], "Embedding values missing"
    assert "metadata" in embedded_data[0], "Metadata missing"
    
    return embedded_data

def test_pinecone_upload(embedded_data, force_upload=False):
    """Test uploading to Pinecone"""
    print("\n=== Testing Pinecone upload ===")
    
    # Initialize Pinecone
    print("Initializing Pinecone...")
    pc, cloud, region = init_pinecone()  # Updated to get cloud and region
    print(f"Using cloud: {cloud}, region: {region}")
    
    # Create or get index
    print(f"Creating/getting index: {TEST_INDEX_NAME}")
    index = create_or_get_index(TEST_INDEX_NAME)
    
    # Check if vectors already exist in this namespace
    stats = index.describe_index_stats()
    namespace_stats = stats.get('namespaces', {}).get(TEST_NAMESPACE, {})
    existing_count = namespace_stats.get('vector_count', 0)
    
    if existing_count > 0 and not force_upload:
        print(f"Found {existing_count} existing vectors in namespace '{TEST_NAMESPACE}'")
        print("Skipping upload to avoid duplicates (use --force-upload to override)")
        return existing_count
    
    if force_upload and existing_count > 0:
        print(f"Force uploading despite {existing_count} existing vectors...")
    else:
        print(f"Namespace '{TEST_NAMESPACE}' is empty, uploading vectors...")
        
    upsert_embeddings(index, TEST_EMBEDDINGS, TEST_NAMESPACE)
    
    # Add a delay to allow Pinecone to update stats
    print("Waiting for Pinecone to update stats...")
    time.sleep(5)  # Wait 5 seconds
    
    # Verify upload by checking vector count
    stats = index.describe_index_stats()
    print(f"Index stats: {stats}")
    namespace_stats = stats.get('namespaces', {}).get(TEST_NAMESPACE, {})
    vector_count = namespace_stats.get('vector_count', 0)
    print(f"Vectors in Pinecone: {vector_count}")
    assert vector_count > 0, "No vectors found in Pinecone after upload"
    
    return vector_count

def test_qa_chain():
    """Test the QA chain with a specific question"""
    print("\n=== Testing QA Chain ===")
    
    # Create the QA chain
    print("Creating QA chain...")
    chain = create_qa_chain(use_cli=True)
    
    # Test question
    test_question = "What's the last date to file taxes without incurring a penalty?"
    print(f"\nTest Question: {test_question}")
    
    # Get response
    result = chain({"query": test_question})
    answer = result.get('result', '')
    sources = result.get('source_documents', [])
    
    print("\nAnswer:", answer)
    
    if sources:
        print("\nSources:")
        for doc in sources:
            print(f"- {doc.metadata['source']}")
    
    # Basic validation
    assert answer, "No answer received from QA chain"
    assert "Jan" in answer or "January" in answer, "Expected answer to mention January"
    
    return result

def main():
    try:
        # Add command line arguments
        import sys
        force_rescrape = "--rescrape" in sys.argv
        force_reembed = "--reembed" in sys.argv
        force_upload = "--force-upload" in sys.argv
        
        setup_test()
        
        # Run tests
        total_processed = test_scraping(force_rescrape)
        embedded_data = test_ingestion(scraped_data, force_reembed)
        vector_count = test_pinecone_upload(embedded_data, force_upload)
        qa_result = test_qa_chain()  # Added QA chain test
        
        print("\n=== Test Summary ===")
        print(f"✓ Successfully loaded/scraped {total_processed} pages")
        print(f"✓ Successfully loaded/created {len(embedded_data)} embeddings")
        print(f"✓ Found/uploaded {vector_count} vectors in Pinecone")
        print(f"✓ Successfully tested QA chain")
        print(f"\nTest files saved in {TEST_OUTPUT_DIR}/")
        print("All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main() 
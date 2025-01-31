# Greenburgh RAG System

A RAG (Retrieval-Augmented Generation) system for the Greenburgh website, using web scraping, Ollama embeddings, and Pinecone vector database.

## Setup
bash
python3 -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate


2. **Install requirements**
bash
pip install -r venv/requirements.txt

3. **Create .env file with your credentials**

bash
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=your_environment # e.g., "us-east-1-aws"
MAX_DEPTH=5
START_URL=https://www.greenburghny.com/


## Testing Suite

The testing suite provides tools for testing the scraping, embedding, and vector database upload pipeline.

### Quick Start

Basic test run:
bash
python venv/test_flow.py


This will:
1. Use cached scraped data if available
2. Use cached embeddings if available
3. Skip Pinecone upload if vectors already exist

### Command Line Options

Control each step of the pipeline with these flags:

- `--rescrape`: Force new web scraping
- `--reembed`: Force new embeddings generation
- `--force-upload`: Force Pinecone upload

Examples:
bash
Force everything to be redone
python venv/test_flow.py --rescrape --reembed --force-upload
Use cached scraping but create new embeddings
python venv/test_flow.py --reembed
Use cached data but force upload to Pinecone
python venv/test_flow.py --force-upload

### Test Files Structure

- `test_flow.py`: Main test orchestration script
- `test_output/`: Directory containing cached data
  - `test_scraped_data.json`: Cached web scraping results
  - `test_embeddings.json`: Cached embeddings

### Pipeline Steps

1. **Web Scraping**
   - Scrapes single test URL
   - Caches results
   - Use `--rescrape` to force new scraping

2. **Embedding Generation**
   - Creates embeddings using Ollama
   - Caches results
   - Use `--reembed` to force regeneration

3. **Pinecone Upload**
   - Uploads vectors to Pinecone
   - Uses "test" namespace
   - Use `--force-upload` to force new upload

### Configuration

Default test settings:
- Test URL: `https://www.greenburghny.com/CivicAlerts.aspx?AID=2832`
- Pinecone Index: `greenburgh`
- Pinecone Namespace: `test`
- Output Directory: `test_output/`

### Output Example



## Project Structure

- `scraper.py`: Web scraping functionality
- `ingest.py`: Text processing and embedding generation
- `create_index.py`: Pinecone index management
- `qa_chain.py`: Question-answering chain
- `main.py`: Main application script
- `test_flow.py`: Testing suite


For development, use different flag combinations:


## Error Handling

The test script provides clear error messages for:
- Failed web scraping
- Failed embedding generation
- Failed Pinecone uploads
- Missing environment variables

## Caching Behavior

- Scraped data and embeddings are cached by default
- Pinecone uploads are skipped if vectors exist
- Use force flags to override caching


### Let me explain the difference between Pinecone environment and index:

#### **Pinecone Environment**
- This is your cloud deployment environment where all your indexes live.
- It's associated with a specific cloud region (like `"us-east-1-aws"`).
- You set this in your `.env` file as `PINECONE_ENVIRONMENT`.
- One environment can host multiple indexes.
- **Think of it like your "database server".**

#### **Pinecone Index**
- This is a specific vector database within your environment.
- Each index has its own:
  - **Dimension size** (e.g., 4096 for Ollama embeddings).
  - **Metric type** (e.g., we use `"cosine"`).
  - **Multiple namespaces** (e.g., `"test"`, `"prod"`, etc.).
- **Think of it like a "database" within your server.**

---

#### **Here's an analogy:**
- The **Pinecone Environment** is like a **"database server"**.
- The **Pinecone Index** is like a **"database"** hosted within that server.

Pinecone Environment (like a database server)
└── Index "greenburgh" (like a database)
    ├── Namespace "test" (like a table)
    │   └── 32 vectors (like rows)
    └── Namespace "prod"
        └── X vectors
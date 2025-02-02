# Search Configuration and Tuning

## Model Choices

### LLM Model
Using `gpt-4-turbo-preview` for inference because:
- Faster response times
- Lower cost ($0.01/1K input tokens, $0.03/1K output tokens)
- 128K context window
- Better instruction following

### Embedding Model
Using `text-embedding-3-small` for embeddings because:
- 1536 dimensions
- Good balance of performance and cost
- Integrates well with our Pinecone vector store

## Search Parameters

### Retrieval Configuration
- Number of chunks retrieved (k=5)
- Search type: similarity
- Metric: cosine similarity

### Prompt Template
Custom prompt designed for Greenburgh context with:
- Clear role definition
- Instruction to not make up information
- Professional tone for government context

## Pinecone Configuration
- Dimension: 1536 (matching embedding model)
- Metric: cosine
- Region: us-east-1
- Serverless spec for better scaling

## Chunking Strategy
- Chunk size: 1000 characters
- Chunk overlap: 200 characters
- Preserves context while maintaining granularity

## Future Tuning Considerations
- Adjust k value based on answer completeness
- Fine-tune temperature (currently 0.7) based on response variety needs
- Monitor and adjust chunk size based on answer quality

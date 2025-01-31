

There are several key parameters we can tune across different parts of the pipeline to affect answer quality:

1. **Chunking Parameters** (scripts/03_create_chunks.py):
```python
# Chunk size affects how much context each embedding has
chunk_size = 1000  # Can be increased/decreased
chunk_overlap = 200  # Controls how much chunks overlap
```
- Larger chunks = more context but less precise matching
- Smaller chunks = more precise matching but might miss broader context
- More overlap = better context preservation between chunks

2. **Retrieval Parameters** (src/qa_chain.py):
```python
# In create_qa_chain():
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}  # Number of chunks to retrieve
)
```
- Increase k for more comprehensive but potentially noisier answers
- Decrease k for more focused but potentially incomplete answers

3. **Prompt Template** (src/qa_chain.py):
```python
prompt_template = """You are a helpful assistant for the Town of Greenburgh, NY. 
Use the following pieces of context to answer the question at the end. 
If you don't know the answer, apologize and say you were unable to find that information, don't try to make up an answer.

Context:
{context}

Question: {question}

Answer: Let me help you with that information about the Town of Greenburgh."""
```
- Can be modified to encourage more detailed/concise responses
- Can add instructions about formatting, tone, or detail level

4. **LLM Parameters** (src/qa_chain.py):
```python
llm = Ollama(
    model="llama2", 
    base_url="http://localhost:11434"
    # Can add parameters like:
    # temperature=0.7,
    # max_tokens=500
)
```
- Lower temperature (0.1-0.4) = more focused, precise answers
- Higher temperature (0.7-1.0) = more creative, varied answers
- Adjust max_tokens to control answer length

Would you like me to provide specific examples of how to modify any of these parameters for different use cases?

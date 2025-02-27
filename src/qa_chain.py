import os
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import pinecone
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

def init_pinecone():
    """Initialize Pinecone client and index"""
    pinecone.init(
        api_key=os.getenv('PINECONE_API_KEY'),
        environment=os.getenv('PINECONE_ENVIRONMENT')
    )
    
    index_name = os.getenv('PINECONE_INDEX')
    
    # Delete existing index if it exists
    if index_name in pinecone.list_indexes():
        pinecone.delete_index(index_name)
    
    # Create new index with correct dimensions
    pinecone.create_index(
        name=index_name,
        dimension=1536,  # Match text-embedding-3-small dimensions
        metric='cosine'
    )
    
    return pinecone.Index(index_name)

def create_qa_chain(use_cli=False):
    """Create a QA chain using Pinecone for retrieval and OpenAI for generation."""
    
    # Get the index
    index_name = os.getenv("PINECONE_INDEX")
    
    # Initialize Pinecone
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index(index_name)
    
    # Create embeddings instance - using OpenAI embeddings
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create vectorstore
    vectorstore = LangchainPinecone(
        index,
        embeddings,
        "text",  # metadata field that contains the text
        namespace=os.getenv("PINECONE_NAMESPACE", "prod")
    )
    
    # Create retriever
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}
    )
    
    # Create OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Add a custom prompt template for Greenburgh
    prompt_template = """You are a helpful assistant for the Town of Greenburgh, NY. Use the following pieces of context to answer the question at the end. If you don't know the answer, apologize and say you were unable to locate that information, don't try to make up an answer.

Context:
{context}

Question: {question}

Answer: Let me help you with that information about the Town of Greenburgh."""
    
    # Create QA chain with custom prompt
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={
            "prompt": PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            ),
        }
    )
    
    return qa_chain

def upload_to_pinecone(embeddings_data, namespace=None):
    """Upload embeddings to Pinecone index"""
    # Get the index
    index_name = os.getenv('PINECONE_INDEX')
    
    # Initialize Pinecone
    pc = Pinecone(
        api_key=os.getenv('PINECONE_API_KEY')
    )
    
    # Use namespace from env var if not provided
    if namespace is None:
        namespace = os.getenv('PINECONE_NAMESPACE', 'prod')
    
    # Get or create index
    try:
        index = pc.Index(index_name)
    except Exception as e:
        # If index doesn't exist, create it
        pc.create_index(
    name=index_name,
    dimension=1536, # Replace with your model dimensions
    metric="cosine", # Replace with your model metric
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    ) 
)
        index = pc.Index(index_name)
    
    # Prepare vectors for upload
    vectors = [
        (
            item['id'],
            item['values'],
            item['metadata']
        )
        for item in embeddings_data
    ]
    
    # Upload in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)
    
    return len(vectors)

if __name__ == "__main__":
    chain = create_qa_chain(use_cli=True)
    while True:
        question = input("\nQuestion (or 'quit'): ")
        if question.lower() in ['quit', 'exit', 'q']:
            break
            
        result = chain({"query": question})
        print("\nAnswer:", result['result'])
        
        if result.get('source_documents'):
            print("\nSources:")
            for doc in result['source_documents']:
                print(f"- {doc.metadata['source']}")
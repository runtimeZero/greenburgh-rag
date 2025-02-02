import sys
from pathlib import Path
import pdfplumber
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.append(str(src_dir))

from utils.file_utils import (
    load_json,
    save_json,
    get_processing_status_file,
    get_chunks_file_path,
    get_embeddings_file_path,
)
from ingest import chunk_texts, embed_documents
from qa_chain import upload_to_pinecone
from langchain.docstore.document import Document


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            documents = []
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    documents.append(
                        {
                            "text": text,
                            "metadata": {"source": str(pdf_path), "page": page_num},
                        }
                    )
            return documents
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return None


def main():
    # Load status file
    status_file = get_processing_status_file()
    status = load_json(status_file) or {}

    # Get all PDFs in data/pdfs
    pdf_dir = Path("data/pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files")

    for pdf_file in pdf_files:
        pdf_path = str(pdf_file)
        print(f"\nChecking {pdf_path}")

        # Check if already fully processed
        if (
            pdf_path in status
            and status[pdf_path].get("status") == "completed"
            and status[pdf_path].get("stage") == "uploaded"
        ):
            print(f"Skipping {pdf_path} - already processed")
            continue

        print(f"Processing {pdf_path}")

        # Create status entry for PDF if not exists
        if pdf_path not in status:
            status[pdf_path] = {
                "status": "pending",
                "stage": "discovered",
                "last_updated": datetime.utcnow().isoformat(),
            }

        try:
            # 1. Extract text and create documents
            print("Extracting text...")
            documents = extract_text_from_pdf(pdf_file)
            if not documents:
                raise Exception("Failed to extract text")

            # 2. Create chunks using existing chunking function
            print("Creating chunks...")
            chunks = chunk_texts(documents)
            chunks_dict = [
                {"page_content": chunk.page_content, "metadata": chunk.metadata}
                for chunk in chunks
            ]

            # Save chunks
            chunks_file = get_chunks_file_path(str(pdf_file))
            chunks_file.parent.mkdir(parents=True, exist_ok=True)
            save_json(chunks_dict, chunks_file)

            # Update status
            status[str(pdf_file)].update(
                {
                    "status": "completed",
                    "stage": "chunked",
                    "chunks_count": len(chunks_dict),
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )
            save_json(status, status_file)
            print(f"Created {len(chunks_dict)} chunks")

            # 3. Create embeddings using existing embedding function
            print("Creating embeddings...")
            embeddings_data = embed_documents(chunks)

            # Save embeddings
            embeddings_file = get_embeddings_file_path(str(pdf_file))
            embeddings_file.parent.mkdir(parents=True, exist_ok=True)
            save_json(embeddings_data, embeddings_file)

            # Update status
            status[str(pdf_file)].update(
                {
                    "status": "completed",
                    "stage": "embedded",
                    "embeddings_count": len(embeddings_data),
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )
            save_json(status, status_file)
            print(f"Created {len(embeddings_data)} embeddings")

            # 4. Upload to Pinecone using existing upload function
            print("Uploading to Pinecone...")
            uploaded_count = upload_to_pinecone(embeddings_data)

            # Update status
            status[str(pdf_file)].update(
                {
                    "status": "completed",
                    "stage": "uploaded",
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )
            save_json(status, status_file)
            print(f"Uploaded {uploaded_count} vectors to Pinecone")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            status[str(pdf_file)].update(
                {
                    "status": "failed",
                    "error": str(e),
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )
            save_json(status, status_file)


if __name__ == "__main__":
    main()

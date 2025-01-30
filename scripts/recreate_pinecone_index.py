import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from qa_chain import init_pinecone

def main():
    print("Recreating Pinecone index...")
    init_pinecone()
    print("Done!")

if __name__ == "__main__":
    main() 
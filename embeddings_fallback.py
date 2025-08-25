# Alternative vector store configuration with local model fallback
import os
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings

def create_embeddings_with_fallback():
    """Create embeddings with fallback options for deployment environments"""
    
    # Try the standard approach first
    try:
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_folder=os.getenv('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
        )
    except Exception as e:
        print(f"Failed to load standard embeddings: {e}")
        
        # Fallback: try to use a local model if available
        try:
            # This will work if the model was pre-downloaded during build
            model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            from langchain.embeddings import SentenceTransformerEmbeddings
            return SentenceTransformerEmbeddings(model=model)
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            raise Exception(f"Unable to load embeddings. Original error: {e}, Fallback error: {e2}")

# Usage in your vector_store.py:
# self.embeddings = create_embeddings_with_fallback()
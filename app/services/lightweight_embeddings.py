"""
Lightweight embeddings service for memory-constrained environments
Uses smaller models and lazy loading to minimize memory usage
"""

import os
import logging
from typing import List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class LightweightEmbeddings(ABC):
    """
    Memory-efficient embeddings using smaller models
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None  # Lazy loading
        
    def _get_model(self):
        """Lazy load the model only when needed"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading lightweight model: {self.model_name}")
                self._model = SentenceTransformer(
                    self.model_name,
                    cache_folder=os.getenv('HF_HOME', os.path.expanduser('~/.cache/huggingface')),
                    device='cpu'  # Force CPU usage
                )
                logger.info("Lightweight embeddings model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise
        return self._model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents with batch processing to save memory"""
        model = self._get_model()
        
        # Process in small batches to reduce memory usage
        batch_size = 8  # Very small batch size
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = model.encode(
                batch,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            embeddings.extend(batch_embeddings.tolist())
            
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        return self.embed_documents([text])[0]


def create_memory_efficient_embeddings():
    """
    Create embeddings optimized for low memory environments
    Fallback chain for different deployment scenarios
    """
    
    # Try ultra-lightweight approach first
    try:
        logger.info("Attempting lightweight embeddings...")
        return LightweightEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        logger.warning(f"Lightweight embeddings failed: {e}")
        
        # Fallback to even smaller model
        try:
            logger.info("Trying smaller model...")
            return LightweightEmbeddings("sentence-transformers/paraphrase-MiniLM-L3-v2")
        except Exception as e2:
            logger.error(f"All embedding options failed: {e2}")
            raise Exception(f"Cannot initialize embeddings. Error: {e2}")

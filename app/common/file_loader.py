from typing import List
import os
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)
from app.common.logger import get_logger

logger = get_logger(__name__)

class FileLoader:
    def __init__(self):
        self.supported_extensions = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.docx': Docx2txtLoader,
            '.doc': Docx2txtLoader,
            '.md': TextLoader  # ✅ Add markdown support
        }
    
    def load_file(self, file_path: str) -> List[Document]:
        """Load a single file and return documents"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension not in self.supported_extensions:
            raise ValueError(
                f"Unsupported file type: {file_extension}. "
                f"Supported types: {list(self.supported_extensions.keys())}"
            )
        
        try:
            loader_class = self.supported_extensions[file_extension]
            loader = loader_class(file_path)
            documents = loader.load()
            
            # Add file path to metadata
            for doc in documents:
                doc.metadata['source_file'] = file_path
                doc.metadata['file_type'] = file_extension
            
            logger.info(f"Loaded {len(documents)} documents from {file_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            raise
    
    def load_multiple_files(self, file_paths: List[str]) -> List[Document]:
        """Load multiple files and return all documents"""
        all_documents = []
        
        for file_path in file_paths:
            try:
                documents = self.load_file(file_path)
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {str(e)}")
                continue  # Continue with other files
        
        return all_documents
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return list(self.supported_extensions.keys())

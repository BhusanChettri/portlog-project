"""Retriever - retrieves relevant context from vector database for RAG."""

import json
import os.path as osp
from pathlib import Path
from typing import List, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.config.settings import get_settings
from src.config.env_loader import load_environment_variables
from src.config.logging_config import get_logger
from src.config.messages import DEFAULT_UNKNOWN_SOURCE

# Load environment variables
load_environment_variables()

logger = get_logger(__name__)


class RAGRetriever:
    """Retrieve relevant context from vector database for RAG.
    
    This class handles document loading, chunking, embedding, and retrieval
    from a ChromaDB vector store. It provides context for the response generator
    to create more informative answers.
    
    Features:
    - Uses RecursiveCharacterTextSplitter with configurable chunk_size and chunk_overlap
    - Combines all PDF pages into one text, then splits into chunks
    - ChromaDB with persistence for efficient retrieval
    - Formats retrieved documents as pretty JSON for LLM consumption
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        chroma_db_dir: Optional[Path] = None,
        collection_name: str = None
    ):
        """
        Initialize RAG retriever.
        
        Args:
            data_dir: Directory containing PDF documents (defaults to config)
            chroma_db_dir: Directory for ChromaDB persistence (defaults to config)
            collection_name: ChromaDB collection name (defaults to config)
        """
        settings = get_settings()
        # Calculate project directory once
        project_dir = Path(__file__).parent.parent.parent
        if data_dir is None:
            data_dir = settings.get_data_dir(project_dir)
        if chroma_db_dir is None:
            chroma_db_dir = settings.get_chroma_db_dir(project_dir)
        if collection_name is None:
            collection_name = settings.chroma_collection_name
        
        self.data_dir = data_dir
        self.chroma_db_dir = chroma_db_dir
        self.collection_name = collection_name
        self.embeddings = None
        self.vector_store = None
    
    def initialize(self):
        """Initialize embeddings and vector store.
        
        Sets up OpenAI embeddings and ChromaDB vector store. If documents
        already exist in the database, reuses them. Otherwise, loads and
        processes PDF documents, creates embeddings, and stores them.
        
        Raises:
            FileNotFoundError: If PDF file is not found in data_dir
        """
        logger.info("Initializing RAG retriever...")
        
        # Initialize embeddings model
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(model=settings.embedding_model)
        
        # Initialize persistent Chroma vector database
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=str(self.chroma_db_dir),
            collection_name=self.collection_name,
        )
        
        # Check if documents already exist
        has_existing_documents = len(self.vector_store.get(limit=1)['ids']) > 0
        if has_existing_documents:
            logger.info("ChromaDB found - reusing existing documents.")
        else:
            logger.info("No existing ChromaDB found - processing and embedding documents...")
            docs = self._load_and_process_documents()
            logger.info(f"Loaded and chunked {len(docs)} document pieces")
            self.vector_store.add_documents(docs)
            logger.info("Embeddings processed and stored in ChromaDB.")
    
    def _load_and_process_documents(self) -> List[Document]:
        """Load PDFs and split them into smaller chunks suitable for embeddings.
        
        Loads the port tariff PDF, combines all pages into a single text,
        then splits into chunks using RecursiveCharacterTextSplitter.
        Each chunk is wrapped in a Document object with source metadata.
        
        Returns:
            List of Document objects, each containing a text chunk and metadata
        
        Raises:
            FileNotFoundError: If PDF file is not found
        """
        docs = []
        settings = get_settings()
        pdf_path = self.data_dir / settings.pdf_filename
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Loading {osp.basename(pdf_path)}")
        loader = PyPDFLoader(str(pdf_path))
        page_docs = loader.load()
        
        # Combine all pages into one text
        combined_text = "\n".join([doc.page_content for doc in page_docs])
        
        # Use configurable splitter settings
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap
        )
        chunks = text_splitter.split_text(combined_text)
        
        # Create Document objects with source metadata
        docs.extend([
            Document(page_content=chunk, metadata={"source": str(pdf_path)})
            for chunk in chunks
        ])
        
        return docs
    
    def retrieve(self, query: str, k: int = None) -> List[Document]:
        """Retrieve relevant documents for a query using similarity search.
        
        Uses ChromaDB's similarity_search to find the k most relevant
        document chunks for the given query based on embedding similarity.
        
        Args:
            query: Search query string
            k: Number of documents to retrieve (defaults to config)
        
        Returns:
            List of Document objects, ordered by relevance (most relevant first)
        
        Raises:
            RuntimeError: If retriever has not been initialized (initialize() not called)
        """
        if self.vector_store is None:
            raise RuntimeError("RAG retriever not initialized. Call initialize() first.")
        
        # Use config default if k not provided
        if k is None:
            settings = get_settings()
            k = settings.rag_retrieval_count
        
        # Use similarity_search
        docs = self.vector_store.similarity_search(query, k=k)
        
        return docs
    
    def retrieve_context(self, query: str, k: int = None) -> str:
        """Retrieve relevant context as formatted string for LLM consumption.
        
        Retrieves documents and formats them as a pretty JSON string with
        newlines between documents. This format is optimized for inclusion
        in LLM prompts.
        
        Args:
            query: Search query string
            k: Number of documents to retrieve (defaults to config)
        
        Returns:
            Formatted context string as pretty JSON. Each document is formatted
            as: {"id": int, "filename": str, "content": str}
            Documents are separated by double newlines.
        """
        docs = self.retrieve(query, k)
        
        # Format retrieved documents as pretty JSON
        formatted_docs = []
        for idx, doc in enumerate(docs, 1):
            filename = osp.basename(doc.metadata.get("source", DEFAULT_UNKNOWN_SOURCE))
            formatted_doc = {
                "id": idx,
                "filename": filename,
                "content": doc.page_content
            }
            formatted_docs.append(formatted_doc)
        
        # Convert to pretty JSON string with newlines between documents
        formatted_json = "\n\n".join([
            json.dumps(doc, indent=2) 
            for doc in formatted_docs
        ])
        
        return formatted_json


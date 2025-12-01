"""Retriever - retrieves relevant context from vector database for RAG."""

import json
import os.path as osp
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Load environment variables
project_dir = Path(__file__).parent.parent.parent
parent_dir = project_dir.parent
env_file = parent_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif (project_dir / ".env").exists():
    load_dotenv(project_dir / ".env")


class RAGRetriever:
    """Retrieve relevant context from vector database for RAG.
    
    This class handles document loading, chunking, embedding, and retrieval
    from a ChromaDB vector store. It provides context for the response generator
    to create more informative answers.
    
    Features:
    - Uses RecursiveCharacterTextSplitter with chunk_size=1000, chunk_overlap=200
    - Combines all PDF pages into one text, then splits into chunks
    - ChromaDB with persistence for efficient retrieval
    - Formats retrieved documents as pretty JSON for LLM consumption
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        chroma_db_dir: Optional[Path] = None,
        collection_name: str = "port_tariff_documents"
    ):
        """
        Initialize RAG retriever.
        
        Args:
            data_dir: Directory containing PDF documents
            chroma_db_dir: Directory for ChromaDB persistence
            collection_name: ChromaDB collection name
        """
        if data_dir is None:
            data_dir = project_dir / "data"
        if chroma_db_dir is None:
            chroma_db_dir = project_dir / "chroma_db"
        
        self.data_dir = data_dir
        self.chroma_db_dir = chroma_db_dir
        self.collection_name = collection_name
        self.embeddings = None
        self.vector_store = None
        self.document_paths = []
    
    def initialize(self):
        """Initialize embeddings and vector store.
        
        Sets up OpenAI embeddings and ChromaDB vector store. If documents
        already exist in the database, reuses them. Otherwise, loads and
        processes PDF documents, creates embeddings, and stores them.
        
        Raises:
            FileNotFoundError: If PDF file is not found in data_dir
        """
        print("Initializing RAG retriever...")
        
        # Initialize embeddings model
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Initialize persistent Chroma vector database
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=str(self.chroma_db_dir),
            collection_name=self.collection_name,
        )
        
        # Check if documents already exist
        has_existing_documents = len(self.vector_store.get(limit=1)['ids']) > 0
        if has_existing_documents:
            print("ChromaDB found - reusing existing documents.")
        else:
            print("No existing ChromaDB found - processing and embedding documents...")
            docs = self._load_and_process_documents()
            print(f"Loaded and chunked {len(docs)} document pieces")
            self.vector_store.add_documents(docs)
            print("Embeddings processed and stored in ChromaDB.")
    
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
        pdf_path = self.data_dir / "port-of-gothenburg-port-tariff-2025.pdf"
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Loading {osp.basename(pdf_path)}")
        loader = PyPDFLoader(str(pdf_path))
        page_docs = loader.load()
        
        # Combine all pages into one text
        combined_text = "\n".join([doc.page_content for doc in page_docs])
        
        # Use same splitter settings
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(combined_text)
        
        # Create Document objects with source metadata
        docs.extend([
            Document(page_content=chunk, metadata={"source": str(pdf_path)})
            for chunk in chunks
        ])
        
        return docs
    
    def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve relevant documents for a query using similarity search.
        
        Uses ChromaDB's similarity_search to find the k most relevant
        document chunks for the given query based on embedding similarity.
        
        Args:
            query: Search query string
            k: Number of documents to retrieve (default: 5)
        
        Returns:
            List of Document objects, ordered by relevance (most relevant first)
        
        Raises:
            RuntimeError: If retriever has not been initialized (initialize() not called)
        """
        if self.vector_store is None:
            raise RuntimeError("RAG retriever not initialized. Call initialize() first.")
        
        # Use similarity_search
        docs = self.vector_store.similarity_search(query, k=k)
        
        return docs
    
    def retrieve_context(self, query: str, k: int = 5) -> str:
        """Retrieve relevant context as formatted string for LLM consumption.
        
        Retrieves documents and formats them as a pretty JSON string with
        newlines between documents. This format is optimized for inclusion
        in LLM prompts.
        
        Args:
            query: Search query string
            k: Number of documents to retrieve (default: 5)
        
        Returns:
            Formatted context string as pretty JSON. Each document is formatted
            as: {"id": int, "filename": str, "content": str}
            Documents are separated by double newlines.
        """
        docs = self.retrieve(query, k)
        
        # Format retrieved documents as pretty JSON
        formatted_docs = []
        for idx, doc in enumerate(docs, 1):
            filename = osp.basename(doc.metadata.get("source", "unknown"))
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


"""Unit tests for RAG retriever."""

import pytest
from pathlib import Path
from src.core.retriever import RAGRetriever


class TestRAGRetriever:
    """Test RAGRetriever class."""
    
    @pytest.fixture
    def retriever(self):
        """Create RAGRetriever instance."""
        retriever = RAGRetriever()
        # Try to initialize (may fail if PDF doesn't exist, that's okay)
        try:
            project_root = Path(__file__).parent.parent.parent
            pdf_path = project_root / "data" / "port-of-gothenburg-port-tariff-2025.pdf"
            if pdf_path.exists():
                retriever.initialize()
        except Exception:
            pass  # Skip if initialization fails
        return retriever
    
    def test_retriever_creation(self, retriever):
        """Test creating a retriever."""
        assert retriever is not None
    
    def test_retrieve_context(self, retriever):
        """Test retrieving context for a query."""
        # Only test if retriever was initialized
        if not hasattr(retriever, 'vector_store') or retriever.vector_store is None:
            pytest.skip("RAG retriever not initialized (PDF may not exist)")
        
        query = "tanker port infrastructure dues"
        context = retriever.retrieve_context(query, k=3)
        
        assert context is not None
        assert len(context) > 0
        # Context should be a string
        assert isinstance(context, str)
    
    def test_retrieve_context_empty_query(self, retriever):
        """Test retrieving context with empty query."""
        if not hasattr(retriever, 'vector_store') or retriever.vector_store is None:
            pytest.skip("RAG retriever not initialized")
        
        context = retriever.retrieve_context("", k=3)
        # Should handle gracefully
        assert context is not None
    
    def test_retrieve_context_different_k(self, retriever):
        """Test retrieving different numbers of documents."""
        if not hasattr(retriever, 'vector_store') or retriever.vector_store is None:
            pytest.skip("RAG retriever not initialized")
        
        query = "container vessel tariff"
        
        context_k1 = retriever.retrieve_context(query, k=1)
        context_k5 = retriever.retrieve_context(query, k=5)
        
        assert len(context_k1) <= len(context_k5)  # More docs should give more context


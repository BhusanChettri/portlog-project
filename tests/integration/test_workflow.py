"""Integration tests for complete workflow."""

import pytest
from src.core.workflow import TariffWorkflow, TariffWorkflowState


class TestTariffWorkflow:
    """Test complete tariff workflow."""
    
    @pytest.fixture
    def workflow(self):
        """Create and initialize workflow."""
        workflow = TariffWorkflow()
        workflow.initialize()
        return workflow
    
    def test_workflow_initialization(self, workflow):
        """Test workflow initialization."""
        assert workflow is not None
        assert workflow.graph is not None
        assert workflow.query_understanding is not None
        assert workflow.retriever is not None
        assert workflow.calculator is not None
        assert workflow.response_generator is not None
    
    def test_simple_tanker_query(self, workflow):
        """Test simple tanker query end-to-end."""
        query = "What is the cost for a 5000 GT tanker arriving from EU?"
        result = workflow.process(query)
        
        assert result is not None
        assert len(result) > 0
        assert "SEK" in result or "tariff" in result.lower()
    
    def test_container_vessel_query(self, workflow):
        """Test container vessel query."""
        query = "A 70,000 GT container vessel from Singapore will call once this week. What port charges apply?"
        result = workflow.process(query)
        
        assert result is not None
        assert len(result) > 0
    
    def test_query_with_sludge(self, workflow):
        """Test query with sludge volume."""
        query = "A tanker of 14000 GT arriving from EU will discharge 15 m3 of sludge. Calculate the total port tariff."
        result = workflow.process(query)
        
        assert result is not None
        assert len(result) > 0
    
    def test_query_understanding_node(self, workflow):
        """Test Node 1: Query Understanding."""
        state: TariffWorkflowState = {
            "query": "What is the cost for a 5000 GT tanker?",
            "parameters": None,
            "rag_context": "",
            "compiled_information": "",
            "calculation_result": None,
            "answer": ""
        }
        
        result = workflow._query_understanding_node(state)
        assert "parameters" in result
        assert result["parameters"] is not None
        assert result["parameters"].vessel_type is not None
    
    def test_retriever_node(self, workflow):
        """Test Node 2: Retriever."""
        state: TariffWorkflowState = {
            "query": "tanker port infrastructure dues",
            "parameters": None,
            "rag_context": "",
            "compiled_information": "",
            "calculation_result": None,
            "answer": ""
        }
        
        result = workflow._retriever_node(state)
        assert "rag_context" in result
        assert len(result["rag_context"]) > 0
    
    def test_compile_information_node(self, workflow):
        """Test Node 3: Compile Information."""
        # First get parameters
        state: TariffWorkflowState = {
            "query": "What is the cost for a 5000 GT tanker?",
            "parameters": None,
            "rag_context": "",
            "compiled_information": "",
            "calculation_result": None,
            "answer": ""
        }
        state = workflow._query_understanding_node(state)
        
        # Then compile information
        result = workflow._compile_information_node(state)
        assert "compiled_information" in result
        assert len(result["compiled_information"]) > 0
    
    def test_tariff_computation_node(self, workflow):
        """Test Node 4: Tariff Computation."""
        # Get parameters first
        state: TariffWorkflowState = {
            "query": "What is the cost for a 5000 GT tanker arriving from EU?",
            "parameters": None,
            "rag_context": "",
            "compiled_information": "",
            "calculation_result": None,
            "answer": ""
        }
        state = workflow._query_understanding_node(state)
        
        # Then compute
        result = workflow._tariff_computation_node(state)
        assert "calculation_result" in result
        assert result["calculation_result"] is not None
        assert "total" in result["calculation_result"]
        assert result["calculation_result"]["total"] >= 0
    
    def test_response_generator_node(self, workflow):
        """Test Node 5: Response Generator."""
        # Set up complete state
        state: TariffWorkflowState = {
            "query": "What is the cost for a 5000 GT tanker arriving from EU?",
            "parameters": None,
            "rag_context": "Sample RAG context about port tariffs.",
            "compiled_information": "Sample compiled information.",
            "calculation_result": {
                "total": 82850.0,
                "components": {"port_infrastructure_dues": 82850.0},
                "breakdown": [{"component": "port_infrastructure_dues", "cost": 82850.0}],
                "currency": "SEK"
            },
            "answer": ""
        }
        state = workflow._query_understanding_node(state)
        state["rag_context"] = "Sample RAG context."
        state["calculation_result"] = {
            "total": 82850.0,
            "components": {"port_infrastructure_dues": 82850.0},
            "breakdown": [{"component": "port_infrastructure_dues", "cost": 82850.0}],
            "currency": "SEK"
        }
        
        result = workflow._response_generator_node(state)
        assert "answer" in result
        assert len(result["answer"]) > 0
    
    def test_empty_query(self, workflow):
        """Test handling of empty query."""
        query = ""
        result = workflow.process(query)
        # Should handle gracefully (may return error message or empty response)
        assert result is not None
    
    def test_invalid_vessel_type(self, workflow):
        """Test query with invalid vessel type."""
        query = "What is the cost for a 5000 GT spaceship?"
        result = workflow.process(query)
        # Should handle gracefully
        assert result is not None


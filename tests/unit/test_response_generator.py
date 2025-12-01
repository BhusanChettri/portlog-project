"""Unit tests for response generator."""

import pytest
from src.core.response_generator import ResponseGenerator


class TestResponseGenerator:
    """Test ResponseGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create ResponseGenerator instance."""
        return ResponseGenerator()
    
    def test_generator_creation(self, generator):
        """Test creating a generator."""
        assert generator is not None
        assert generator.llm is not None
    
    def test_generate_response(self, generator):
        """Test generating a response."""
        query = "What is the cost for a 5000 GT tanker?"
        calculation_result = {
            "total": 82850.0,
            "components": {"port_infrastructure_dues": 82850.0},
            "breakdown": [
                {
                    "component": "port_infrastructure_dues",
                    "cost": 82850.0,
                    "rule_description": "Port infrastructure dues",
                    "details": {"rate": 3.04, "currency": "SEK"}
                }
            ],
            "currency": "SEK"
        }
        rag_context = "Port infrastructure dues are charged per GT based on vessel size bands."
        
        response = generator.generate(query, calculation_result, rag_context)
        
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)
    
    def test_generate_response_minimal(self, generator):
        """Test generating response with minimal inputs."""
        query = "Calculate tariff"
        calculation_result = {
            "total": 0.0,
            "components": {},
            "breakdown": [],
            "currency": "SEK"
        }
        rag_context = ""
        
        response = generator.generate(query, calculation_result, rag_context)
        
        assert response is not None
        assert isinstance(response, str)
    
    def test_generate_response_with_error(self, generator):
        """Test generating response when calculation has error."""
        query = "What is the cost?"
        calculation_result = {
            "total": 0.0,
            "components": {},
            "breakdown": [],
            "error": "Vessel type not identified",
            "currency": "SEK"
        }
        rag_context = ""
        
        response = generator.generate(query, calculation_result, rag_context)
        
        assert response is not None
        assert isinstance(response, str)
        # Should mention the error or provide helpful message


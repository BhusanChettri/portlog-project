"""Generate natural language response from calculator output and RAG context."""

from typing import Dict

from langchain.chat_models import init_chat_model

from src.prompts.response_prompts import RESPONSE_GENERATION_PROMPT
from src.config.settings import get_settings
from src.config.env_loader import load_environment_variables
from src.config.messages import (
    STATUS_NO_ADDITIONAL_CONTEXT,
    FORMAT_TOTAL_LABEL,
    FORMAT_BREAKDOWN_LABEL,
    FORMAT_RATE_LABEL,
    FORMAT_PER_UNIT,
)

# Load environment variables
load_environment_variables()


class ResponseGenerator:
    """Generate natural language response from calculation results and RAG context.
    
    Uses an LLM to combine deterministic calculation results with RAG-retrieved
    context to create a human-readable, informative response. This is the final
    node in the LangGraph workflow.
    """
    
    def __init__(self, llm_model: str = None, llm_provider: str = None):
        """
        Initialize response generator.
        
        Args:
            llm_model: LLM model to use (defaults to config)
            llm_provider: LLM provider (defaults to config)
        """
        settings = get_settings()
        llm_model = llm_model or settings.llm_model_response_generation
        llm_provider = llm_provider or settings.llm_provider
        self.llm = init_chat_model(llm_model, model_provider=llm_provider)
    
    def generate(
        self,
        query: str,
        calculation_result: Dict,
        rag_context: str
    ) -> str:
        """
        Generate response from calculation and context.
        
        Args:
            query: Original user query
            calculation_result: Result from calculator (as dict)
            rag_context: Context from RAG retriever
        
        Returns:
            Natural language response
        """
        # Format calculation result
        settings = get_settings()
        currency = calculation_result.get('currency', settings.default_currency)
        calc_str = f"{FORMAT_TOTAL_LABEL} {calculation_result['total']:.2f} {currency}\n\n"
        calc_str += f"{FORMAT_BREAKDOWN_LABEL}\n"
        for item in calculation_result.get('breakdown', []):
            calc_str += f"- {item['component']}: {item['cost']:.2f} {currency}\n"
            if 'details' in item:
                details = item['details']
                if 'rate' in details:
                    charging_method = details.get('charging_method', 'unit')
                    calc_str += f"  ({FORMAT_RATE_LABEL} {details['rate']} {details.get('currency', currency)} {FORMAT_PER_UNIT} {charging_method})\n"
        
        # Create chain with prompt template
        chain = RESPONSE_GENERATION_PROMPT | self.llm
        
        # Generate response
        response = chain.invoke({
            "query": query,
            "calculation_result": calc_str,
            "rag_context": rag_context or STATUS_NO_ADDITIONAL_CONTEXT
        })
        
        return response.content if hasattr(response, 'content') else str(response)


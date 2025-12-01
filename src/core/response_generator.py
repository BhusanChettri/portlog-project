"""Generate natural language response from calculator output and RAG context."""

from typing import Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

from langchain.chat_models import init_chat_model

from src.prompts.response_prompts import RESPONSE_GENERATION_PROMPT

# Load environment variables
project_dir = Path(__file__).parent.parent.parent
parent_dir = project_dir.parent
env_file = parent_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif (project_dir / ".env").exists():
    load_dotenv(project_dir / ".env")


class ResponseGenerator:
    """Generate natural language response from calculation results and RAG context.
    
    Uses an LLM to combine deterministic calculation results with RAG-retrieved
    context to create a human-readable, informative response. This is the final
    node in the LangGraph workflow.
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini", llm_provider: str = "openai"):
        """
        Initialize response generator.
        
        Args:
            llm_model: LLM model to use
            llm_provider: LLM provider
        """
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
        calc_str = f"Total: {calculation_result['total']:.2f} {calculation_result.get('currency', 'SEK')}\n\n"
        calc_str += "Breakdown:\n"
        for item in calculation_result.get('breakdown', []):
            calc_str += f"- {item['component']}: {item['cost']:.2f} {calculation_result.get('currency', 'SEK')}\n"
            if 'details' in item:
                details = item['details']
                if 'rate' in details:
                    calc_str += f"  (Rate: {details['rate']} {details.get('currency', 'SEK')} per {details.get('charging_method', 'unit')})\n"
        
        # Create chain with prompt template
        chain = RESPONSE_GENERATION_PROMPT | self.llm
        
        # Generate response
        response = chain.invoke({
            "query": query,
            "calculation_result": calc_str,
            "rag_context": rag_context or "No additional context available."
        })
        
        return response.content if hasattr(response, 'content') else str(response)


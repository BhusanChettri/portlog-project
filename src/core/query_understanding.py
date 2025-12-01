"""Query understanding - extracts structured parameters from natural language queries."""

from pathlib import Path
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model

from src.models.schema import VesselType
from src.models.query_models import QueryParameters
from src.prompts.query_prompts import QUERY_UNDERSTANDING_PROMPT

# Load environment variables
project_dir = Path(__file__).parent.parent.parent
parent_dir = project_dir.parent
env_file = parent_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif (project_dir / ".env").exists():
    load_dotenv(project_dir / ".env")


class QueryUnderstanding:
    """Extract structured parameters from natural language queries.
    
    Uses an LLM to parse natural language queries and extract structured
    parameters (vessel type, GT, arrival region, etc.) into a QueryParameters
    object. This is the first node in the LangGraph workflow.
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini", llm_provider: str = "openai"):
        """Initialize query understanding component.
        
        Args:
            llm_model: LLM model to use for query understanding (default: "gpt-4o-mini")
            llm_provider: LLM provider name (default: "openai")
        """
        self.llm = init_chat_model(llm_model, model_provider=llm_provider)
    
    def understand(self, query: str) -> QueryParameters:
        """Extract structured parameters from natural language query.
        
        Uses an LLM with structured output to parse the query and extract
        all relevant parameters including vessel type, specifications,
        call context, quantities, environmental info, etc.
        
        Args:
            query: Natural language query string from the user
        
        Returns:
            QueryParameters object containing all extracted structured data
        
        Raises:
            Exception: If LLM call fails or structured output parsing fails
        """
        # Get vessel types for prompt
        vessel_types = ", ".join([vt.value for vt in VesselType])
        
        # Create chain with prompt template
        chain = QUERY_UNDERSTANDING_PROMPT.partial(vessel_types=vessel_types) | self.llm.with_structured_output(QueryParameters)
        
        # Invoke chain
        result = chain.invoke({"query": query})
        
        return result


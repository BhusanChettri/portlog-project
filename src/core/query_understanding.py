"""Query understanding - extracts structured parameters from natural language queries."""

from langchain.chat_models import init_chat_model

from src.models.schema import VesselType
from src.models.query_models import QueryParameters
from src.prompts.query_prompts import QUERY_UNDERSTANDING_PROMPT
from src.config.settings import get_settings
from src.config.env_loader import load_environment_variables

# Load environment variables
load_environment_variables()


class QueryUnderstanding:
    """Extract structured parameters from natural language queries.
    
    Uses an LLM to parse natural language queries and extract structured
    parameters (vessel type, GT, arrival region, etc.) into a QueryParameters
    object. This is the first node in the LangGraph workflow.
    """
    
    def __init__(self, llm_model: str = None, llm_provider: str = None):
        """Initialize query understanding component.
        
        Args:
            llm_model: LLM model to use for query understanding (defaults to config)
            llm_provider: LLM provider name (defaults to config)
        """
        settings = get_settings()
        llm_model = llm_model or settings.llm_model_query_understanding
        llm_provider = llm_provider or settings.llm_provider
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


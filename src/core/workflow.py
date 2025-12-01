"""Main workflow orchestrator - LangGraph-based workflow."""

from typing import TypedDict, Optional, Dict, Any
from pathlib import Path

from langgraph.graph import StateGraph, START, END

from src.core.query_understanding import QueryUnderstanding
from src.models.query_models import QueryParameters
from src.core.retriever import RAGRetriever
from src.core.calculator import TariffCalculator
from src.core.response_generator import ResponseGenerator
from src.config.settings import get_settings
from src.config.logging_config import get_logger
from src.config.messages import (
    ERROR_NO_PARAMETERS,
    ERROR_VESSEL_TYPE_NOT_IDENTIFIED,
    ERROR_CALCULATION_FAILED,
)

logger = get_logger(__name__)


class TariffWorkflowState(TypedDict):
    """State shared between LangGraph nodes.
    
    This TypedDict defines the state structure that flows through the
    LangGraph workflow. Each node can read from and write to this state.
    
    Attributes:
        query: Original user query string
        parameters: Structured parameters extracted by query understanding (Node 1)
        rag_context: Context retrieved from vector database (Node 2)
        compiled_information: Enriched parameter information (Node 3)
        calculation_result: Tariff calculation results (Node 4)
        answer: Final natural language response (Node 5)
    """
    # Input
    query: str
    
    # Node 1: Query Understanding
    parameters: Optional[QueryParameters]
    
    # Node 2: Retriever (RAG)
    rag_context: str
    
    # Node 3: Compile Information
    compiled_information: str
    
    # Node 4: Tariff Computation (deterministic)
    calculation_result: Optional[Dict[str, Any]]
    
    # Node 5: Response Generator
    answer: str


class TariffWorkflow:
    """Main workflow orchestrator using LangGraph.
    
    Orchestrates the complete tariff calculation workflow using LangGraph.
    The workflow consists of 5 nodes:
    1. Query Understanding: Extract structured parameters from natural language
    2. Retriever: Retrieve relevant context from vector database (runs in parallel with Node 3)
    3. Compile Information: Enrich and validate parameters using JSON dataset (runs in parallel with Node 2)
    4. Tariff Computation: Calculate tariff deterministically using rules
    5. Response Generator: Generate natural language response
    
    Workflow structure:
    - Node 1 → Node 2 and Node 3 (parallel execution)
    - Node 2 → Node 5 (Response Generator) directly
    - Node 3 → Node 4 (Tariff Computation)
    - Node 4 → Node 5 (Response Generator)
    - Node 5 waits for both Node 2 and Node 4 to complete before generating response
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        chroma_db_dir: Optional[Path] = None
    ):
        """
        Initialize workflow.
        
        Args:
            data_dir: Directory containing PDF documents
            chroma_db_dir: Directory for ChromaDB
        """
        self.query_understanding = QueryUnderstanding()
        self.rag_retriever = RAGRetriever(data_dir, chroma_db_dir)
        self.calculator = TariffCalculator()
        self.response_generator = ResponseGenerator()
        
        self.graph = None
        self._initialized = False
    
    def initialize(self):
        """Initialize all components and build LangGraph workflow.
        
        Initializes the RAG retriever, loads the tariff database,
        and builds the LangGraph workflow with all nodes and edges.
        This method is idempotent - calling it multiple times has no effect.
        """
        if self._initialized:
            return
        
        logger.info("Initializing Tariff Workflow (LangGraph)...")
        logger.info("1. Initializing RAG retriever...")
        self.rag_retriever.initialize()
        logger.info("2. Loading tariff database...")
        # Calculator already loads database in __init__
        logger.info("3. Building LangGraph workflow...")
        
        # Build LangGraph
        graph = StateGraph(TariffWorkflowState)
        
        # Add nodes
        graph.add_node("query_understanding", self._query_understanding_node)
        graph.add_node("retriever", self._retriever_node)
        graph.add_node("compile_information", self._compile_information_node)
        graph.add_node("tariff_computation", self._tariff_computation_node)
        graph.add_node("response_generator", self._response_generator_node)
        
        # Define edges
        # START → Node 1
        graph.add_edge(START, "query_understanding")
        
        # Node 1 → Node 2 (RAG) and Node 3 (Compile) in PARALLEL
        graph.add_edge("query_understanding", "retriever")
        graph.add_edge("query_understanding", "compile_information")
        graph.add_edge("compile_information", "tariff_computation")

        # Node 2 (Retriever) → Node 5 (Response Generator) directly
        graph.add_edge("retriever", "response_generator")
        graph.add_edge("tariff_computation", "response_generator")
        
                
        # Node 5 → END
        graph.add_edge("response_generator", END)
        
        # Compile graph
        self.graph = graph.compile()
        
        logger.info("4. LangGraph workflow ready!")
        
        self._initialized = True
    
    # Node 1: Query Understanding
    def _query_understanding_node(self, state: TariffWorkflowState) -> TariffWorkflowState:
        """Extract structured parameters from user query (Node 1).
        
        Uses LLM to parse natural language query and extract structured
        parameters (vessel type, GT, arrival region, etc.).
        
        Args:
            state: Current workflow state containing the user query
        
        Returns:
            Updated state with 'parameters' field populated
        """
        logger.info("Node 1: Query Understanding")
        query = state["query"]
        
        parameters = self.query_understanding.understand(query)
        logger.debug(f"Extracted: vessel_type={parameters.vessel_type}, GT={parameters.vessel_details.gross_tonnage_gt}, region={parameters.call_context.arrival_region}")
        
        return {"parameters": parameters}
    
    def _retriever_node(self, state: TariffWorkflowState) -> TariffWorkflowState:
        """Retrieve relevant context from vector database (Node 2).
        
        Retrieves relevant document chunks from ChromaDB based on the query.
        Runs in parallel with Node 3 (Compile Information).
        
        
        Args:
            state: Current workflow state containing the user query
        
        Returns:
            Updated state with 'rag_context' field populated (formatted JSON string)
        """
        logger.info("Node 2: Retriever (RAG)")
        query = state["query"]
        
        settings = get_settings()
        rag_context = self.rag_retriever.retrieve_context(query, k=settings.rag_retrieval_count)
        doc_count = rag_context.count('"id"') if rag_context else 0
        logger.debug(f"Retrieved {doc_count} relevant documents")
        
        return {"rag_context": rag_context}
    
    def _compile_information_node(self, state: TariffWorkflowState) -> TariffWorkflowState:
        """Enrich and prepare parameters for calculation (Node 3).
        
        Uses the pre-computed JSON dataset to validate and enrich parameters
        extracted by Node 1. This node does NOT use LLM - it's purely deterministic.
        Runs in parallel with Node 2 (Retriever).
        
        This node:
        1. Takes extracted parameters from Node 1 (LLM)
        2. Validates vessel type and maps to enum
        3. Checks available rules and components for the vessel type
        4. Validates that required parameters (e.g., GT) are present
        5. Prepares enriched parameter information
        
        Args:
            state: Current workflow state containing extracted parameters
        
        Returns:
            Updated state with 'compiled_information' field populated
        """
        logger.info("Node 3: Compile Information")
        
        parameters = state.get("parameters")
        
        if not parameters:
            logger.warning("No parameters to enrich")
            return {"compiled_information": ERROR_NO_PARAMETERS}
        
        # Get available rules for this vessel type
        # Use the existing conversion method from QueryParameters to avoid duplication
        calc_params = parameters.to_calculator_params()
        vessel_type_enum = calc_params.get("vessel_type")
        
        if vessel_type_enum:
            available_rules = self.calculator.database.get_rules(
                vessel_type=vessel_type_enum
            )
            components = set(rule.component for rule in available_rules)
            logger.debug(f"Found {len(available_rules)} rules, {len(components)} components for {parameters.vessel_type}")
            
            # Validate that we have minimum required parameters
            validation_notes = []
            if (not parameters.vessel_details.gross_tonnage_gt and 
                not parameters.vessel_details.deadweight_tonnage_dwt and
                not parameters.vessel_details.length_overall_m):
                validation_notes.append("Warning: No size parameter (GT/DWT/LOA) provided")
            
            # Prepare enriched parameters info
            compiled_info = {
                "vessel_type": parameters.vessel_type,
                "extracted_parameters": {
                    "gt": parameters.vessel_details.gross_tonnage_gt,
                    "dwt": parameters.vessel_details.deadweight_tonnage_dwt,
                    "loa": parameters.vessel_details.length_overall_m,
                    "arrival_region": parameters.call_context.arrival_region,
                    "sludge_volume": parameters.quantities.sludge_volume_m3,
                    "calls_per_week": parameters.call_context.calls_per_week_on_service,
                },
                "available_components": [c.value for c in components],
                "available_rules_count": len(available_rules),
                "validation_notes": validation_notes,
                "ready_for_calculation": vessel_type_enum is not None
            }
            
            logger.debug(f"Parameters enriched, ready_for_calculation={compiled_info['ready_for_calculation']}")
            
            return {"compiled_information": str(compiled_info)}
        else:
            logger.warning("Vessel type not identified, cannot enrich parameters")
            return {"compiled_information": ERROR_VESSEL_TYPE_NOT_IDENTIFIED}
    
    def _tariff_computation_node(self, state: TariffWorkflowState) -> TariffWorkflowState:
        """Calculate tariff deterministically using JSON rules (Node 4).
        
        Performs the actual tariff calculation using the TariffCalculator.
        This is a purely deterministic operation - no LLM calls.
        Receives input from Node 3 (Compile Information) only.
        Output goes to Node 5 (Response Generator).
        
        Args:
            state: Current workflow state containing parameters from Node 3
        
        Returns:
            Updated state with 'calculation_result' field populated (dictionary format)
        """
        logger.info("Node 4: Tariff Computation")
        
        parameters = state.get("parameters")
        
        if not parameters or not parameters.vessel_type:
            logger.warning("Vessel type not identified for calculation")
            return {
                "calculation_result": {
                    "total": 0.0,
                    "components": {},
                    "breakdown": [],
                    "error": ERROR_VESSEL_TYPE_NOT_IDENTIFIED
                }
            }
        
        # Convert new structure to calculator parameters
        calc_params = parameters.to_calculator_params()
        
        # Remove None values
        calc_params = {k: v for k, v in calc_params.items() if v is not None}
        
        # Calculate
        calculation_result = self.calculator.calculate(calc_params)
        logger.info(f"Calculation complete: {calculation_result.total:.2f} SEK ({len(calculation_result.components)} components)")
        
        return {"calculation_result": calculation_result.to_dict()}
    
    def _response_generator_node(self, state: TariffWorkflowState) -> TariffWorkflowState:
        """Generate natural language response (Node 5).
        
        Uses an LLM to combine calculation results and RAG context into
        a natural, informative response. This is the final node in the workflow.
        
        Receives input from:
        - Node 2 (Retriever): RAG context for explanations and additional information
        - Node 4 (Tariff Computation): Deterministic calculation results
        
        Waits for both Node 2 and Node 4 to complete before generating response.
        
        Uses:
        - Calculation result from Node 4 (deterministic tariff calculation)
        - RAG context from Node 2 (for explanations and additional context)
        - Original query (for context and personalization)
        
        Args:
            state: Current workflow state containing calculation result and RAG context
        
        Returns:
            Updated state with 'answer' field populated (natural language response)
        """
        logger.info("Node 5: Response Generator")
        
        query = state["query"]
        calculation_result = state.get("calculation_result")
        rag_context = state.get("rag_context", "")
        
        if not calculation_result or calculation_result.get("error"):
            logger.warning("No valid calculation result, returning error message")
            answer = ERROR_CALCULATION_FAILED
        else:
            answer = self.response_generator.generate(
                query=query,
                calculation_result=calculation_result,
                rag_context=rag_context
            )
        
        logger.debug("Response generated")
        
        return {"answer": answer}
    
    def process(self, query: str) -> str:
        """
        Process a user query through the LangGraph workflow.
        
        Args:
            query: User's natural language query
        
        Returns:
            Natural language response
        """
        if not self._initialized:
            self.initialize()
        
        logger.info(f"Processing query: {query}")
        
        # Invoke LangGraph
        initial_state: TariffWorkflowState = {
            "query": query,
            "parameters": None,
            "rag_context": "",
            "compiled_information": "",
            "calculation_result": None,
            "answer": ""
        }
        
        result = self.graph.invoke(initial_state)
        
        logger.info("Workflow complete")
        
        return result["answer"]


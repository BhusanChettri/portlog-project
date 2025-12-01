"""Extract tariff data from PDF using LLM and save to structured format."""

import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from langchain_community.document_loaders import PyPDFLoader
from langchain.chat_models import init_chat_model

from src.models.schema import (
    TariffDatabase,
    TariffRule,
    VesselType,
    TariffComponent,
    ChargingMethod,
)
from src.prompts.extraction_prompts import EXTRACTION_PROMPT
from src.config.settings import get_settings
from src.config.env_loader import load_environment_variables
from src.config.logging_config import get_logger

# Load environment variables
load_environment_variables()

logger = get_logger(__name__)


class ExtractionResponse(BaseModel):
    """Response from LLM extraction containing tariff rules.
    
    This is an internal Pydantic model used to structure the LLM's
    extraction output. The rules field contains a JSON string that
    is parsed separately to handle complex nested structures.
    
    Attributes:
        rules: JSON string containing list of extracted tariff rules
        extraction_notes: Optional notes about the extraction process
    """
    rules: str = Field(description="JSON string containing list of extracted tariff rules")
    extraction_notes: Optional[str] = Field(None, description="Notes about the extraction process")


class TariffExtractor:
    """Extract tariff data from PDF using LLM and save to structured JSON.
    
    This class handles Phase 1 (Extraction) of the two-phase system.
    It uses an LLM to extract structured tariff rules from PDF documents
    and saves them as JSON for fast loading in Phase 2.
    
    The extraction process:
    1. Loads PDF and extracts text
    2. Uses LLM with structured output to extract tariff rules
    3. Normalizes vessel types and component names (fixes common typos)
    4. Validates and converts to TariffRule objects
    5. Saves to JSON file for future use
    """
    
    def __init__(self, llm_model: str = None, llm_provider: str = None):
        """
        Initialize the extractor.
        
        Args:
            llm_model: LLM model to use for extraction (defaults to config)
            llm_provider: LLM provider (defaults to config)
        """
        settings = get_settings()
        llm_model = llm_model or settings.llm_model_extraction
        llm_provider = llm_provider or settings.llm_provider
        self.llm = init_chat_model(llm_model, model_provider=llm_provider)
        self.llm_structured = self.llm.with_structured_output(ExtractionResponse)
    
    def extract_from_pdf(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
        chunk_size: int = None
    ) -> TariffDatabase:
        """
        Extract tariff rules from PDF and save to JSON.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Path to save extracted JSON (defaults to config)
            chunk_size: Maximum characters per chunk for processing large PDFs (defaults to config)
        
        Returns:
            TariffDatabase with extracted rules
        """
        logger.info(f"Loading PDF: {pdf_path}")
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        
        # Combine all pages
        full_text = "\n".join([p.page_content for p in pages])
        logger.info(f"PDF loaded: {len(pages)} pages, {len(full_text)} characters")
        
        # Get settings for defaults
        settings = get_settings()
        if chunk_size is None:
            chunk_size = settings.extraction_chunk_size
        
        # Prepare prompt with vessel types and component names
        vessel_types = [vt.value for vt in VesselType]
        component_names = [tc.value for tc in TariffComponent]
        
        # Process in chunks if PDF is very large
        if len(full_text) > chunk_size:
            logger.info(f"PDF is large ({len(full_text)} chars), processing in chunks...")
            all_rules = []
            chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
                response = self._extract_from_text(chunk, vessel_types, component_names)
                # Parse JSON string to list
                rules_data = json.loads(response.rules)
                all_rules.extend(rules_data)
        else:
            response = self._extract_from_text(full_text, vessel_types, component_names)
            # Parse JSON string to list
            all_rules = json.loads(response.rules)
        
        # Normalize and convert dictionaries to TariffRule objects
        rules = []
        for rule_dict in all_rules:
            try:
                # Normalize vessel_type (fix common typos)
                vessel_type = rule_dict.get("vessel_type", "").lower().strip()
                vessel_type_fixes = {
                    "cruise_vessles": "cruise_vessels",
                    "cruise_vessel": "cruise_vessels",
                    "container_vessel": "container_vessels",
                    "roro_vessel": "roro_vessels",
                    "car_carrier": "car_carriers",
                    "ropax_passenger_vessel": "ropax_passenger_vessels",
                    "break_bulk_lolo_vessel": "break_bulk_lolo_vessels",
                    "inland_waterway": "inland_waterways",
                    "harbour_vessel": "harbour_vessels",
                    "other_vessel": "other_vessels",
                }
                if vessel_type in vessel_type_fixes:
                    rule_dict["vessel_type"] = vessel_type_fixes[vessel_type]
                
                # Normalize component names
                component = rule_dict.get("component", "").lower().strip()
                component_fixes = {
                    "port_infrastructure": "port_infrastructure_dues",
                    "solid_waste": "ship_generated_solid_waste",
                    "sludge": "sludge_oily_bilge_water",
                    "scrubber": "scrubber_waste",
                    "environmental_discount": "environmental_discounts",
                    "freshwater": "fresh_water",
                    "fresh_water_dues": "fresh_water",
                    "ops": "connecting_to_ops",
                    "connecting_to_ops_dues": "connecting_to_ops",
                }
                if component in component_fixes:
                    rule_dict["component"] = component_fixes[component]
                
                rule = TariffRule(**rule_dict)
                rules.append(rule)
            except Exception as e:
                logger.warning(f"Failed to parse rule: {e}")
                logger.debug(f"Rule data: {rule_dict}")
        
        logger.info(f"Extracted {len(rules)} tariff rules")
        
        # Create database
        settings = get_settings()
        database = TariffDatabase(
            rules=rules,
            version=settings.tariff_version,
            port_name=settings.port_name
        )
        
        # Save to disk
        if output_path is None:
            project_dir = Path(__file__).parent.parent.parent
            output_path = settings.get_tariff_rules_path(project_dir)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_to_disk(database, output_path)
        
        return database
    
    def _extract_from_text(
        self,
        text: str,
        vessel_types: List[str],
        component_names: List[str]
    ) -> ExtractionResponse:
        """Extract rules from text using LLM.
        
        Internal method that invokes the LLM with the extraction prompt
        to extract tariff rules from PDF text content.
        
        Args:
            text: PDF text content (truncated to configured limit if longer)
            vessel_types: List of vessel type strings for prompt
            component_names: List of component name strings for prompt
        
        Returns:
            ExtractionResponse containing JSON string of extracted rules
        
        Note:
            Text is truncated to configured limit to fit within LLM context limits.
        """
        # Create chain with prompt template
        settings = get_settings()
        truncate_limit = settings.extraction_text_truncate_limit
        chain = EXTRACTION_PROMPT | self.llm_structured
        response = chain.invoke({
            "pdf_content": text[:truncate_limit],
            "vessel_types": ", ".join(vessel_types),
            "component_names": ", ".join(component_names)
        })
        
        return response
    
    def _save_to_disk(self, database: TariffDatabase, output_path: Path):
        """Save TariffDatabase to JSON file.
        
        Converts the TariffDatabase to a dictionary and saves it as
        a pretty-printed JSON file with UTF-8 encoding.
        
        Args:
            database: TariffDatabase object to save
            output_path: Path where JSON file should be saved
        
        Note:
            Creates parent directories if they don't exist.
        """
        # Convert to dict for JSON serialization
        data = {
            "version": database.version,
            "port_name": database.port_name,
            "rules": [rule.model_dump() for rule in database.rules]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved extracted data to: {output_path}")
        logger.info(f"Total rules saved: {len(database.rules)}")


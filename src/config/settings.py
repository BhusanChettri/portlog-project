"""Centralized configuration management using Pydantic Settings.

This module provides a single source of truth for all configuration values.
All settings can be overridden via environment variables.
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    For example, LLM_MODEL_QUERY_UNDERSTANDING=gpt-4 will override the default.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========== LLM Configuration ==========
    llm_model_query_understanding: str = Field(
        default="gpt-4o-mini",
        description="LLM model for query understanding"
    )
    llm_model_response_generation: str = Field(
        default="gpt-4o-mini",
        description="LLM model for response generation"
    )
    llm_model_extraction: str = Field(
        default="gpt-4o-mini",
        description="LLM model for data extraction"
    )
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, etc.)"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for vector database"
    )
    
    # ========== RAG/Vector Database Configuration ==========
    rag_chunk_size: int = Field(
        default=1000,
        description="Chunk size for text splitting in RAG"
    )
    rag_chunk_overlap: int = Field(
        default=200,
        description="Chunk overlap for text splitting in RAG"
    )
    rag_retrieval_count: int = Field(
        default=5,
        description="Number of documents to retrieve from vector database"
    )
    chroma_collection_name: str = Field(
        default="port_tariff_documents",
        description="ChromaDB collection name"
    )
    
    # ========== File Paths Configuration ==========
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory containing PDF documents"
    )
    chroma_db_dir: Path = Field(
        default=Path("chroma_db"),
        description="Directory for ChromaDB persistence"
    )
    pdf_filename: str = Field(
        default="port-of-gothenburg-port-tariff-2025.pdf",
        description="PDF filename in data directory"
    )
    tariff_rules_json: Path = Field(
        default=Path("extracted_data/tariff_rules.json"),
        description="Path to extracted tariff rules JSON file"
    )
    extraction_chunk_size: int = Field(
        default=50000,
        description="Chunk size for processing large PDFs during extraction"
    )
    
    # ========== Currency Configuration ==========
    default_currency: str = Field(
        default="SEK",
        description="Default currency code"
    )
    
    # ========== Business Logic Constants ==========
    exclusive_components: List[str] = Field(
        default=["port_infrastructure_dues"],
        description="List of tariff components that are mutually exclusive"
    )
    sludge_free_threshold_m3: float = Field(
        default=11.0,
        description="Free sludge volume threshold in cubic meters"
    )
    esi_score_threshold: int = Field(
        default=30,
        description="Minimum ESI score to qualify for environmental discount"
    )
    esi_discount_percentage: float = Field(
        default=0.10,
        description="ESI discount percentage (0.10 = 10%)"
    )
    
    # ========== Server Configuration ==========
    server_host: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    server_port: int = Field(
        default=7860,
        description="Server port number"
    )
    
    # ========== Application Metadata ==========
    port_name: str = Field(
        default="Port of Gothenburg",
        description="Port name for tariff database"
    )
    tariff_version: str = Field(
        default="2025",
        description="Tariff version/year"
    )
    
    # ========== LLM Processing Limits ==========
    extraction_text_truncate_limit: int = Field(
        default=100000,
        description="Maximum characters to process in a single LLM extraction call"
    )
    
    def get_data_dir(self, project_dir: Path) -> Path:
        """Get absolute path to data directory.
        
        Args:
            project_dir: Project root directory
            
        Returns:
            Absolute path to data directory
        """
        if self.data_dir.is_absolute():
            return self.data_dir
        return project_dir / self.data_dir
    
    def get_chroma_db_dir(self, project_dir: Path) -> Path:
        """Get absolute path to ChromaDB directory.
        
        Args:
            project_dir: Project root directory
            
        Returns:
            Absolute path to ChromaDB directory
        """
        if self.chroma_db_dir.is_absolute():
            return self.chroma_db_dir
        return project_dir / self.chroma_db_dir
    
    def get_tariff_rules_path(self, project_dir: Path) -> Path:
        """Get absolute path to tariff rules JSON file.
        
        Args:
            project_dir: Project root directory
            
        Returns:
            Absolute path to tariff rules JSON file
        """
        if self.tariff_rules_json.is_absolute():
            return self.tariff_rules_json
        return project_dir / self.tariff_rules_json


# Global settings instance
# This will be initialized when the module is imported
# Environment variables will be loaded automatically
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Creates and caches a Settings instance on first call.
    Subsequent calls return the cached instance.
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience: Export settings instance directly
settings = get_settings()


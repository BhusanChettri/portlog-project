"""Load tariff data from disk (no LLM calls)."""

import json
from pathlib import Path
from typing import Optional

from src.models.schema import TariffDatabase, TariffRule


class TariffLoader:
    """Load tariff rules from disk (fast, no LLM).
    
    This class provides static methods to load tariff data from JSON files.
    It's used in Phase 2 (Usage) to quickly load pre-extracted tariff rules
    without making LLM calls. All methods are static for convenience.
    """
    
    @staticmethod
    def load_from_json(json_path: Path) -> TariffDatabase:
        """
        Load tariff rules from JSON file.
        
        Args:
            json_path: Path to JSON file containing tariff rules
        
        Returns:
            TariffDatabase with loaded rules
        """
        json_path = Path(json_path) if isinstance(json_path, str) else json_path
        if not json_path.exists():
            raise FileNotFoundError(f"Tariff data file not found: {json_path}")
        
        print(f"Loading tariff data from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert dictionaries to TariffRule objects
        rules = []
        for rule_dict in data.get("rules", []):
            try:
                rule = TariffRule(**rule_dict)
                rules.append(rule)
            except Exception as e:
                print(f"Warning: Failed to load rule: {e}")
                print(f"Rule data: {rule_dict}")
        
        database = TariffDatabase(
            rules=rules,
            version=data.get("version", "2025"),
            port_name=data.get("port_name", "Port of Gothenburg")
        )
        
        print(f"Loaded {len(rules)} tariff rules")
        return database
    
    @staticmethod
    def get_default_path() -> Path:
        """Get default path to extracted tariff data.
        
        Returns:
            Path object pointing to extracted_data/tariff_rules.json
            relative to the project root.
        """
        project_dir = Path(__file__).parent.parent.parent
        return project_dir / "extracted_data" / "tariff_rules.json"
    
    @staticmethod
    def load_default() -> Optional[TariffDatabase]:
        """
        Load tariff data from default location.
        
        Returns:
            TariffDatabase if file exists, None otherwise
        """
        default_path = TariffLoader.get_default_path()
        if default_path.exists():
            return TariffLoader.load_from_json(default_path)
        return None


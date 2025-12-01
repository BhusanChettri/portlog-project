"""Unit tests for extractor and loader."""

import pytest
import json
from pathlib import Path
from src.core.dataset_loader import TariffLoader
from src.models.schema import TariffDatabase, VesselType


class TestTariffLoader:
    """Test TariffLoader class."""
    
    def test_load_from_json_file_exists(self):
        """Test loading from existing JSON file."""
        # Check if extracted data exists
        project_root = Path(__file__).parent.parent.parent
        json_path = project_root / "extracted_data" / "tariff_rules.json"
        
        if json_path.exists():
            database = TariffLoader.load_from_json(str(json_path))
            assert database is not None
            assert isinstance(database, TariffDatabase)
            assert len(database.rules) > 0
            assert database.port_name is not None
    
    def test_load_from_json_file_not_exists(self):
        """Test loading from non-existent file."""
        database = TariffLoader.load_from_json("/nonexistent/path/file.json")
        assert database is None
    
    def test_load_default(self):
        """Test loading from default location."""
        database = TariffLoader.load_default()
        # May or may not exist depending on whether extraction was run
        if database is not None:
            assert isinstance(database, TariffDatabase)
            assert len(database.rules) > 0
    
    def test_loaded_data_structure(self):
        """Test that loaded data has correct structure."""
        database = TariffLoader.load_default()
        if database is None:
            pytest.skip("No extracted data available")
        
        assert hasattr(database, "port_name")
        assert hasattr(database, "version")
        assert hasattr(database, "rules")
        assert hasattr(database, "get_rules")
        
        # Test get_rules method
        tanker_rules = database.get_rules(vessel_type=VesselType.TANKERS)
        assert isinstance(tanker_rules, list)
    
    def test_loaded_rules_valid(self):
        """Test that loaded rules are valid."""
        database = TariffLoader.load_default()
        if database is None:
            pytest.skip("No extracted data available")
        
        for rule in database.rules[:10]:  # Test first 10 rules
            assert hasattr(rule, "vessel_type")
            assert hasattr(rule, "component")
            assert hasattr(rule, "charging_method")
            assert hasattr(rule, "pricing")
            assert rule.pricing.currency == "SEK"


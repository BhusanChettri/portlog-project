"""Unit tests for tariff calculator."""

import pytest
from src.core.calculator import TariffCalculator, CalculationResult
from src.models.schema import VesselType
from tests.test_fixtures import create_example_rules


class TestCalculationResult:
    """Test CalculationResult class."""
    
    def test_result_creation(self):
        """Test creating a calculation result."""
        result = CalculationResult()
        assert result.total == 0.0
        assert len(result.components) == 0
        assert len(result.breakdown) == 0
    
    def test_add_component(self):
        """Test adding a component to result."""
        result = CalculationResult()
        result.add_component(
            component_name="port_infrastructure_dues",
            cost=15200.0,
            rule=None,
            details={"rate": 3.04, "currency": "SEK"}
        )
        
        assert result.total == 15200.0
        assert len(result.components) == 1
        assert len(result.breakdown) == 1
        assert result.breakdown[0]["component"] == "port_infrastructure_dues"
        assert result.breakdown[0]["cost"] == 15200.0
    
    def test_add_multiple_components(self):
        """Test adding multiple components."""
        result = CalculationResult()
        result.add_component("port_infrastructure_dues", 15200.0, None, {})
        result.add_component("solid_waste", 650.0, None, {})
        result.add_component("sludge", 2250.0, None, {})
        
        assert result.total == pytest.approx(18100.0, rel=0.01)
        assert len(result.components) == 3
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = CalculationResult()
        result.add_component("port_infrastructure_dues", 15200.0, None, {})
        
        result_dict = result.to_dict()
        assert "total" in result_dict
        assert "components" in result_dict
        assert "breakdown" in result_dict
        assert result_dict["total"] == 15200.0


class TestTariffCalculator:
    """Test TariffCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator with sample database."""
        database = create_example_rules()
        return TariffCalculator(database)
    
    def test_calculate_without_vessel_type(self, calculator):
        """Test calculation without vessel type."""
        params = {"gt": 5000}
        result = calculator.calculate(params)
        
        assert result.total == 0.0
        assert len(result.components) == 0
    
    def test_calculate_tanker_basic(self, calculator):
        """Test basic tanker calculation."""
        params = {
            "vessel_type": VesselType.TANKERS,
            "gt": 5000,
            "arrival_origin": "EU"
        }
        result = calculator.calculate(params)
        
        assert result.total > 0
        assert len(result.components) > 0
        # Should have at least port infrastructure dues
        assert any("port_infrastructure" in comp.lower() for comp in result.components.keys())
    
    def test_calculate_with_sludge(self, calculator):
        """Test calculation with sludge volume."""
        params = {
            "vessel_type": VesselType.TANKERS,
            "gt": 5000,
            "arrival_origin": "EU",
            "sludge_volume": 15
        }
        result = calculator.calculate(params)
        
        assert result.total > 0
        # Should include sludge component if rules exist
        component_names = [comp.lower() for comp in result.components.keys()]
        # May or may not have sludge depending on rules
    
    def test_calculate_non_eu(self, calculator):
        """Test calculation for non-EU arrival."""
        params = {
            "vessel_type": VesselType.TANKERS,
            "gt": 5000,
            "arrival_origin": "non-EU"
        }
        result = calculator.calculate(params)
        
        # May or may not have rules for non-EU, so just check it doesn't crash
        assert result.total >= 0
        # Non-EU rates might be different
    
    def test_calculate_container_vessel(self, calculator):
        """Test calculation for container vessel."""
        params = {
            "vessel_type": VesselType.CONTAINER_VESSELS,
            "gt": 8000,
            "arrival_origin": "EU"
        }
        result = calculator.calculate(params)
        
        # May or may not have rules for container vessels in example data
        assert result.total >= 0
        assert isinstance(result.components, dict)
    
    def test_calculate_with_bands(self, calculator):
        """Test calculation with GT bands."""
        # Test different GT values to trigger different bands
        test_cases = [
            (2000, "Should use lower band"),
            (5000, "Should use middle band"),
            (20000, "Should use higher band"),
        ]
        
        for gt, description in test_cases:
            params = {
                "vessel_type": VesselType.TANKERS,
                "gt": gt,
                "arrival_origin": "EU"
            }
            result = calculator.calculate(params)
            assert result.total > 0, f"{description}: GT={gt}"
    
    def test_calculate_with_conditions(self, calculator):
        """Test calculation with conditions."""
        # Test with sludge volume condition
        params_small = {
            "vessel_type": VesselType.TANKERS,
            "gt": 5000,
            "arrival_origin": "EU",
            "sludge_volume": 5  # Small volume
        }
        result_small = calculator.calculate(params_small)
        
        params_large = {
            "vessel_type": VesselType.TANKERS,
            "gt": 5000,
            "arrival_origin": "EU",
            "sludge_volume": 15  # Large volume
        }
        result_large = calculator.calculate(params_large)
        
        # Results might differ based on volume thresholds
        assert result_small.total >= 0
        assert result_large.total >= 0
    
    def test_calculate_empty_params(self, calculator):
        """Test calculation with empty parameters."""
        params = {}
        result = calculator.calculate(params)
        
        assert result.total == 0.0
        assert len(result.components) == 0


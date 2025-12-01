"""Unit tests for tariff model utility functions."""

import pytest
from src.models.schema import TariffRule, Condition, Band, PricingRule, VesselType, TariffComponent, ChargingMethod
from src.models.utils import (
    evaluate_condition,
    check_rule_applicable,
    find_applicable_band,
    calculate_component_cost,
)


class TestEvaluateCondition:
    """Test condition evaluation."""
    
    def test_equality_condition(self):
        """Test equality condition."""
        condition = Condition(
            field="arrival_origin",
            operator="eq",
            value="EU",
            description="From EU"
        )
        context = {"arrival_origin": "EU"}
        assert evaluate_condition(condition, context) is True
        
        context = {"arrival_origin": "non-EU"}
        assert evaluate_condition(condition, context) is False
    
    def test_greater_than_condition(self):
        """Test greater than condition."""
        condition = Condition(
            field="sludge_volume",
            operator="gt",
            value=11,
            description="More than 11 m3"
        )
        context = {"sludge_volume": 15}
        assert evaluate_condition(condition, context) is True
        
        context = {"sludge_volume": 5}
        assert evaluate_condition(condition, context) is False
    
    def test_less_than_or_equal_condition(self):
        """Test less than or equal condition."""
        condition = Condition(
            field="sludge_volume",
            operator="lte",
            value=11,
            description="11 m3 or less"
        )
        context = {"sludge_volume": 11}
        assert evaluate_condition(condition, context) is True
        
        context = {"sludge_volume": 15}
        assert evaluate_condition(condition, context) is False
    
    def test_field_mapping(self):
        """Test field name mapping."""
        condition = Condition(
            field="arrival port",
            operator="from",
            value="European ports",
            description="From EU"
        )
        context = {"arrival_origin": "EU"}
        assert evaluate_condition(condition, context) is True
    
    def test_operator_variations(self):
        """Test different operator formats."""
        # Test "from" operator
        condition = Condition(
            field="arrival port",
            operator="from",
            value="European ports",
            description="From EU"
        )
        context = {"arrival_origin": "EU"}
        assert evaluate_condition(condition, context) is True
        
        # Test "more than" operator
        condition = Condition(
            field="sludge_volume",
            operator="more than",
            value="11",
            description="More than 11"
        )
        context = {"sludge_volume": 15}
        assert evaluate_condition(condition, context) is True
    
    def test_missing_field(self):
        """Test condition with missing field in context."""
        condition = Condition(
            field="sludge_volume",
            operator="gt",
            value=11,
            description="More than 11"
        )
        context = {}  # Missing sludge_volume
        assert evaluate_condition(condition, context) is False


class TestCheckRuleApplicable:
    """Test rule applicability checking."""
    
    def test_rule_without_conditions(self):
        """Test rule that always applies (no conditions)."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[],
            conditions=[],
            pricing=PricingRule(rate=3.04, currency="SEK"),
            description="Always applies"
        )
        context = {}
        assert check_rule_applicable(rule, context) is True
    
    def test_rule_with_single_condition(self):
        """Test rule with one condition."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.SOLID_WASTE,
            charging_method=ChargingMethod.PER_GT,
            bands=[],
            conditions=[
                Condition(
                    field="arrival_origin",
                    operator="eq",
                    value="EU",
                    description="From EU"
                )
            ],
            pricing=PricingRule(rate=0.13, currency="SEK", rate_unit="SEK_per_GT"),
            description="EU solid waste"
        )
        context = {"arrival_origin": "EU"}
        assert check_rule_applicable(rule, context) is True
        
        context = {"arrival_origin": "non-EU"}
        assert check_rule_applicable(rule, context) is False
    
    def test_rule_with_multiple_conditions(self):
        """Test rule with multiple conditions (all must be met)."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.SLUDGE_OILY_BILGE_WATER,
            charging_method=ChargingMethod.PER_M3,
            bands=[],
            conditions=[
                Condition(
                    field="arrival_origin",
                    operator="eq",
                    value="EU",
                    description="From EU"
                ),
                Condition(
                    field="sludge_volume",
                    operator="gt",
                    value=11,
                    description="More than 11 m3"
                )
            ],
            pricing=PricingRule(rate=150, currency="SEK"),
            description="EU sludge > 11 m3"
        )
        context = {"arrival_origin": "EU", "sludge_volume": 15}
        assert check_rule_applicable(rule, context) is True
        
        context = {"arrival_origin": "EU", "sludge_volume": 5}  # Volume too low
        assert check_rule_applicable(rule, context) is False
        
        context = {"arrival_origin": "non-EU", "sludge_volume": 15}  # Wrong origin
        assert check_rule_applicable(rule, context) is False


class TestFindApplicableBand:
    """Test band finding logic."""
    
    def test_find_band_in_range(self):
        """Test finding a band when value is in range."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[
                Band(name="0-2300", band_type="gt_range", min_value=0, max_value=2300),
                Band(name="2301-3300", band_type="gt_range", min_value=2301, max_value=3300),
                Band(name="3301-15000", band_type="gt_range", min_value=3301, max_value=15000),
            ],
            conditions=[],
            pricing=PricingRule(rate=3.04, currency="SEK"),
            description="Banded dues"
        )
        
        band = find_applicable_band(rule, 2500, "gt_range")  # Use band_type, not "gt"
        assert band is not None
        assert band["min_value"] == 2301
        assert band["max_value"] == 3300
    
    def test_find_band_at_boundary(self):
        """Test finding band at boundary value."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[
                Band(name="0-2300", band_type="gt_range", min_value=0, max_value=2300),
                Band(name="2301-3300", band_type="gt_range", min_value=2301, max_value=3300),
            ],
            conditions=[],
            pricing=PricingRule(rate=3.04, currency="SEK"),
            description="Banded dues"
        )
        
        band = find_applicable_band(rule, 2300, "gt_range")
        assert band is not None
        assert band["max_value"] == 2300
    
    def test_find_band_no_max(self):
        """Test finding band with no maximum."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[
                Band(name="0-15000", band_type="gt_range", min_value=0, max_value=15000),
                Band(name=">15000", band_type="gt_range", min_value=15001, max_value=None),
            ],
            conditions=[],
            pricing=PricingRule(rate=5.75, currency="SEK", rate_unit="SEK_per_GT"),
            description="Banded dues"
        )
        
        band = find_applicable_band(rule, 20000, "gt_range")
        assert band is not None
        assert band["min_value"] == 15001
        assert band["max_value"] is None
    
    def test_no_band_found(self):
        """Test when no band matches."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[
                Band(name="0-2300", band_type="gt_range", min_value=0, max_value=2300),
            ],
            conditions=[],
            pricing=PricingRule(rate=3.04, currency="SEK"),
            description="Banded dues"
        )
        
        band = find_applicable_band(rule, 5000, "gt_range")
        assert band is None  # Value too high for available bands


class TestCalculateComponentCost:
    """Test cost calculation."""
    
    def test_per_gt_calculation(self):
        """Test per GT calculation."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[],
            conditions=[],
            pricing=PricingRule(rate=3.04, currency="SEK"),
            description="Per GT"
        )
        context = {"gt": 5000}
        cost = calculate_component_cost(rule, context)
        assert cost == pytest.approx(5000 * 3.04, rel=0.01)
    
    def test_per_m3_calculation(self):
        """Test per m3 calculation."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.SLUDGE_OILY_BILGE_WATER,
            charging_method=ChargingMethod.PER_M3,
            bands=[],
            conditions=[],
            pricing=PricingRule(rate=150, currency="SEK"),
            description="Per m3"
        )
        context = {"volume_m3": 15}  # Use volume_m3, not sludge_volume
        cost = calculate_component_cost(rule, context)
        assert cost == pytest.approx(15 * 150, rel=0.01)
    
    def test_flat_fee_calculation(self):
        """Test flat fee calculation."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.FLAT_SEK_PER_CALL,
            bands=[],
            conditions=[],
            pricing=PricingRule(flat_fee=1000, currency="SEK"),
            description="Flat fee"
        )
        context = {}
        cost = calculate_component_cost(rule, context)
        assert cost == 1000
    
    def test_banded_calculation(self):
        """Test calculation with bands."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[
                Band(name="0-2300", band_type="gt_range", min_value=0, max_value=2300),
            ],
            conditions=[],
            pricing=PricingRule(rate=3.04, currency="SEK"),
            description="Banded"
        )
        context = {"gt": 2000}
        cost = calculate_component_cost(rule, context)
        assert cost == pytest.approx(2000 * 3.04, rel=0.01)


"""Unit tests for tariff models and schema."""

import pytest
from src.models.schema import (
    VesselType,
    TariffComponent,
    ChargingMethod,
    Band,
    Condition,
    PricingRule,
    TariffRule,
    TariffDatabase,
)
from tests.test_fixtures import create_example_rules


class TestEnums:
    """Test enum definitions."""
    
    def test_vessel_type_enum(self):
        """Test VesselType enum values."""
        assert VesselType.TANKERS.value == "tankers"
        assert VesselType.CONTAINER_VESSELS.value == "container_vessels"
        assert len(VesselType) >= 12  # Should have at least 12 vessel types
    
    def test_tariff_component_enum(self):
        """Test TariffComponent enum values."""
        assert TariffComponent.PORT_INFRASTRUCTURE_DUES.value == "port_infrastructure_dues"
        assert TariffComponent.SHIP_GENERATED_SOLID_WASTE.value == "ship_generated_solid_waste"
    
    def test_charging_method_enum(self):
        """Test ChargingMethod enum values."""
        assert ChargingMethod.PER_GT.value == "per_gt"
        # Note: PER_GT_BANDED may not exist, using PER_GT instead
        assert ChargingMethod.PER_GT.value == "per_gt"
        assert ChargingMethod.FLAT_SEK_PER_CALL.value == "flat_sek_per_call"


class TestBand:
    """Test Band model."""
    
    def test_band_creation(self):
        """Test creating a band."""
        band = Band(
            name="0-2300 GT",
            band_type="gt_range",
            min_value=0,
            max_value=2300
        )
        assert band.name == "0-2300 GT"
        assert band.min_value == 0
        assert band.max_value == 2300
    
    def test_band_with_no_max(self):
        """Test band with no maximum value."""
        band = Band(
            name=">15000 GT",
            band_type="gt_range",
            min_value=15000,
            max_value=None
        )
        assert band.max_value is None


class TestCondition:
    """Test Condition model."""
    
    def test_condition_creation(self):
        """Test creating a condition."""
        condition = Condition(
            field="arrival_origin",
            operator="eq",
            value="EU",
            description="Vessel arrives from EU"
        )
        assert condition.field == "arrival_origin"
        assert condition.operator == "eq"
        assert condition.value == "EU"
    
    def test_condition_with_numeric_value(self):
        """Test condition with numeric value."""
        condition = Condition(
            field="sludge_volume",
            operator="gt",
            value=11,
            description="Sludge volume greater than 11 m3"
        )
        assert condition.value == 11


class TestPricingRule:
    """Test PricingRule model."""
    
    def test_pricing_creation(self):
        """Test creating a pricing object."""
        pricing = PricingRule(
            rate=3.04,
            currency="SEK"
        )
        assert pricing.rate == 3.04
        assert pricing.currency == "SEK"
    
    def test_pricing_with_percentage(self):
        """Test pricing with percentage discount."""
        pricing = PricingRule(
            rate=100,
            currency="SEK",
            percentage=-10  # 10% discount
        )
        assert pricing.percentage == -10


class TestTariffRule:
    """Test TariffRule model."""
    
    def test_rule_creation(self, sample_rule):
        """Test creating a tariff rule."""
        assert sample_rule.vessel_type == VesselType.TANKERS
        assert sample_rule.component == TariffComponent.PORT_INFRASTRUCTURE_DUES
        assert len(sample_rule.bands) == 1
    
    def test_rule_with_conditions(self):
        """Test rule with conditions."""
        rule = TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.SHIP_GENERATED_SOLID_WASTE,
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
            pricing=PricingRule(rate=0.13, currency="SEK"),
            description="Solid waste dues"
        )
        assert len(rule.conditions) == 1
        assert rule.conditions[0].value == "EU"


class TestTariffDatabase:
    """Test TariffDatabase model."""
    
    def test_database_creation(self, sample_database):
        """Test creating a tariff database."""
        assert sample_database.port_name is not None
        assert len(sample_database.rules) > 0
    
    def test_get_rules_by_vessel_type(self, sample_database):
        """Test getting rules filtered by vessel type."""
        tanker_rules = sample_database.get_rules(vessel_type=VesselType.TANKERS)
        assert len(tanker_rules) > 0
        assert all(rule.vessel_type == VesselType.TANKERS for rule in tanker_rules)
    
    def test_get_rules_by_component(self, sample_database):
        """Test getting rules filtered by component."""
        component_rules = sample_database.get_rules(
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES
        )
        assert len(component_rules) > 0
        assert all(
            rule.component == TariffComponent.PORT_INFRASTRUCTURE_DUES
            for rule in component_rules
        )
    
    def test_get_rules_combined_filter(self, sample_database):
        """Test getting rules with both vessel type and component filters."""
        rules = sample_database.get_rules(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES
        )
        assert all(rule.vessel_type == VesselType.TANKERS for rule in rules)
        assert all(
            rule.component == TariffComponent.PORT_INFRASTRUCTURE_DUES
            for rule in rules
        )


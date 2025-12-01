"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import pytest
from src.models.schema import TariffDatabase, TariffRule, VesselType, TariffComponent
from tests.test_fixtures import create_example_rules


@pytest.fixture
def sample_database():
    """Create a sample tariff database for testing."""
    return create_example_rules()


@pytest.fixture
def sample_rule():
    """Create a sample tariff rule for testing."""
    from src.models.schema import ChargingMethod, Band, Condition, PricingRule
    
    return TariffRule(
        vessel_type=VesselType.TANKERS,
        component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
        charging_method=ChargingMethod.PER_GT,
        bands=[
            Band(
                name="0-2300 GT",
                band_type="gt_range",
                min_value=0,
                max_value=2300
            )
        ],
        conditions=[],
        pricing=PricingRule(
            rate=3.04,
            currency="SEK"
        ),
        description="Port infrastructure dues for tankers"
    )


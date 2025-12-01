"""Test fixtures and sample data for tariff system tests."""

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


def create_example_rules() -> TariffDatabase:
    """Create example tariff rules for testing.
    
    This function creates a sample TariffDatabase with example rules
    that demonstrate various schema features (bands, conditions, pricing).
    Used exclusively for unit testing.
    
    Returns:
        TariffDatabase with sample tariff rules
    """
    
    rules = [
        # Example 1: Tanker - Port Infrastructure Dues (with GT bands and EU condition)
        TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.PORT_INFRASTRUCTURE_DUES,
            charging_method=ChargingMethod.PER_GT,
            bands=[
                Band(
                    name="GT_0_500",
                    min_value=0,
                    max_value=500,
                    band_type="gt"
                ),
                Band(
                    name="GT_500_1000",
                    min_value=500,
                    max_value=1000,
                    band_type="gt"
                ),
                Band(
                    name="GT_1000_plus",
                    min_value=1000,
                    max_value=None,
                    band_type="gt"
                ),
            ],
            conditions=[
                Condition(
                    field="arrival_origin",
                    operator="eq",
                    value="EU",
                    description="Arrival from EU"
                )
            ],
            pricing=PricingRule(
                rate=12.5,
                currency="SEK",
                description="12.5 SEK per GT for EU arrivals"
            ),
            description="Port infrastructure dues for tankers arriving from EU"
        ),
        
        # Example 2: Tanker - Sludge (with volume condition)
        TariffRule(
            vessel_type=VesselType.TANKERS,
            component=TariffComponent.SLUDGE_OILY_BILGE_WATER,
            charging_method=ChargingMethod.PER_M3,
            conditions=[
                Condition(
                    field="sludge_volume",
                    operator="lte",
                    value=11,
                    description="Sludge volume ≤ 11 m³"
                )
            ],
            pricing=PricingRule(
                rate=150.0,
                currency="SEK",
                description="150 SEK per m³ for volumes ≤ 11 m³"
            ),
            description="Sludge and oily bilge water dues for tankers (low volume)"
        ),
        
        # Example 3: Container Vessel - Frequency Discount (with calls-per-week band)
        TariffRule(
            vessel_type=VesselType.CONTAINER_VESSELS,
            component=TariffComponent.FREQUENCY_DISCOUNT,
            charging_method=ChargingMethod.PERCENTAGE,
            bands=[
                Band(
                    name="calls_1_2",
                    min_value=1,
                    max_value=3,
                    band_type="calls_per_week"
                ),
                Band(
                    name="calls_3_plus",
                    min_value=3,
                    max_value=None,
                    band_type="calls_per_week"
                ),
            ],
            conditions=[
                Condition(
                    field="calls_per_week",
                    operator="gte",
                    value=1,
                    description="At least 1 call per week"
                )
            ],
            pricing=PricingRule(
                percentage=-5.0,  # 5% discount
                currency="SEK",
                description="5% discount for 1-2 calls per week"
            ),
            description="Frequency discount for container vessels"
        ),
        
        # Example 4: Flat fee example
        TariffRule(
            vessel_type=VesselType.YACHTS,
            component=TariffComponent.CONNECTING_TO_OPS,
            charging_method=ChargingMethod.FLAT_SEK_PER_CALL,
            pricing=PricingRule(
                flat_fee=5000.0,
                currency="SEK",
                description="Flat 5000 SEK per call"
            ),
            description="OPS connection fee for yachts"
        ),
    ]
    
    return TariffDatabase(
        rules=rules,
        version="2025",
        port_name="Port of Gothenburg"
    )


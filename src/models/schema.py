"""Port Tariff Data Schema - Comprehensive models for deterministic tariff calculation."""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class VesselType(str, Enum):
    """Enumeration of all vessel types in the port tariff system.
    
    This enum defines all supported vessel types for tariff calculations.
    Each vessel type may have different tariff components and rates.
    
    Attributes:
        TANKERS: Tanker vessels
        CONTAINER_VESSELS: Container shipping vessels
        RORO_VESSELS: Roll-on/roll-off vessels
        CAR_CARRIERS: Car carrier vessels
        ROPAX_PASSENGER_VESSELS: RoPax passenger vessels
        CRUISE_VESSELS: Cruise ships
        BREAK_BULK_LOLO_VESSELS: Break bulk and LoLo vessels
        INLAND_WATERWAYS: Inland waterway vessels
        YACHTS: Yacht vessels
        ARCHIPELAGO_TRAFFIC: Archipelago traffic vessels
        HARBOUR_VESSELS: Harbour service vessels
        OTHER_VESSELS: Other vessel types not specifically categorized
    """
    TANKERS = "tankers"
    CONTAINER_VESSELS = "container_vessels"
    RORO_VESSELS = "roro_vessels"
    CAR_CARRIERS = "car_carriers"
    ROPAX_PASSENGER_VESSELS = "ropax_passenger_vessels"
    CRUISE_VESSELS = "cruise_vessels"
    BREAK_BULK_LOLO_VESSELS = "break_bulk_lolo_vessels"
    INLAND_WATERWAYS = "inland_waterways"
    YACHTS = "yachts"
    ARCHIPELAGO_TRAFFIC = "archipelago_traffic"
    HARBOUR_VESSELS = "harbour_vessels"
    OTHER_VESSELS = "other_vessels"


class TariffComponent(str, Enum):
    """Enumeration of all tariff component names (dues).
    
    This enum defines all possible tariff components that can be charged
    for port services. Components are categorized by:
    - Common components (applied to most vessel types)
    - Container-specific components
    - Cruise/Passenger-specific components
    - Yacht-specific components
    - Other vessel-specific components
    """
    # Common components
    PORT_INFRASTRUCTURE_DUES = "port_infrastructure_dues"
    SHIP_GENERATED_SOLID_WASTE = "ship_generated_solid_waste"
    SLUDGE_OILY_BILGE_WATER = "sludge_oily_bilge_water"
    SCRUBBER_WASTE = "scrubber_waste"
    ENVIRONMENTAL_DISCOUNTS = "environmental_discounts"
    FRESH_WATER = "fresh_water"
    RINSING_WATER = "rinsing_water"
    LAY_UP_DUES = "lay_up_dues"
    CONNECTING_TO_OPS = "connecting_to_ops"
    
    # Container-specific
    INTRODUCTORY_DISCOUNT = "introductory_discount"
    FREQUENCY_DISCOUNT = "frequency_discount"
    
    # Cruise/Passenger-specific
    ISPS_FEES = "isps_fees"
    PASSENGER_DUES = "passenger_dues"
    
    # Yacht-specific
    BLACK_GREY_WATER = "black_grey_water"
    SECURITY_PATROL_ISPS_DUE = "security_patrol_isps_due"
    
    # Other vessels
    PASSING_VESSEL_DUES = "passing_vessel_dues"
    BUNKERING_CREW_CHANGE_PROVISIONING_DISCOUNT = "bunkering_crew_change_provisioning_discount"
    REPAIRS_LAYING_UP_TANK_CLEANING_FEES = "repairs_laying_up_tank_cleaning_fees"
    SERVICE_VESSELS_NAVAL_SHIP_FEES = "service_vessels_naval_ship_fees"
    PORT_DUES_FOR_CARGO = "port_dues_for_cargo"


class ChargingMethod(str, Enum):
    """How the tariff component is charged.
    
    Defines the unit of measurement or method used to calculate charges.
    Examples include per gross tonnage (GT), per cubic meter, flat fees, etc.
    
    Attributes:
        PER_GT: Charged per Gross Tonnage
        PER_M3: Charged per cubic meter
        PER_TON: Charged per ton
        PER_METRE_LOA: Charged per meter of Length Overall
        FLAT_SEK_PER_CALL: Flat fee in SEK per call
        PER_24H_PERIOD: Charged per 24-hour period
        PER_PASSENGER: Charged per passenger
        PER_TEU: Charged per Twenty-foot Equivalent Unit
        PER_CALL: Charged per call
        PERCENTAGE: Percentage discount or markup
    """
    PER_GT = "per_gt"  # Gross Tonnage
    PER_M3 = "per_m3"  # Cubic meters
    PER_TON = "per_ton"  # Tons
    PER_METRE_LOA = "per_metre_loa"  # Length Overall
    FLAT_SEK_PER_CALL = "flat_sek_per_call"
    PER_24H_PERIOD = "per_24h_period"
    PER_PASSENGER = "per_passenger"
    PER_TEU = "per_teu"  # Twenty-foot Equivalent Unit
    PER_CALL = "per_call"
    PERCENTAGE = "percentage"  # Percentage discount/markup


class Band(BaseModel):
    """Represents a band/threshold for tariff calculation.
    
    Bands define ranges of values (e.g., GT ranges) that determine
    which rate applies. For example, vessels with GT 0-2300 may have
    one rate, while vessels with GT 2301-3300 have another.
    
    Attributes:
        name: Name/identifier for this band (e.g., 'GT_0_500', 'calls_per_week_1_2')
        min_value: Minimum value for this band (inclusive). None means unbounded below.
        max_value: Maximum value for this band (exclusive, or None for unbounded above).
        band_type: Type of band: 'gt', 'calls_per_week', 'volume', 'seasonal', etc.
    """
    name: str = Field(description="Name/identifier for this band (e.g., 'GT_0_500', 'calls_per_week_1_2')")
    min_value: Optional[float] = Field(None, description="Minimum value for this band (inclusive)")
    max_value: Optional[float] = Field(None, description="Maximum value for this band (exclusive, or None for unbounded)")
    band_type: str = Field(description="Type of band: 'gt', 'calls_per_week', 'volume', 'seasonal', etc.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "GT_0_500",
                "min_value": 0,
                "max_value": 500,
                "band_type": "gt"
            }
        }


class Condition(BaseModel):
    """Represents a condition that must be met for a tariff rule to apply.
    
    Conditions define when a tariff rule is applicable. For example,
    a rule might only apply if the vessel arrives from EU ports, or
    if the sludge volume exceeds 11 m³.
    
    Attributes:
        field: Field name to check (e.g., 'arrival_origin', 'sludge_volume', 'calls_per_week')
        operator: Comparison operator: 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in'
        value: Value(s) to compare against. Can be string, number, or list.
        description: Human-readable description of the condition (optional)
    """
    field: str = Field(description="Field name to check (e.g., 'arrival_origin', 'sludge_volume', 'calls_per_week')")
    operator: str = Field(description="Comparison operator: 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in'")
    value: Union[str, float, int, List[Any]] = Field(description="Value(s) to compare against")
    description: Optional[str] = Field(None, description="Human-readable description of the condition")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "field": "arrival_origin",
                    "operator": "eq",
                    "value": "EU",
                    "description": "Arrival from EU"
                },
                {
                    "field": "sludge_volume",
                    "operator": "lte",
                    "value": 11,
                    "description": "Sludge volume ≤ 11 m³"
                },
                {
                    "field": "calls_per_week",
                    "operator": "in",
                    "value": [1, 2],
                    "description": "1-2 calls per week"
                }
            ]
        }


class PricingRule(BaseModel):
    """Defines the pricing formula for a tariff component.
    
    Specifies how to calculate the cost for a tariff component.
    Can use rate-based calculation, flat fees, or percentage discounts/markups.
    
    Attributes:
        rate: Base rate (e.g., SEK per GT, SEK per m³). None if not applicable.
        currency: Currency code (default: "SEK")
        flat_fee: Flat fee amount (if applicable). None if rate-based.
        percentage: Percentage discount or markup (e.g., -10 for 10% discount, +5 for 5% markup)
        formula: Optional formula string for complex calculations
        min_charge: Minimum charge amount (optional)
        max_charge: Maximum charge amount (optional)
    """
    rate: Optional[float] = Field(None, description="Base rate (e.g., SEK per GT, SEK per m³)")
    currency: str = Field(default="SEK", description="Currency code")
    flat_fee: Optional[float] = Field(None, description="Flat fee amount (if applicable)")
    percentage: Optional[float] = Field(None, description="Percentage discount or markup (e.g., -10 for 10% discount, +5 for 5% markup)")
    formula: Optional[str] = Field(None, description="Optional formula string for complex calculations")
    min_charge: Optional[float] = Field(None, description="Minimum charge amount")
    max_charge: Optional[float] = Field(None, description="Maximum charge amount")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "rate": 12.5,
                    "currency": "SEK",
                    "description": "12.5 SEK per GT"
                },
                {
                    "flat_fee": 5000,
                    "currency": "SEK",
                    "description": "Flat 5000 SEK per call"
                },
                {
                    "percentage": -10,
                    "description": "10% discount"
                }
            ]
        }


class TariffRule(BaseModel):
    """Complete tariff rule combining all aspects for a vessel type + component.
    
    A tariff rule defines how a specific component is charged for a specific
    vessel type, including conditions, bands, and pricing.
    
    Attributes:
        vessel_type: Vessel type this rule applies to
        component: Tariff component (due) name
        charging_method: How this component is charged
        bands: Bands/thresholds for this rule (optional - some components may not have bands)
        conditions: Conditions that must be met for this rule to apply (optional)
        pricing: Pricing formula/rate for this rule
        description: Human-readable description of this rule (optional)
        notes: Additional notes or special considerations (optional)
    """
    vessel_type: VesselType = Field(description="Vessel type this rule applies to")
    component: TariffComponent = Field(description="Tariff component (due) name")
    charging_method: ChargingMethod = Field(description="How this component is charged")
    
    # Bands/thresholds (optional - some components may not have bands)
    bands: List[Band] = Field(default_factory=list, description="Bands/thresholds for this rule")
    
    # Conditions (optional - some rules may apply unconditionally)
    conditions: List[Condition] = Field(default_factory=list, description="Conditions that must be met for this rule to apply")
    
    # Pricing
    pricing: PricingRule = Field(description="Pricing formula/rate for this rule")
    
    # Metadata
    description: Optional[str] = Field(None, description="Human-readable description of this rule")
    notes: Optional[str] = Field(None, description="Additional notes or special considerations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vessel_type": "tankers",
                "component": "port_infrastructure_dues",
                "charging_method": "per_gt",
                "bands": [
                    {
                        "name": "GT_0_500",
                        "min_value": 0,
                        "max_value": 500,
                        "band_type": "gt"
                    },
                    {
                        "name": "GT_500_plus",
                        "min_value": 500,
                        "max_value": None,
                        "band_type": "gt"
                    }
                ],
                "conditions": [
                    {
                        "field": "arrival_origin",
                        "operator": "eq",
                        "value": "EU",
                        "description": "Arrival from EU"
                    }
                ],
                "pricing": {
                    "rate": 12.5,
                    "currency": "SEK"
                },
                "description": "Port infrastructure dues for tankers, charged per GT with EU/non-EU rates"
            }
        }


class TariffDatabase(BaseModel):
    """Complete database of all tariff rules.
    
    Container for all tariff rules extracted from the PDF document.
    Provides methods to query and filter rules by vessel type and component.
    
    Attributes:
        rules: All tariff rules in the database
        version: Tariff version/year (default: "2025")
        port_name: Port name (default: "Port of Gothenburg")
    """
    rules: List[TariffRule] = Field(default_factory=list, description="All tariff rules")
    version: str = Field(default="2025", description="Tariff version/year")
    port_name: str = Field(default="Port of Gothenburg", description="Port name")
    
    def get_rules(
        self,
        vessel_type: Optional[VesselType] = None,
        component: Optional[TariffComponent] = None
    ) -> List[TariffRule]:
        """Get rules filtered by vessel type and/or component.
        
        Args:
            vessel_type: Optional vessel type to filter by
            component: Optional component to filter by
        
        Returns:
            List of TariffRule objects matching the filters.
            If both filters are None, returns all rules.
        """
        filtered = self.rules
        if vessel_type:
            filtered = [r for r in filtered if r.vessel_type == vessel_type]
        if component:
            filtered = [r for r in filtered if r.component == component]
        return filtered


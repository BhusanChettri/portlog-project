"""Query-related data models for user input parsing."""

from typing import Optional, Literal
from pydantic import BaseModel, Field

from src.models.schema import VesselType


class VesselDetails(BaseModel):
    """Vessel specifications extracted from user query.
    
    Contains physical and operational characteristics of the vessel
    that are relevant for tariff calculations.
    
    Attributes:
        gross_tonnage_gt: Gross Tonnage (GT) - most common size metric
        deadweight_tonnage_dwt: Deadweight Tonnage (DWT)
        length_overall_m: Length Overall in metres (LOA)
        beam_m: Beam (width) in metres
        draft_m: Draft (depth) in metres
        teu: TEU (Twenty-foot Equivalent Units) for container vessels
        passengers: Number of passengers (for passenger vessels)
    """
    gross_tonnage_gt: Optional[float] = Field(None, description="Gross Tonnage")
    deadweight_tonnage_dwt: Optional[float] = Field(None, description="Deadweight Tonnage")
    length_overall_m: Optional[float] = Field(None, description="Length Overall in metres")
    beam_m: Optional[float] = Field(None, description="Beam in metres")
    draft_m: Optional[float] = Field(None, description="Draft in metres")
    teu: Optional[int] = Field(None, description="TEU (Twenty-foot Equivalent Units)")
    passengers: Optional[int] = Field(None, description="Number of passengers")


class CallContext(BaseModel):
    """Call context information extracted from user query.
    
    Contains information about the vessel's port call, including
    origin, frequency, duration, and operational characteristics.
    
    Attributes:
        arrival_region: Region of arrival: "EU", "non_EU", "domestic", or "unknown"
        previous_port: Previous port name (optional)
        next_port: Next port name (optional)
        calls_per_week_on_service: Number of calls per week on service (for frequency discounts)
        number_of_calls_this_season: Number of calls this season (optional)
        stay_duration_hours: Duration of stay in hours (optional)
        layup_days: Number of layup days (optional)
        is_inland_waterway: Whether vessel uses inland waterways (optional)
        is_short_sea_shipping: Whether vessel is short sea shipping (optional)
        season: Season type: "peak" or "off_peak" (optional)
    """
    arrival_region: Optional[Literal["EU", "non_EU", "domestic", "unknown"]] = Field(None)
    previous_port: Optional[str] = Field(None)
    next_port: Optional[str] = Field(None)
    calls_per_week_on_service: Optional[int] = Field(None)
    number_of_calls_this_season: Optional[int] = Field(None)
    stay_duration_hours: Optional[float] = Field(None)
    layup_days: Optional[int] = Field(None)
    is_inland_waterway: Optional[bool] = Field(None)
    is_short_sea_shipping: Optional[bool] = Field(None)
    season: Optional[Literal["peak", "off_peak"]] = Field(None)


class Quantities(BaseModel):
    """Quantities for tariff calculation extracted from user query.
    
    Contains various quantities that affect tariff calculations,
    such as waste volumes, water usage, cargo tonnage, etc.
    
    Attributes:
        sludge_volume_m3: Sludge volume in cubic meters
        solid_waste_volume_m3: Solid waste volume in cubic meters
        rinsing_water_tons: Rinsing water in tons
        fresh_water_m3: Fresh water in cubic meters
        black_grey_water_m3: Black/grey water in cubic meters
        cargo_tonnage_tons: Cargo tonnage in tons
        electricity_kwh: Electricity usage in kWh
    """
    sludge_volume_m3: Optional[float] = Field(None)
    solid_waste_volume_m3: Optional[float] = Field(None)
    rinsing_water_tons: Optional[float] = Field(None)
    fresh_water_m3: Optional[float] = Field(None)
    black_grey_water_m3: Optional[float] = Field(None)
    cargo_tonnage_tons: Optional[float] = Field(None)
    electricity_kwh: Optional[float] = Field(None)


class Environmental(BaseModel):
    """Environmental information extracted from user query.
    
    Contains environmental certifications and scores that may
    qualify vessels for discounts or affect tariff calculations.
    
    Attributes:
        esi_score: Environmental Ship Index (ESI) score (0-100+)
        csi_class: Clean Shipping Index (CSI) class (optional)
        fossil_free_fuel_share: Percentage of fossil-free fuel (0-1 if percentage given)
        discount_certificate_for_waste: Whether valid waste certificate is presented
    """
    esi_score: Optional[float] = Field(None)
    csi_class: Optional[int] = Field(None)
    fossil_free_fuel_share: Optional[float] = Field(None, description="0-1 if percentage given")
    discount_certificate_for_waste: Optional[bool] = Field(None)


class OpsAndLayup(BaseModel):
    """OPS and layup information extracted from user query.
    
    Contains information about Onshore Power Supply (OPS) usage
    and layup operations that may affect tariff calculations.
    
    Attributes:
        use_ops: Whether vessel uses Onshore Power Supply (OPS)
        yacht_loa_m: Yacht Length Overall in metres (for yacht-specific calculations)
    """
    use_ops: Optional[bool] = Field(None, description="Uses Onshore Power Supply")
    yacht_loa_m: Optional[float] = Field(None, description="Yacht Length Overall in metres")


class QueryIntent(BaseModel):
    """Query intent information extracted from user query.
    
    Classifies the user's intent to help determine the appropriate response.
    
    Attributes:
        type: Intent type: "total_tariff", "component_breakdown", "compare_options", "explanation", or "other"
        description: Short natural-language summary of the query intent
    """
    type: Literal["total_tariff", "component_breakdown", "compare_options", "explanation", "other"]
    description: str = Field(description="Short natural-language summary")


class QueryParameters(BaseModel):
    """Structured parameters extracted from user query.
    
    This is the main data structure that contains all extracted information
    from a natural language query. It groups related parameters into logical
    sub-models for better organization.
    
    Attributes:
        vessel_type: Vessel type string (will be converted to VesselType enum)
        vessel_details: Vessel specifications (GT, DWT, LOA, etc.)
        call_context: Port call context (arrival region, frequency, etc.)
        quantities: Quantities for calculation (sludge, waste, water, etc.)
        environmental: Environmental information (ESI score, certificates, etc.)
        ops_and_layup: OPS and layup information
        query_intent: Query intent classification
        raw_text_notes: Any extra details from the query that don't fit into structured fields
    """
    vessel_type: Optional[str] = Field(None, description="Vessel type (will be converted to VesselType enum)")
    vessel_details: VesselDetails = Field(default_factory=VesselDetails)
    call_context: CallContext = Field(default_factory=CallContext)
    quantities: Quantities = Field(default_factory=Quantities)
    environmental: Environmental = Field(default_factory=Environmental)
    ops_and_layup: OpsAndLayup = Field(default_factory=OpsAndLayup)
    query_intent: QueryIntent
    raw_text_notes: str = Field(default="", description="Any extra details")
    
    def to_calculator_params(self) -> dict:
        """Convert to parameters dict for calculator.
        
        Maps the nested QueryParameters structure to a flat dictionary
        format expected by the TariffCalculator. Handles vessel type
        string-to-enum conversion and field name mappings.
        
        Returns:
            Dictionary with keys:
                - vessel_type: VesselType enum
                - gt: Gross tonnage (float)
                - dwt: Deadweight tonnage (float)
                - loa_metres: Length overall in metres (float)
                - teu: TEU count (int)
                - passenger_count: Passenger count (int)
                - arrival_origin: "EU" or "non-EU" (str)
                - sludge_volume: Sludge volume in m³ (float)
                - volume_m3: Volume in m³ (float)
                - calls_per_week: Calls per week (int)
                - esi_score: ESI score (float)
                - use_ops: Whether OPS is used (bool)
                - is_inland_waterway: Whether inland waterway (bool)
                - discount_certificate_for_waste: Whether waste certificate present (bool)
                - fossil_free_fuel_share: Fossil-free fuel share (float)
        """
        # Convert vessel_type string to enum
        vessel_type_enum = None
        if self.vessel_type:
            # Map common variations to enum values
            vessel_type_map = {
                "tanker": VesselType.TANKERS,
                "container": VesselType.CONTAINER_VESSELS,
                "container_vessel": VesselType.CONTAINER_VESSELS,
                "roro": VesselType.RORO_VESSELS,
                "roro_vessel": VesselType.RORO_VESSELS,
                "car_carrier": VesselType.CAR_CARRIERS,
                "ropax": VesselType.ROPAX_PASSENGER_VESSELS,
                "passenger": VesselType.ROPAX_PASSENGER_VESSELS,
                "cruise": VesselType.CRUISE_VESSELS,
                "yacht": VesselType.YACHTS,
                "break_bulk": VesselType.BREAK_BULK_LOLO_VESSELS,
                "lolo": VesselType.BREAK_BULK_LOLO_VESSELS,
                "inland": VesselType.INLAND_WATERWAYS,
                "archipelago": VesselType.ARCHIPELAGO_TRAFFIC,
                "harbour": VesselType.HARBOUR_VESSELS,
                "other": VesselType.OTHER_VESSELS,
            }
            vessel_type_enum = vessel_type_map.get(self.vessel_type.lower(), None)
            if not vessel_type_enum:
                # Try direct match with enum values
                try:
                    vessel_type_enum = VesselType(self.vessel_type.lower())
                except ValueError:
                    pass
        
        # Map arrival_region to arrival_origin
        arrival_origin = None
        if self.call_context.arrival_region:
            if self.call_context.arrival_region == "EU":
                arrival_origin = "EU"
            elif self.call_context.arrival_region == "non_EU":
                arrival_origin = "non-EU"
        
        return {
            "vessel_type": vessel_type_enum,
            "gt": self.vessel_details.gross_tonnage_gt,
            "dwt": self.vessel_details.deadweight_tonnage_dwt,
            "loa_metres": self.vessel_details.length_overall_m or self.ops_and_layup.yacht_loa_m,
            "teu": self.vessel_details.teu,
            "passenger_count": self.vessel_details.passengers,
            "arrival_origin": arrival_origin,
            "sludge_volume": self.quantities.sludge_volume_m3,
            "volume_m3": self.quantities.sludge_volume_m3 or self.quantities.solid_waste_volume_m3,
            "calls_per_week": self.call_context.calls_per_week_on_service,
            "esi_score": self.environmental.esi_score,
            "use_ops": self.ops_and_layup.use_ops,
            "is_inland_waterway": self.call_context.is_inland_waterway,
            "discount_certificate_for_waste": self.environmental.discount_certificate_for_waste,
            "fossil_free_fuel_share": self.environmental.fossil_free_fuel_share,
        }


"""Deterministic tariff calculator using extracted JSON rules."""

from typing import Dict, List, Optional

from src.core.dataset_loader import TariffLoader
from src.models.schema import TariffDatabase, TariffRule, VesselType
from src.models.utils import (
    check_rule_applicable,
    calculate_component_cost,
    find_applicable_band,
)


class CalculationResult:
    """Result of tariff calculation.
    
    Container for the results of a tariff calculation, including
    total cost, per-component costs, detailed breakdown, and
    applicable rules.
    
    Attributes:
        components: Dictionary mapping component names to costs
        total: Total tariff cost in SEK
        breakdown: List of detailed breakdown dictionaries
        applicable_rules: List of TariffRule objects that were applied
    """
    
    def __init__(self):
        """Initialize an empty calculation result."""
        self.components: Dict[str, float] = {}  # Component name -> cost
        self.total: float = 0.0
        self.breakdown: List[Dict] = []  # Detailed breakdown
        self.applicable_rules: List[TariffRule] = []
    
    def add_component(self, component_name: str, cost: float, rule: TariffRule, details: Dict):
        """Add a component cost to the calculation result.
        
        Adds or accumulates a component cost. If the component already exists,
        the cost is added to the existing value (for additive charges).
        
        Args:
            component_name: Name of the tariff component
            cost: Cost amount in SEK (can be negative for discounts)
            rule: TariffRule object that was applied (can be None for special cases)
            details: Dictionary with additional details (rate, charging_method, band, etc.)
        """
        if component_name in self.components:
            self.components[component_name] += cost
        else:
            self.components[component_name] = cost
        
        self.total += cost
        self.breakdown.append({
            "component": component_name,
            "cost": cost,
            "rule_description": rule.description if rule else component_name,
            "details": details
        })
        self.applicable_rules.append(rule)
    
    def to_dict(self) -> Dict:
        """Convert calculation result to dictionary format.
        
        Returns:
            Dictionary with keys:
                - total: Total cost in SEK
                - components: Dictionary of component names to costs
                - breakdown: List of detailed breakdown dictionaries
                - currency: Currency code ("SEK")
        """
        return {
            "total": self.total,
            "components": self.components,
            "breakdown": self.breakdown,
            "currency": "SEK"
        }


class TariffCalculator:
    """Deterministic tariff calculator using extracted JSON rules.
    
    This is the core calculation engine that applies tariff rules
    deterministically based on vessel parameters. It handles:
    - Rule filtering by vessel type and conditions
    - Band matching for tiered rates
    - Component exclusivity (e.g., only one port infrastructure dues)
    - Special cases (ESI discounts, excess sludge charges, etc.)
    - Additive charges (discounts, excess volumes)
    
    The calculator is deterministic - it does not use LLM inference,
    only structured rule matching and arithmetic.
    """
    
    def __init__(self, database: Optional[TariffDatabase] = None):
        """
        Initialize calculator.
        
        Args:
            database: TariffDatabase (if None, loads from default location)
        """
        if database is None:
            database = TariffLoader.load_default()
            if database is None:
                raise ValueError("No tariff database found. Run extraction first.")
        
        self.database = database
    
    def calculate(self, parameters: Dict) -> CalculationResult:
        """Calculate tariff for given parameters.
        
        Processes all applicable tariff rules for the vessel type,
        checks conditions, matches bands, and calculates costs.
        Handles special cases like ESI discounts and excess sludge charges.
        
        Args:
            parameters: Dictionary containing:
                - vessel_type: VesselType enum (required)
                - gt: Gross tonnage (float, optional)
                - dwt: Deadweight tonnage (float, optional)
                - volume_m3: Volume in cubic meters (float, optional)
                - tonnage: Tonnage (float, optional)
                - loa_metres: Length overall in metres (float, optional)
                - passenger_count: Number of passengers (int, optional)
                - teu: TEU count (int, optional)
                - arrival_origin: "EU" or "non-EU" (str, optional)
                - sludge_volume: Sludge volume in m³ (float, optional)
                - calls_per_week: Calls per week (int, optional)
                - esi_score: ESI score (float, optional)
                - use_ops: Whether OPS is used (bool, optional)
                - is_inland_waterway: Whether inland waterway (bool, optional)
                - discount_certificate_for_waste: Whether waste certificate present (bool, optional)
                - fossil_free_fuel_share: Fossil-free fuel share (float, optional)
        
        Returns:
            CalculationResult object with total cost, component breakdown,
            and applicable rules. Returns empty result if vessel_type is missing.
        
        Note:
            Rules are sorted by priority (fewer bands/conditions = more specific = higher priority).
            Exclusive components (e.g., port_infrastructure_dues) are only applied once.
            ESI discount (10%) is applied automatically if esi_score >= 30.
        """
        result = CalculationResult()
        
        # Get vessel type
        vessel_type = parameters.get("vessel_type")
        if not vessel_type:
            return result  # Can't calculate without vessel type
        
        # Get all rules for this vessel type
        rules = self.database.get_rules(vessel_type=vessel_type)
        
        # Build context for condition checking
        context = {
            "gt": parameters.get("gt", 0),
            "dwt": parameters.get("dwt", 0),
            "volume_m3": parameters.get("volume_m3", 0),
            "tonnage": parameters.get("tonnage", 0),
            "loa_metres": parameters.get("loa_metres", 0),
            "passenger_count": parameters.get("passenger_count", 0),
            "teu": parameters.get("teu", 0),
            "arrival_origin": parameters.get("arrival_origin"),
            "arrival_region": parameters.get("arrival_origin"),
            "sludge_volume": parameters.get("sludge_volume"),
            "calls_per_week": parameters.get("calls_per_week"),
            "esi_score": parameters.get("esi_score"),
            "use_ops": parameters.get("use_ops"),
            "is_inland_waterway": parameters.get("is_inland_waterway"),
            "discount_certificate_for_waste": parameters.get("discount_certificate_for_waste"),
            "fossil_free_fuel_share": parameters.get("fossil_free_fuel_share"),
        }
        
        # Track which components have been applied (to avoid duplicates for banded rules)
        applied_components = set()
        
        # Sort rules: prioritize rules with fewer bands/conditions (more specific)
        def rule_priority(rule):
            priority = 999  # Default priority
            
            # For port infrastructure dues, prefer rules with fewer bands
            if rule.component.value == "port_infrastructure_dues" and rule.bands:
                priority = len(rule.bands)
            
            # For solid waste and sludge, prefer rules with fewer conditions
            elif rule.component.value in ["ship_generated_solid_waste", "sludge_oily_bilge_water"]:
                arrival_conditions = [c for c in rule.conditions if c.field in ["arrival port", "arrival_region"]]
                if len(arrival_conditions) > 1:
                    priority = 100 + len(rule.conditions)
                else:
                    priority = len(rule.conditions)
            
            return priority
        
        sorted_rules = sorted(rules, key=rule_priority)
        
        # Process each rule
        for rule in sorted_rules:
            # Check if rule applies
            if not check_rule_applicable(rule, context):
                continue
            
            # For exclusive components, skip if we've already applied one
            exclusive_components = ["port_infrastructure_dues"]
            
            # For solid waste and sludge, only exclude if it's a base charge (per_gt) with positive rate
            if rule.component.value == "ship_generated_solid_waste":
                if (rule.charging_method.value == "per_gt" and 
                    rule.pricing.rate and 
                    rule.pricing.rate > 0 and
                    "ship_generated_solid_waste" in applied_components):
                    continue
            
            if rule.component.value == "sludge_oily_bilge_water":
                if rule.charging_method.value == "per_gt" and rule.component.value in applied_components:
                    continue
                if rule.charging_method.value == "per_m3":
                    pass  # Always allow excess charges
            
            if rule.component.value in exclusive_components:
                if rule.component.value in applied_components:
                    continue
            
            # Find applicable band if any
            band = None
            if rule.bands:
                band_value = context.get("gt", 0)
                if rule.charging_method.value in ["per_m3", "per_ton"]:
                    band_value = context.get("volume_m3", context.get("tonnage", 0))
                
                band = find_applicable_band(rule, band_value, "standard")
                if not band:
                    band = find_applicable_band(rule, band_value, "gt_range")
                
                if not band:
                    continue
                
                # Skip if more specific rule already matched
                if (rule.component.value == "port_infrastructure_dues" and 
                    len(rule.bands) > 1 and 
                    rule.component.value in applied_components):
                    continue
            
            # Mark this component as applied
            if rule.component.value in exclusive_components:
                if rule.component.value == "port_infrastructure_dues":
                    if rule.component.value in applied_components:
                        continue
                    if band or not rule.bands:
                        applied_components.add(rule.component.value)
                else:
                    applied_components.add(rule.component.value)
            elif (rule.component.value == "ship_generated_solid_waste" and 
                  rule.charging_method.value == "per_gt" and 
                  rule.pricing.rate and 
                  rule.pricing.rate > 0):
                applied_components.add(rule.component.value)
            elif rule.component.value == "sludge_oily_bilge_water" and rule.charging_method.value == "per_gt":
                applied_components.add(rule.component.value)
            
            # Special handling for sludge exceeding 11m³
            quantity_override = None
            if (rule.component.value == "sludge_oily_bilge_water" and 
                rule.charging_method.value == "per_m3" and
                context.get("sludge_volume", 0) > 11):
                has_exceeding_condition = any(
                    cond.field in ["quantity", "sludge_volume"] and 
                    "more than" in str(cond.operator).lower() and
                    "11" in str(cond.value)
                    for cond in rule.conditions
                )
                if has_exceeding_condition:
                    excess_volume = context.get("sludge_volume", 0) - 11
                    quantity_override = excess_volume
            
            # Calculate cost
            cost = calculate_component_cost(rule, context, quantity=quantity_override)
            
            # Handle discounts (negative costs) and regular charges
            if cost != 0:
                details = {
                    "charging_method": rule.charging_method.value,
                    "rate": rule.pricing.rate,
                    "currency": rule.pricing.currency,
                }
                if band:
                    details["band"] = f"{band.get('min_value', '')}-{band.get('max_value', '')}"
                if rule.pricing.percentage:
                    details["percentage"] = rule.pricing.percentage
                
                result.add_component(
                    component_name=rule.component.value,
                    cost=cost,
                    rule=rule,
                    details=details
                )
        
        # Apply ESI discount to port infrastructure dues if applicable
        esi_score = context.get("esi_score", 0)
        if esi_score is not None and esi_score >= 30:
            port_dues_cost = result.components.get("port_infrastructure_dues", 0)
            if port_dues_cost > 0:
                esi_discount = port_dues_cost * -0.10
                result.add_component(
                    component_name="environmental_discounts",
                    cost=esi_discount,
                    rule=None,
                    details={
                        "type": "ESI_discount",
                        "percentage": -10,
                        "applied_to": "port_infrastructure_dues"
                    }
                )
        
        return result


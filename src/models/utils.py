"""Utility functions for working with tariff models."""

from typing import Dict, Any, Optional
from src.models.schema import (
    TariffRule,
    Condition,
    VesselType,
    TariffComponent,
    ChargingMethod,
)


def evaluate_condition(condition: Condition, context: Dict[str, Any]) -> bool:
    """Evaluate whether a condition is met given a context dictionary.
    
    This function evaluates a single condition against the provided context.
    It handles field name mapping, type conversion for numeric comparisons,
    and various operator formats (e.g., "from", "must" are treated as "equals").
    
    Special handling:
    - Maps field names from extracted rules to context field names
    - Handles EU/non-EU matching with various string formats
    - Converts string numbers to numeric types for comparisons
    - Supports multiple operator formats (eq, =, ==, equals, from, must, etc.)
    
    Args:
        condition: The Condition object to evaluate
        context: Dictionary containing field values (e.g., {'arrival_origin': 'EU', 'sludge_volume': 10})
    
    Returns:
        True if condition is met, False otherwise. Returns False if field value is None.
    """
    # Map field names from extracted rules to context field names
    field_mapping = {
        "arrival port": "arrival_origin",  # From extracted rules
        "arrival_region": "arrival_origin",  # From new query structure
        "sludge_volume": "sludge_volume",
        "sludge_volume_m3": "sludge_volume",
        "quantity": "sludge_volume",  # Generic quantity often refers to sludge
        "calls_per_week": "calls_per_week",
        "calls_per_week_on_service": "calls_per_week",
        "certificates": "discount_certificate_for_waste",  # Waste certificate
        "ESI score": "esi_score",
        "fossil-free fuel percentage": "fossil_free_fuel_share",
    }
    
    # Get the actual field name to look up
    lookup_field = field_mapping.get(condition.field, condition.field)
    field_value = context.get(lookup_field)
    
    # Also try direct lookup if mapping didn't work
    if field_value is None:
        field_value = context.get(condition.field)
    
    if field_value is None:
        return False
    
    operator = condition.operator.lower() if isinstance(condition.operator, str) else condition.operator
    target_value = condition.value
    
    # Try to convert types for numeric comparisons
    def try_convert_to_number(val):
        """Try to convert value to number if possible."""
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            # Try to extract number from string
            import re
            numbers = re.findall(r'\d+\.?\d*', val)
            if numbers:
                try:
                    return float(numbers[0])
                except ValueError:
                    pass
        return val
    
    # For numeric comparisons, try to convert both values
    numeric_operators = ["gt", ">", "greater_than", "more than", "gte", ">=", "greater_than_or_equal", 
                         "at least", "lt", "<", "less_than", "less than", "lte", "<=", "less_than_or_equal", "at most"]
    if operator in numeric_operators:
        field_value = try_convert_to_number(field_value)
        target_value = try_convert_to_number(target_value)
        # If both are numbers, proceed with comparison
        if isinstance(field_value, (int, float)) and isinstance(target_value, (int, float)):
            pass  # Continue with numeric comparison
        else:
            # Fall back to string comparison
            field_value = str(field_value)
            target_value = str(target_value)
    
    # Handle operator variations
    if operator in ["eq", "=", "==", "equals", "from", "must"]:  # "from" and "must" mean "equals" in extracted data
        # For "arrival port" conditions, check if value matches
        if condition.field in ["arrival port", "arrival_region"]:
            # Map target values - handle both EU and non-EU cases
            if isinstance(target_value, str):
                target_lower = target_value.lower()
                field_lower = str(field_value).lower() if field_value else ""
                
                # Check for non-EU match FIRST (before EU check, since "non-european" contains "european")
                if "non" in target_lower:
                    # Target is non-EU/non-European - check if field value indicates non-EU
                    # Accept various formats: "non-EU", "non_EU", etc.
                    non_eu_indicators = ["non-eu", "non_eu", "non-europe", "non_europe", "non-european", "non_european"]
                    return (field_lower in non_eu_indicators or 
                            field_value in ["non-EU", "non_EU"] or
                            (isinstance(field_value, str) and "non" in field_lower and ("eu" in field_lower or "europe" in field_lower)))
                
                # Check for EU match (only if not non-EU)
                elif "eu" in target_lower or "europe" in target_lower or "european" in target_lower:
                    # Target is EU/European - check if field value indicates EU
                    return field_lower in ["eu", "europe", "european"] or field_value == "EU"
            
            # Fallback to exact match
            return str(field_value).lower() == str(target_value).lower()
        # For "certificates" field, check boolean
        if condition.field == "certificates":
            if isinstance(target_value, str):
                target_lower = target_value.lower()
                if "valid" in target_lower or "has" in target_lower or "true" in target_lower:
                    return bool(field_value) is True
            return bool(field_value) == bool(target_value)
        return field_value == target_value
    elif operator in ["ne", "!=", "<>", "not_equals"]:
        return field_value != target_value
    elif operator in ["gt", ">", "greater_than", "more than"]:  # "more than" means "greater than"
        return field_value > target_value
    elif operator in ["gte", ">=", "greater_than_or_equal", "at least"]:
        return field_value >= target_value
    elif operator in ["lt", "<", "less_than", "less than"]:
        return field_value < target_value
    elif operator in ["lte", "<=", "less_than_or_equal", "at most"]:
        return field_value <= target_value
    elif operator in ["in", "contains"]:
        if isinstance(target_value, (list, tuple)):
            return field_value in target_value
        return str(field_value) in str(target_value)
    elif operator in ["not_in", "not contains"]:
        if isinstance(target_value, (list, tuple)):
            return field_value not in target_value
        return str(field_value) not in str(target_value)
    else:
        # Default: try equality if operator is unknown
        return str(field_value).lower() == str(target_value).lower()


def check_rule_applicable(rule: TariffRule, context: Dict[str, Any]) -> bool:
    """Check if a tariff rule is applicable given the context.
    
    Evaluates all conditions of a rule against the context. If a rule has
    no conditions, it is always applicable. Special handling for conflicting
    conditions on the same field (e.g., both EU and non-EU) treats them as OR logic.
    
    Args:
        rule: The TariffRule object to check
        context: Dictionary containing field values for condition evaluation
    
    Returns:
        True if all conditions are met (or rule has no conditions), False otherwise.
        
    Note:
        If a rule has multiple "arrival port" conditions (likely a data extraction error),
        they are treated as OR logic - if ANY matches, the group applies.
    """
    if not rule.conditions:
        return True  # No conditions means rule always applies
    
    # Special handling: If a rule has conflicting conditions on the same field
    # (e.g., both "from European ports" and "from non-European ports"),
    # this is likely a data extraction error. Treat it as OR, not AND.
    # Check if we have multiple "arrival port" conditions with "from" operator
    arrival_port_conditions = [
        cond for cond in rule.conditions 
        if cond.field in ["arrival port", "arrival_region"] and cond.operator.lower() in ["from", "eq", "="]
    ]
    
    if len(arrival_port_conditions) > 1:
        # Multiple arrival port conditions - check if ANY matches (OR logic)
        # This handles incorrectly extracted rules that have both EU and non-EU conditions
        other_conditions = [cond for cond in rule.conditions if cond not in arrival_port_conditions]
        arrival_matches = any(evaluate_condition(cond, context) for cond in arrival_port_conditions)
        other_match = all(evaluate_condition(cond, context) for cond in other_conditions) if other_conditions else True
        return arrival_matches and other_match
    
    # Normal case: all conditions must match (AND logic)
    return all(evaluate_condition(cond, context) for cond in rule.conditions)


def find_applicable_band(
    rule: TariffRule,
    value: float,
    band_type: str = "gt"
) -> Optional[Dict[str, Any]]:
    """Find the applicable band for a given value.
    
    Searches through the rule's bands to find one that matches the given value.
    A band matches if: min_value <= value < max_value (or unbounded if None).
    
    If the specified band_type doesn't match, it tries alternative band types
    ("standard", "gt_range") for backward compatibility.
    
    Args:
        rule: The TariffRule object containing bands
        value: The value to find band for (e.g., GT value, volume, etc.)
        band_type: Type of band to match (e.g., "gt", "standard", "gt_range", "calls_per_week")
    
    Returns:
        Band dictionary (from model_dump()) if found, None otherwise.
        The dictionary contains: name, min_value, max_value, band_type.
    """
    # Try the specified band_type first
    for band in rule.bands:
        if band.band_type != band_type:
            continue
        
        min_val = band.min_value if band.min_value is not None else float('-inf')
        max_val = band.max_value if band.max_value is not None else float('inf')
        
        if min_val <= value < max_val:
            return band.model_dump()
    
    # If no match found and band_type is "gt", try "standard" or "gt_range"
    if band_type == "gt":
        for alt_type in ["standard", "gt_range"]:
            for band in rule.bands:
                if band.band_type != alt_type:
                    continue
                
                min_val = band.min_value if band.min_value is not None else float('-inf')
                max_val = band.max_value if band.max_value is not None else float('inf')
                
                if min_val <= value < max_val:
                    return band.model_dump()
    
    return None


def calculate_component_cost(
    rule: TariffRule,
    context: Dict[str, Any],
    quantity: Optional[float] = None
) -> float:
    """Calculate the cost for a tariff component based on a rule and context.
    
    Calculates the cost using the rule's pricing information. Supports:
    - Rate-based calculation (rate × quantity)
    - Flat fees
    - Percentage discounts/markups
    - Min/max charge constraints
    
    Args:
        rule: The TariffRule object to apply
        context: Dictionary containing field values (GT, volume, etc.)
        quantity: Optional quantity override. If None, quantity is determined
                 from context based on the charging method.
    
    Returns:
        Calculated cost in SEK (currency from rule.pricing.currency).
        Returns 0.0 if no pricing information is available.
    """
    pricing = rule.pricing
    
    # Determine quantity based on charging method
    if quantity is None:
        quantity = _get_quantity_for_charging_method(rule.charging_method, context)
    
    # Calculate base cost
    if pricing.rate is not None:
        cost = pricing.rate * quantity
    elif pricing.flat_fee is not None:
        cost = pricing.flat_fee
    else:
        cost = 0.0
    
    # Apply percentage discount/markup
    if pricing.percentage is not None:
        # If percentage is positive, it's a markup; if negative, it's a discount
        # The percentage is already in the correct sign (e.g., -10 for 10% discount)
        cost = cost * (1 + pricing.percentage / 100)
    
    # Apply min/max constraints
    if pricing.min_charge is not None:
        cost = max(cost, pricing.min_charge)
    if pricing.max_charge is not None:
        cost = min(cost, pricing.max_charge)
    
    return cost


def _get_quantity_for_charging_method(
    charging_method: ChargingMethod,
    context: Dict[str, Any]
) -> float:
    """Extract quantity from context based on charging method.
    
    Maps charging methods to their corresponding context field names
    and extracts the appropriate quantity value.
    
    Args:
        charging_method: The ChargingMethod enum value
        context: Dictionary containing field values
    
    Returns:
        Quantity value from context. Returns 1.0 for flat fees/per call,
        0.0 if field not found or charging method not mapped.
    """
    mapping = {
        ChargingMethod.PER_GT: "gt",
        ChargingMethod.PER_M3: "volume_m3",
        ChargingMethod.PER_TON: "tonnage",
        ChargingMethod.PER_METRE_LOA: "loa_metres",
        ChargingMethod.PER_PASSENGER: "passenger_count",
        ChargingMethod.PER_TEU: "teu",
    }
    
    field_name = mapping.get(charging_method)
    if field_name:
        return context.get(field_name, 0.0)
    
    # For flat fees or per call, return 1
    if charging_method in [ChargingMethod.FLAT_SEK_PER_CALL, ChargingMethod.PER_CALL]:
        return 1.0
    
    return 0.0


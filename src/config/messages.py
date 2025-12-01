"""User-facing messages and error strings.

This module centralizes all user-facing messages to improve maintainability
and enable future internationalization (i18n) support.
"""

# Error Messages
ERROR_CALCULATION_FAILED = (
    "I couldn't calculate the tariff. Please provide more details about the vessel type and specifications."
)

ERROR_NO_PARAMETERS = "No parameters extracted"
ERROR_VESSEL_TYPE_NOT_IDENTIFIED = "Vessel type not identified"

# Status Messages
STATUS_NO_ADDITIONAL_CONTEXT = "No additional context available."

# Format Strings (for internal calculation result formatting)
FORMAT_TOTAL_LABEL = "Total:"
FORMAT_BREAKDOWN_LABEL = "Breakdown:"
FORMAT_RATE_LABEL = "Rate:"
FORMAT_PER_UNIT = "per"

# Default Values
DEFAULT_UNKNOWN_SOURCE = "unknown"


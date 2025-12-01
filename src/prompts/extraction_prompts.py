"""Prompts for data extraction from PDF."""

from langchain_core.prompts import PromptTemplate


EXTRACTION_PROMPT = PromptTemplate.from_template(
    """
You are extracting **port tariff rules** from a PDF snippet. Your job is to convert ONLY the
information that actually appears in this snippet into structured rules.

This snippet may cover:
- one or several vessel types, and/or
- one or several tariff components,
- or only part of a table or description.

Do NOT invent rules, bands, or conditions that are not explicitly present in the text.

Supported vessel types (must choose one of these for each rule):
{vessel_types}

Supported component names (must choose one of these for each rule):
{component_names}

For each rule you find, extract:

1. **vessel_type** - one of the supported vessel types.
2. **component** - one of the supported component names.
3. **charging_method** - how the charge is applied, such as:
   - "per_gt", "per_gt_banded", "per_m3", "per_ton",
   - "per_m_loa_day", "flat_sek_per_call", "flat_sek_per_day",
   - "percentage_discount", "surcharge", etc.
4. **bands/thresholds (if any)** - GT bands, volume bands, call-frequency bands, seasonal bands, etc.
5. **conditions (if any)** - EU vs non-EU, volume > 11 m3, “from 7th call”, “off-season”, etc.
6. **pricing** - numeric rate(s), currency, and any percentage discounts/markups.
7. **description** - short free-text summary in your own words.

Important global rules:
- Work ONLY with the content in this `PDF Content` chunk.
- If information is missing (e.g., the snippet cuts off a table), either:
  - skip that incomplete rule, OR
  - include it but clearly note missing parts in `extraction_notes`.
- Be precise with numbers (including decimal separators).
- Use `"SEK"` as currency where the text implies Swedish kronor.
- When there are multiple rows in a table, create **multiple rules** or multiple bands inside
  one rule, whichever is more natural given the structure.
- Prefer **one rule with multiple bands** for a single component table (e.g. GT ranges),
  rather than separate rules with identical conditions.

You must return a SINGLE JSON object with this EXACT outer structure:

{{
  "rules": "[JSON array string with all rules]",
  "extraction_notes": "Any notes about ambiguity, truncation, or assumptions."
}}

The `rules` field is a **string** containing a JSON array. Each element in that array is a rule object:

- vessel_type: string (one of: {vessel_types})
- component: string (one of: {component_names})
- charging_method: string
- bands: array of objects with:
    - name: string (e.g. "0-2300 GT band")
    - band_type: string (e.g. "gt_range", "volume_range", "calls_per_week", "season")
    - min_value: number or null
    - max_value: number or null (null means "no upper limit")
- conditions: array of objects with:
    - field: string (e.g. "arrival_region", "sludge_volume_m3", "call_number", "season")
    - operator: string (e.g. "=", "!=", "<", "<=", ">", ">=", "in", "between")
    - value: string or number
    - description: short human-readable explanation
- pricing: object with fields such as:
    - rate: number (the main numeric rate for this rule, if applicable)
    - rate_unit: string (e.g. "SEK_per_GT", "SEK_per_m3", "SEK_per_m_loa_day", "SEK_per_call")
    - currency: string (e.g. "SEK")
    - percentage: number (for percentage discounts or markups, e.g. 10 for 10%)
    - flat_amount: number (for flat SEK charges, if any)
- description: string (optional, short)

The `rules` string MUST be valid JSON when parsed.

---

### Examples

These are examples based on similar kinds of content. Follow the same pattern.

Example 1 - Tanker port infrastructure dues table

PDF Content (example):
"PORT INFRASTRUCTURE DUES 0 - 2 300 GT 3,04 SEK/GT 2 301 - 3 300 GT 3,70 SEK/GT
3 301 - 15 000 GT 4,08 SEK/GT > 15 001 GT 5,75 SEK/GT."

Expected JSON (outer object):

{{
  "rules": "[{{\\"vessel_type\\": \\"tanker\\", \\"component\\": \\"port_infrastructure_dues\\", \\"charging_method\\": \\"per_gt_banded\\", \\"bands\\": [{{\\"name\\": \\"0-2300 GT\\", \\"band_type\\": \\"gt_range\\", \\"min_value\\": 0, \\"max_value\\": 2300}}, {{\\"name\\": \\"2301-3300 GT\\", \\"band_type\\": \\"gt_range\\", \\"min_value\\": 2301, \\"max_value\\": 3300}}, {{\\"name\\": \\"3301-15000 GT\\", \\"band_type\\": \\"gt_range\\", \\"min_value\\": 3301, \\"max_value\\": 15000}}, {{\\"name\\": \\">15001 GT\\", \\"band_type\\": \\"gt_range\\", \\"min_value\\": 15001, \\"max_value\\": null}}], \\"conditions\\": [], \\"pricing\\": {{\\"rate\\": null, \\"rate_unit\\": \\"SEK_per_GT\\", \\"currency\\": \\"SEK\\", \\"percentage\\": null, \\"flat_amount\\": null}}, \\"description\\": \\"Band-based port infrastructure dues per GT for tankers based on gross tonnage ranges.\\"}}]",
  "extraction_notes": "Single component table for tanker port infrastructure dues."
}}

Note: here the per-band numeric rates are encoded implicitly in `description` or could also be
placed in an extended pricing structure per band; for this assignment we keep the rates in the bands
as part of the description if your schema does not allow nested rates per band.

(If you prefer, you may instead add a `rate` field inside each band. Be consistent.)

---

Example 2 - Solid waste dues with EU vs non-EU and discount

PDF Content (example):
"DUES FOR SHIP-GENERATED SOLID WASTE. Vessels from European ports: 0,13 SEK/GT.
Vessels from non-European ports: 0,24 SEK/GT. Ships with a valid waste certificate
receive a discount of 0,05 SEK/GT."

Expected `rules` string (simplified):

"[{{\\"vessel_type\\": \\"tanker\\", \\"component\\": \\"solid_waste\\", \\"charging_method\\": \\"per_gt\\", \\"bands\\": [], \\"conditions\\": [{{\\"field\\": \\"arrival_region\\", \\"operator\\": \\"=\\", \\"value\\": \\"EU\\", \\"description\\": \\"Vessel arrives from a European port.\\"}}], \\"pricing\\": {{\\"rate\\": 0.13, \\"rate_unit\\": \\"SEK_per_GT\\", \\"currency\\": \\"SEK\\", \\"percentage\\": null, \\"flat_amount\\": null}}, \\"description\\": \\"Solid waste dues per GT for vessels from European ports.\\"}}, {{\\"vessel_type\\": \\"tanker\\", \\"component\\": \\"solid_waste\\", \\"charging_method\\": \\"per_gt\\", \\"bands\\": [], \\"conditions\\": [{{\\"field\\": \\"arrival_region\\", \\"operator\\": \\"=\\", \\"value\\": \\"non_EU\\", \\"description\\": \\"Vessel arrives from a non-European port.\\"}}], \\"pricing\\": {{\\"rate\\": 0.24, \\"rate_unit\\": \\"SEK_per_GT\\", \\"currency\\": \\"SEK\\", \\"percentage\\": null, \\"flat_amount\\": null}}, \\"description\\": \\"Solid waste dues per GT for vessels from non-European ports.\\"}}, {{\\"vessel_type\\": \\"tanker\\", \\"component\\": \\"solid_waste\\", \\"charging_method\\": \\"per_gt\\", \\"bands\\": [], \\"conditions\\": [{{\\"field\\": \\"has_waste_certificate\\", \\"operator\\": \\"=\\", \\"value\\": true, \\"description\\": \\"Ship has a valid waste reduction certificate.\\"}}], \\"pricing\\": {{\\"rate\\": -0.05, \\"rate_unit\\": \\"SEK_per_GT\\", \\"currency\\": \\"SEK\\", \\"percentage\\": null, \\"flat_amount\\": null}}, \\"description\\": \\"Discount per GT for vessels with valid waste certificate.\\"}}]"

---

Now process the actual PDF snippet below and extract ALL rules you can find,
following the schema and style above.

PDF Content:
{pdf_content}
"""
)

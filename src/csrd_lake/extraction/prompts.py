"""Prompt template + ESRS metric catalog for LLM extraction.

The catalog is a focused subset (≤80 metrics) covering 5 ESRS topics:
E1 (climate), E2 (pollution), E3 (water), S1 (workforce), G1 (governance).
Per PRD §8, the full ESRS catalog is out-of-scope for v1.
"""

from __future__ import annotations

from csrd_lake.extraction.schemas import ESRSTopic

# ── Catalog of metrics we ask the LLM to find per ESRS topic ──────────
# Each metric has: an ID (used as the dbt model key), a human-readable name,
# the unit (or 'text' / 'boolean' / 'count'), and the data type.

ESRS_METRIC_CATALOG: dict[ESRSTopic, list[dict[str, str]]] = {
    ESRSTopic.E1_CLIMATE: [
        {"id": "E1-6.scope_1", "name": "Total Scope 1 GHG emissions", "unit": "tCO2e"},
        {
            "id": "E1-6.scope_2_market",
            "name": "Total Scope 2 GHG emissions (market-based)",
            "unit": "tCO2e",
        },
        {
            "id": "E1-6.scope_2_location",
            "name": "Total Scope 2 GHG emissions (location-based)",
            "unit": "tCO2e",
        },
        {"id": "E1-6.scope_3", "name": "Total Scope 3 GHG emissions", "unit": "tCO2e"},
        {"id": "E1-5.energy_total", "name": "Total energy consumption", "unit": "MWh"},
        {
            "id": "E1-5.energy_renewable_pct",
            "name": "Renewable share of total energy consumption",
            "unit": "%",
        },
        {
            "id": "E1-1.transition_plan_exists",
            "name": "Climate transition plan disclosed",
            "unit": "boolean",
        },
        {"id": "E1-2.net_zero_target_year", "name": "Net-zero target year", "unit": "year"},
    ],
    ESRSTopic.E2_POLLUTION: [
        {"id": "E2-4.air_pollutants", "name": "Total air pollutant emissions", "unit": "tonnes"},
        {"id": "E2-5.substances_concern", "name": "Use of substances of concern", "unit": "tonnes"},
    ],
    ESRSTopic.E3_WATER: [
        {"id": "E3-4.water_consumption", "name": "Total water consumption", "unit": "m3"},
        {
            "id": "E3-4.water_withdrawal_stress",
            "name": "Water withdrawal in water-stressed areas",
            "unit": "m3",
        },
    ],
    ESRSTopic.S1_WORKFORCE: [
        {"id": "S1-6.headcount_total", "name": "Total employees (headcount)", "unit": "count"},
        {
            "id": "S1-9.gender_diversity_top_mgmt_pct",
            "name": "% women in top management",
            "unit": "%",
        },
        {
            "id": "S1-14.work_related_injuries",
            "name": "Number of recordable work-related injuries",
            "unit": "count",
        },
        {
            "id": "S1-14.fatalities",
            "name": "Number of fatalities from work-related injuries",
            "unit": "count",
        },
        {"id": "S1-16.pay_gap_pct", "name": "Gender pay gap (median)", "unit": "%"},
    ],
    ESRSTopic.G1_GOVERNANCE: [
        {
            "id": "G1-3.confirmed_corruption_incidents",
            "name": "Confirmed incidents of corruption or bribery",
            "unit": "count",
        },
        {
            "id": "G1-1.business_conduct_policy_exists",
            "name": "Business-conduct policy disclosed",
            "unit": "boolean",
        },
    ],
}


# Tool-use schema (Anthropic) / JSON schema (Mistral) for structured extraction.
# Keys mirror ESRSMetric except confidence_score (LLM self-rates as model_confidence)
# and audit fields the host code populates.
EXTRACTION_TOOL_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["metrics"],
    "properties": {
        "metrics": {
            "type": "array",
            "description": "Extracted ESRS metrics from the supplied report excerpt.",
            "items": {
                "type": "object",
                "required": [
                    "esrs_disclosure",
                    "metric_name",
                    "model_confidence",
                    "source_page",
                    "source_snippet",
                ],
                "properties": {
                    "esrs_disclosure": {
                        "type": "string",
                        "description": "ESRS disclosure code (e.g. 'E1-6', 'S1-9').",
                    },
                    "metric_name": {
                        "type": "string",
                        "description": "Human-readable metric name from the catalog.",
                    },
                    "value_numeric": {
                        "type": ["number", "null"],
                        "description": "Numeric value if applicable; else null.",
                    },
                    "value_text": {
                        "type": ["string", "null"],
                        "description": "Text value if applicable (e.g. boolean as 'Yes'/'No'); else null.",
                    },
                    "unit": {
                        "type": ["string", "null"],
                        "description": "Unit of measure (tCO2e, MWh, %, count, year, ...).",
                    },
                    "model_confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Self-rated confidence in the extraction quality (0-1).",
                    },
                    "source_page": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "1-indexed page number in the source PDF.",
                    },
                    "source_snippet": {
                        "type": "string",
                        "minLength": 20,
                        "description": "Verbatim text from the report supporting the value.",
                    },
                },
            },
        }
    },
}


def build_extraction_prompt(
    pdf_text: str,
    company_name: str,
    fiscal_year: int,
    esrs_topic: ESRSTopic,
    language: str,
) -> str:
    """Render the extraction prompt for one ESRS topic on one company chunk."""
    catalog = ESRS_METRIC_CATALOG.get(esrs_topic, [])
    catalog_lines = "\n".join(f"  - {m['id']}: {m['name']} (unit: {m['unit']})" for m in catalog)

    return f"""You are extracting ESRS sustainability metrics from a corporate report.

Company: {company_name}
Fiscal year: {fiscal_year}
ESRS topic: {esrs_topic.value}
Document language: {language}

Catalog of metrics to look for under {esrs_topic.value}:
{catalog_lines}

Rules:
1. Only extract values that appear LITERALLY in the report excerpt below.
2. If a metric is not disclosed, omit it (do not invent or estimate).
3. Each metric MUST include the page number (source_page) and a verbatim snippet (source_snippet, ≥20 chars) supporting the value.
4. model_confidence reflects YOUR self-rated certainty in [0, 1].
5. Boolean metrics: use value_text 'Yes' or 'No'; value_numeric null.
6. Numeric metrics: use value_numeric (raw number); value_text null.

Report excerpt:
---
{pdf_text}
---
"""

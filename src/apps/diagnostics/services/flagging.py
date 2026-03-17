"""Auto-flagging service for lab result values.

Parses reference ranges in various formats and computes flags:
- N  = Normal (within reference range)
- H  = High (above upper limit)
- L  = Low (below lower limit)
- CRITICAL_H = Critically high (above critical upper limit)
- CRITICAL_L = Critically low (below critical lower limit)
"""

import logging
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Regex patterns for common ref range formats
# Matches: "13.5-17.5", "0.1 - 1.2", "< 200", "> 40", "<4.0", ">= 30"
RANGE_PATTERN = re.compile(
    r"^\s*"
    r"(?:"
    r"(?P<lt>[<≤])\s*(?P<lt_val>[\d.]+)"  # < 200 or ≤ 200
    r"|(?P<gt>[>≥])\s*(?P<gt_val>[\d.]+)"  # > 40 or ≥ 40
    r"|(?P<low>[\d.]+)\s*[-–—]\s*(?P<high>[\d.]+)"  # 13.5-17.5
    r")"
    r"\s*$"
)


def _parse_numeric(value: str) -> Decimal | None:
    """Try to extract a numeric value from a result string."""
    if not value:
        return None
    # Strip units, whitespace, and common prefixes
    cleaned = re.sub(r"[^\d.\-]", "", str(value).strip())
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_range(ref_range: str) -> dict | None:
    """Parse a reference range string into low/high bounds.

    Returns dict with 'low' and/or 'high' as Decimal, or None if
    non-numeric / qualitative range.
    """
    if not ref_range:
        return None

    match = RANGE_PATTERN.match(ref_range.strip())
    if not match:
        return None

    result: dict[str, Decimal | bool] = {}

    if match.group("lt"):
        # "< 200" → high = 200
        result["high"] = Decimal(match.group("lt_val"))
        if match.group("lt") == "≤":
            result["high_inclusive"] = True
    elif match.group("gt"):
        # "> 40" → low = 40
        result["low"] = Decimal(match.group("gt_val"))
        if match.group("gt") == "≥":
            result["low_inclusive"] = True
    elif match.group("low") and match.group("high"):
        # "13.5-17.5" → low = 13.5, high = 17.5
        result["low"] = Decimal(match.group("low"))
        result["high"] = Decimal(match.group("high"))
        result["low_inclusive"] = True
        result["high_inclusive"] = True

    return result if result else None


def compute_flag(
    value: str,
    ref_range: str,
    critical_low: str | None = None,
    critical_high: str | None = None,
) -> str | None:
    """Compute a flag for a single result value against its reference range.

    Args:
        value: The result value (e.g. '14.5')
        ref_range: The reference range string (e.g. '13.5-17.5')
        critical_low: Optional critical low threshold (e.g. '7.0')
        critical_high: Optional critical high threshold (e.g. '20.0')

    Returns:
        'N' (normal), 'H' (high), 'L' (low),
        'CRITICAL_H' (critically high), 'CRITICAL_L' (critically low),
        or None if the value/range is non-numeric.
    """
    numeric_val = _parse_numeric(value)
    if numeric_val is None:
        return None

    bounds = _parse_range(ref_range)
    if bounds is None:
        return None

    # Check critical thresholds first
    if critical_high:
        crit_h = _parse_numeric(critical_high)
        if crit_h is not None and numeric_val >= crit_h:
            return "CRITICAL_H"

    if critical_low:
        crit_l = _parse_numeric(critical_low)
        if crit_l is not None and numeric_val <= crit_l:
            return "CRITICAL_L"

    # Check against reference range
    low = bounds.get("low")
    high = bounds.get("high")

    if low is not None:
        low_inclusive = bounds.get("low_inclusive", False)
        if low_inclusive and numeric_val < low:
            return "L"
        if not low_inclusive and numeric_val <= low:
            return "L"

    if high is not None:
        high_inclusive = bounds.get("high_inclusive", False)
        if high_inclusive and numeric_val > high:
            return "H"
        if not high_inclusive and numeric_val >= high:
            return "H"

    return "N"


def flag_report_results(
    result_data: dict,
    template_fields: list[dict] | None = None,
) -> dict:
    """Flag all results in a report's result_data.

    Matches each result field against its reference range
    (from result_data itself or from template_fields) to
    compute H/L/Critical flags.

    Args:
        result_data: Report result data, e.g.
            {"Hemoglobin": {"value": "14.5", "unit": "g/dL", "ref_range": "13.5-17.5"}}
        template_fields: Optional list of template field defs with
            critical_low / critical_high values.

    Returns:
        Updated result_data with 'flag' key added to each field.
    """
    if not result_data:
        return result_data

    # Build lookup from template fields for critical thresholds
    template_lookup = {}
    if template_fields:
        for field in template_fields:
            template_lookup[field.get("name", "")] = field

    flagged_data = {}
    for field_name, field_data in result_data.items():
        if not isinstance(field_data, dict):
            flagged_data[field_name] = field_data
            continue

        value = field_data.get("value", "")
        ref_range = field_data.get("ref_range", "")

        # Get critical thresholds from template if available
        tmpl = template_lookup.get(field_name, {})
        critical_low = tmpl.get("critical_low")
        critical_high = tmpl.get("critical_high")

        flag = compute_flag(value, ref_range, critical_low, critical_high)

        flagged_data[field_name] = {
            **field_data,
            "flag": flag,
        }

    return flagged_data

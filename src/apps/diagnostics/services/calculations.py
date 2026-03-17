"""Auto-calculation service for derived lab result fields.

Supports formulas like:
- A/G Ratio = Albumin / Globulin
- LDL (Friedewald) = Total Cholesterol - HDL - (Triglycerides / 5)
- MCHC = (Hemoglobin / Hematocrit) * 100
- MCH = (Hemoglobin / RBC Count) * 10
- MCV = (Hematocrit / RBC Count) * 10
"""

import logging
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import TypedDict

logger = logging.getLogger(__name__)


class FormulaSpec(TypedDict):
    operands: list[str]
    calc: Callable[[dict[str, Decimal]], Decimal]
    precision: int


# Predefined formulas: maps field name → (formula description, operand names, calc fn)
PREDEFINED_FORMULAS: dict[str, FormulaSpec] = {
    "A/G Ratio": {
        "operands": ["Albumin", "Globulin"],
        "calc": lambda vals: vals["Albumin"] / vals["Globulin"],
        "precision": 2,
    },
    "LDL Cholesterol": {
        "operands": ["Total Cholesterol", "HDL Cholesterol", "Triglycerides"],
        "calc": lambda vals: (
            vals["Total Cholesterol"]
            - vals["HDL Cholesterol"]
            - (vals["Triglycerides"] / Decimal("5"))
        ),
        "precision": 1,
    },
    "VLDL": {
        "operands": ["Triglycerides"],
        "calc": lambda vals: vals["Triglycerides"] / Decimal("5"),
        "precision": 1,
    },
    "MCHC": {
        "operands": ["Hemoglobin", "Hematocrit"],
        "calc": lambda vals: vals["Hemoglobin"] / vals["Hematocrit"] * Decimal("100"),
        "precision": 1,
    },
    "MCH": {
        "operands": ["Hemoglobin", "RBC Count"],
        "calc": lambda vals: vals["Hemoglobin"] / vals["RBC Count"] * Decimal("10"),
        "precision": 1,
    },
    "MCV": {
        "operands": ["Hematocrit", "RBC Count"],
        "calc": lambda vals: vals["Hematocrit"] / vals["RBC Count"] * Decimal("10"),
        "precision": 1,
    },
    "TC/HDL Ratio": {
        "operands": ["Total Cholesterol", "HDL Cholesterol"],
        "calc": lambda vals: vals["Total Cholesterol"] / vals["HDL Cholesterol"],
        "precision": 2,
    },
}


def _safe_decimal(value: str) -> Decimal | None:
    """Convert string value to Decimal, returning None on failure."""
    if not value:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", str(value).strip())
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def auto_calculate(result_data: dict) -> dict:
    """Auto-calculate derived fields in result_data.

    For each field that has a predefined formula, if all operands
    are present with numeric values, compute the result.

    Args:
        result_data: Report result data dict, e.g.
            {"Albumin": {"value": "4.0", ...}, "Globulin": {"value": "2.5", ...}}

    Returns:
        Updated result_data with calculated fields filled in.
    """
    if not result_data:
        return result_data

    for field_name, formula in PREDEFINED_FORMULAS.items():
        # Only calculate if the field exists in result_data
        if field_name not in result_data:
            continue

        # Skip if already has a non-empty value
        existing_value = result_data[field_name].get("value", "")
        if existing_value and existing_value.strip():
            continue

        # Gather operand values
        operand_vals: dict[str, Decimal] = {}
        all_present = True
        for operand in formula["operands"]:
            if operand not in result_data:
                all_present = False
                break
            dec_val = _safe_decimal(result_data[operand].get("value", ""))
            if dec_val is None or dec_val == Decimal("0"):
                all_present = False
                break
            operand_vals[operand] = dec_val

        if not all_present:
            continue

        try:
            calculated = formula["calc"](operand_vals)
            precision = formula["precision"]
            result_data[field_name]["value"] = str(round(calculated, precision))
            result_data[field_name]["auto_calculated"] = True
        except (ZeroDivisionError, InvalidOperation) as e:
            logger.warning(
                "Auto-calc failed for %s: %s",
                field_name,
                str(e),
            )

    return result_data

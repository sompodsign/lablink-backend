"""
Data migration to fill gender/age-specific reference ranges for templates
that currently only have a single universal ref_range.

Only updates tests where medical reference ranges genuinely differ by
gender or age. Qualitative tests (cultures, imaging, etc.) are left as-is.
"""

from django.db import migrations

# Maps test type name -> field name -> gender/age-specific ref ranges.
# Only includes tests where ranges actually differ by gender or age.
GENDER_AGE_RANGES = {
    # ── Lipid Profile ────────────────────────────────────
    "Lipid Profile": {
        "HDL Cholesterol": {
            "ref_range_male": ">40",
            "ref_range_female": ">50",
            "ref_range_child": ">45",
        },
    },
    "HDL Cholesterol": {
        "HDL Cholesterol": {
            "ref_range_male": ">40",
            "ref_range_female": ">50",
            "ref_range_child": ">45",
        },
    },
    # ── Liver Function ───────────────────────────────────
    "Liver Function Test (LFT)": {
        "SGPT / ALT": {
            "ref_range_male": "7-56",
            "ref_range_female": "7-45",
            "ref_range_child": "7-40",
        },
        "SGOT / AST": {
            "ref_range_male": "10-40",
            "ref_range_female": "9-32",
            "ref_range_child": "10-35",
        },
        "Alkaline Phosphatase": {
            "ref_range_male": "44-147",
            "ref_range_female": "44-147",
            "ref_range_child": "150-420",
        },
    },
    "SGPT / ALT": {
        "SGPT / ALT": {
            "ref_range_male": "7-56",
            "ref_range_female": "7-45",
            "ref_range_child": "7-40",
        },
    },
    "SGOT / AST": {
        "SGOT / AST": {
            "ref_range_male": "10-40",
            "ref_range_female": "9-32",
            "ref_range_child": "10-35",
        },
    },
    "Alkaline Phosphatase (ALP)": {
        "Alkaline Phosphatase": {
            "ref_range_male": "44-147",
            "ref_range_female": "44-147",
            "ref_range_child": "150-420",
        },
    },
    # ── Renal ────────────────────────────────────────────
    "Blood Urea / BUN": {
        "Blood Urea": {
            "ref_range_male": "15-40",
            "ref_range_female": "15-40",
            "ref_range_child": "10-36",
        },
        "BUN": {
            "ref_range_male": "7-20",
            "ref_range_female": "7-20",
            "ref_range_child": "5-18",
        },
    },
    # ── Hormones ─────────────────────────────────────────
    "FSH (Follicle Stimulating Hormone)": {
        "FSH": {
            "ref_range_male": "1.5-12.4",
            "ref_range_female": "3.5-12.5 (Follicular)",
        },
    },
    "LH (Luteinizing Hormone)": {
        "LH": {
            "ref_range_male": "1.7-8.6",
            "ref_range_female": "2.4-12.6 (Follicular)",
        },
    },
    "Estradiol (E2)": {
        "Estradiol": {
            "ref_range_male": "10-40",
            "ref_range_female": "12.5-166 (Follicular)",
        },
    },
    "Cortisol (Morning)": {
        "Cortisol (AM)": {
            "ref_range_male": "6.2-19.4",
            "ref_range_female": "6.2-19.4",
            "ref_range_child": "3.0-21.0",
        },
    },
    "Insulin (Fasting)": {
        "Fasting Insulin": {
            "ref_range_male": "2.6-24.9",
            "ref_range_female": "2.6-24.9",
            "ref_range_child": "3.0-20.0",
        },
    },
    # ── Iron / Vitamins ──────────────────────────────────
    "Vitamin D (25-OH)": {
        "Vitamin D (25-OH)": {
            "ref_range_male": "30-100",
            "ref_range_female": "30-100",
            "ref_range_child": "30-100",
        },
    },
    "Vitamin B12": {
        "Vitamin B12": {
            "ref_range_male": "200-900",
            "ref_range_female": "200-900",
            "ref_range_child": "200-900",
        },
    },
    "Folic Acid (Folate)": {
        "Folic Acid": {
            "ref_range_male": "2.7-17.0",
            "ref_range_female": "2.7-17.0",
            "ref_range_child": "5.0-21.0",
        },
    },
    # ── Cardiac Markers ──────────────────────────────────
    "LDH (Lactate Dehydrogenase)": {
        "LDH": {
            "ref_range_male": "140-280",
            "ref_range_female": "140-280",
            "ref_range_child": "170-580",
        },
    },
    # ── Tumor Markers ────────────────────────────────────
    "PSA (Prostate Specific Antigen)": {
        "Total PSA": {
            "ref_range_male": "<4.0",
        },
    },
    "AFP (Alpha-Fetoprotein)": {
        "AFP": {
            "ref_range_male": "<7.0",
            "ref_range_female": "<7.0",
            "ref_range_child": "<30.0",
        },
    },
    # ── Enzymes ──────────────────────────────────────────
    "Amylase (Serum)": {
        "Serum Amylase": {
            "ref_range_male": "28-100",
            "ref_range_female": "28-100",
            "ref_range_child": "25-125",
        },
    },
    "Lipase (Serum)": {
        "Serum Lipase": {
            "ref_range_male": "0-160",
            "ref_range_female": "0-160",
            "ref_range_child": "0-140",
        },
    },
    # ── Immunology ───────────────────────────────────────
    "Serum IgE (Total)": {
        "Total IgE": {
            "ref_range_male": "<100",
            "ref_range_female": "<100",
            "ref_range_child": "<60",
        },
    },
    # ── Thyroid (standalone) ─────────────────────────────
    "TSH (Thyroid Stimulating Hormone)": {
        "TSH": {
            "ref_range_male": "0.27-4.20",
            "ref_range_female": "0.27-4.20",
            "ref_range_child": "0.7-6.4",
        },
    },
    # ── GGT (standalone - already done in 0010 but some
    #    templates may be newly created after that) ───────
    "GGT (Gamma-GT)": {
        "GGT": {
            "ref_range_male": "8-61",
            "ref_range_female": "5-36",
        },
    },
    # ── Urine ────────────────────────────────────────────
    "Urine Routine (R/E)": {
        "Pus Cells": {
            "ref_range_male": "0-5 /HPF",
            "ref_range_female": "0-5 /HPF",
            "ref_range_child": "0-5 /HPF",
        },
        "RBC": {
            "ref_range_male": "0-2 /HPF",
            "ref_range_female": "0-2 /HPF",
            "ref_range_child": "0-2 /HPF",
        },
    },
}


def fill_gender_age_ranges(apps, schema_editor):
    ReportTemplate = apps.get_model("diagnostics", "ReportTemplate")

    updated_count = 0
    for template in ReportTemplate.objects.select_related("test_type").all():
        test_name = template.test_type.name
        field_map = GENDER_AGE_RANGES.get(test_name)
        if not field_map:
            continue

        changed = False
        new_fields = []
        for field in template.fields:
            fname = field.get("name", "")
            overrides = field_map.get(fname)

            if overrides and "ref_range_male" not in field:
                # Keep the universal ref_range if it exists, add gender ones
                updated_field = {**field, **overrides}
                new_fields.append(updated_field)
                changed = True
            else:
                new_fields.append(field)

        if changed:
            template.fields = new_fields
            template.save(update_fields=["fields"])
            updated_count += 1

    print(f"Updated {updated_count} report templates with gender/age ref ranges.")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("diagnostics", "0015_add_created_by_to_report"),
    ]

    operations = [
        migrations.RunPython(fill_gender_age_ranges, noop),
    ]

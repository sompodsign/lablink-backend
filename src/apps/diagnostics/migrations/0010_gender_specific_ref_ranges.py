"""
Data migration to restructure ReportTemplate fields from single ref_range
to gender/age-specific ref ranges: ref_range_male, ref_range_female, ref_range_child.
This provides accurate reference values based on patient demographics.
"""
from django.db import migrations


# Maps test type name -> list of fields with gender/age-specific ref ranges
# Only includes tests where ranges actually differ by gender or age.
# Tests with universal ranges keep a single ref_range (no _male/_female suffix).
GENDER_SPECIFIC_FIELDS = {
    "CBC (Complete Blood Count)": [
        {"name": "Hemoglobin (Hb)", "unit": "g/dL", "ref_range_male": "13.5-17.5", "ref_range_female": "12.0-16.0", "ref_range_child": "11.0-14.0"},
        {"name": "RBC Count", "unit": "million/cumm", "ref_range_male": "4.5-5.9", "ref_range_female": "3.8-5.2", "ref_range_child": "3.9-5.3"},
        {"name": "Total WBC Count", "unit": "/cumm", "ref_range": "4000-11000"},
        {"name": "Neutrophils", "unit": "%", "ref_range": "40-70"},
        {"name": "Lymphocytes", "unit": "%", "ref_range": "20-40"},
        {"name": "Monocytes", "unit": "%", "ref_range": "2-8"},
        {"name": "Eosinophils", "unit": "%", "ref_range": "1-6"},
        {"name": "Basophils", "unit": "%", "ref_range": "0-1"},
        {"name": "Platelet Count", "unit": "/cumm", "ref_range": "150000-450000"},
        {"name": "Hematocrit (HCT/PCV)", "unit": "%", "ref_range_male": "38-50", "ref_range_female": "36-44", "ref_range_child": "33-43"},
        {"name": "MCV", "unit": "fL", "ref_range": "80-100"},
        {"name": "MCH", "unit": "pg", "ref_range": "27-33"},
        {"name": "MCHC", "unit": "g/dL", "ref_range": "32-36"},
        {"name": "RDW", "unit": "%", "ref_range": "11.5-14.5"},
    ],
    "ESR (Erythrocyte Sedimentation Rate)": [
        {"name": "ESR (Westergren)", "unit": "mm/1st hr", "ref_range_male": "0-15", "ref_range_female": "0-20", "ref_range_child": "0-10"},
    ],
    "Hemoglobin (Hb)": [
        {"name": "Hemoglobin", "unit": "g/dL", "ref_range_male": "13.5-17.5", "ref_range_female": "12.0-16.0", "ref_range_child": "11.0-14.0"},
    ],
    "Renal Function Test (RFT)": [
        {"name": "Serum Creatinine", "unit": "mg/dL", "ref_range_male": "0.7-1.3", "ref_range_female": "0.6-1.1", "ref_range_child": "0.3-0.7"},
        {"name": "Blood Urea", "unit": "mg/dL", "ref_range": "15-40"},
        {"name": "BUN", "unit": "mg/dL", "ref_range": "7-20"},
        {"name": "Serum Uric Acid", "unit": "mg/dL", "ref_range_male": "3.4-7.0", "ref_range_female": "2.4-6.0", "ref_range_child": "2.0-5.5"},
        {"name": "Sodium (Na+)", "unit": "mmol/L", "ref_range": "136-145"},
        {"name": "Potassium (K+)", "unit": "mmol/L", "ref_range": "3.5-5.1"},
        {"name": "Chloride (Cl-)", "unit": "mmol/L", "ref_range": "98-106"},
    ],
    "Serum Creatinine": [
        {"name": "Serum Creatinine", "unit": "mg/dL", "ref_range_male": "0.7-1.3", "ref_range_female": "0.6-1.1", "ref_range_child": "0.3-0.7"},
    ],
    "Serum Uric Acid": [
        {"name": "Serum Uric Acid", "unit": "mg/dL", "ref_range_male": "3.4-7.0", "ref_range_female": "2.4-6.0", "ref_range_child": "2.0-5.5"},
    ],
    "Serum Iron": [
        {"name": "Serum Iron", "unit": "μg/dL", "ref_range_male": "65-176", "ref_range_female": "50-170", "ref_range_child": "50-120"},
    ],
    "Serum Ferritin": [
        {"name": "Serum Ferritin", "unit": "ng/mL", "ref_range_male": "12-300", "ref_range_female": "12-150", "ref_range_child": "7-140"},
    ],
    "GGT (Gamma-GT)": [
        {"name": "GGT", "unit": "U/L", "ref_range_male": "8-61", "ref_range_female": "5-36"},
    ],
    "HDL Cholesterol": [
        {"name": "HDL Cholesterol", "unit": "mg/dL", "ref_range_male": ">40", "ref_range_female": ">50"},
    ],
    "Thyroid Profile (T3, T4, TSH)": [
        {"name": "T3 (Total)", "unit": "ng/dL", "ref_range": "80-200"},
        {"name": "T4 (Total)", "unit": "μg/dL", "ref_range": "5.1-14.1"},
        {"name": "TSH", "unit": "μIU/mL", "ref_range": "0.27-4.20"},
    ],
    "Testosterone": [
        {"name": "Testosterone", "unit": "ng/dL", "ref_range_male": "270-1070", "ref_range_female": "15-70"},
    ],
    "Prolactin": [
        {"name": "Prolactin", "unit": "ng/mL", "ref_range_male": "2-18", "ref_range_female": "2-29"},
    ],
    "Growth Hormone (GH)": [
        {"name": "Growth Hormone", "unit": "ng/mL", "ref_range_male": "0-3", "ref_range_female": "0-8"},
    ],
    "CPK (Creatine Phosphokinase)": [
        {"name": "CPK (Total)", "unit": "U/L", "ref_range_male": "39-308", "ref_range_female": "26-192"},
    ],
    "Semen Analysis": [
        {"name": "Volume", "unit": "mL", "ref_range": "1.5-5.0"},
        {"name": "Color", "unit": "", "ref_range": "Grayish White"},
        {"name": "pH", "unit": "", "ref_range": "7.2-8.0"},
        {"name": "Liquefaction Time", "unit": "min", "ref_range": "<30"},
        {"name": "Sperm Count", "unit": "million/mL", "ref_range": ">15"},
        {"name": "Total Motility", "unit": "%", "ref_range": ">40"},
        {"name": "Progressive Motility", "unit": "%", "ref_range": ">32"},
        {"name": "Normal Morphology", "unit": "%", "ref_range": ">4"},
    ],
}


def update_templates(apps, schema_editor):
    ReportTemplate = apps.get_model('diagnostics', 'ReportTemplate')

    for template in ReportTemplate.objects.select_related('test_type').all():
        test_name = template.test_type.name
        new_fields = GENDER_SPECIFIC_FIELDS.get(test_name)

        if new_fields:
            # Use our pre-defined gender-specific fields
            template.fields = new_fields
            template.save(update_fields=['fields'])
        else:
            # For all other templates, ensure fields have the standard format
            # (they already have ref_range which works as universal)
            pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('diagnostics', '0009_add_soft_delete_to_report'),
    ]

    operations = [
        migrations.RunPython(update_templates, noop),
    ]

"""Default report template field definitions for Bangladeshi diagnostic tests.

This module is used by:
- The seed migration (0008_seed_report_templates) to populate initial data
- The post_save signal on DiagnosticCenter to auto-create templates for new tenants
"""

# ────────────────────────────────────────────────────────────────────
# Template field definitions keyed by TestType name
# ────────────────────────────────────────────────────────────────────
TEMPLATE_FIELDS = {
    # ── Hematology ──────────────────────────────────────────────
    "CBC (Complete Blood Count)": [
        {
            "name": "Hemoglobin (Hb)",
            "unit": "g/dL",
            "ref_range": "M: 13.5-17.5 / F: 12.0-16.0",
        },
        {
            "name": "RBC Count",
            "unit": "million/cumm",
            "ref_range": "M: 4.5-5.9 / F: 3.8-5.2",
        },
        {"name": "Total WBC Count", "unit": "/cumm", "ref_range": "4000-11000"},
        {"name": "Neutrophils", "unit": "%", "ref_range": "40-70"},
        {"name": "Lymphocytes", "unit": "%", "ref_range": "20-40"},
        {"name": "Monocytes", "unit": "%", "ref_range": "2-8"},
        {"name": "Eosinophils", "unit": "%", "ref_range": "1-6"},
        {"name": "Basophils", "unit": "%", "ref_range": "0-1"},
        {"name": "Platelet Count", "unit": "/cumm", "ref_range": "150000-450000"},
        {
            "name": "Hematocrit (HCT/PCV)",
            "unit": "%",
            "ref_range": "M: 38-50 / F: 36-44",
        },
        {"name": "MCV", "unit": "fL", "ref_range": "80-100"},
        {"name": "MCH", "unit": "pg", "ref_range": "27-33"},
        {"name": "MCHC", "unit": "g/dL", "ref_range": "32-36"},
        {"name": "RDW", "unit": "%", "ref_range": "11.5-14.5"},
    ],
    "ESR (Erythrocyte Sedimentation Rate)": [
        {
            "name": "ESR (Westergren)",
            "unit": "mm/1st hr",
            "ref_range": "M: 0-15 / F: 0-20",
        },
    ],
    "Blood Group & Rh Typing": [
        {"name": "ABO Group", "unit": "", "ref_range": "A / B / AB / O"},
        {"name": "Rh Factor", "unit": "", "ref_range": "Positive / Negative"},
    ],
    "Hemoglobin (Hb)": [
        {
            "name": "Hemoglobin",
            "unit": "g/dL",
            "ref_range": "M: 13.5-17.5 / F: 12.0-16.0",
        },
    ],
    "Peripheral Blood Film (PBF)": [
        {"name": "RBC Morphology", "unit": "", "ref_range": "Normocytic Normochromic"},
        {"name": "WBC Morphology", "unit": "", "ref_range": "Normal"},
        {"name": "Platelet Morphology", "unit": "", "ref_range": "Adequate"},
        {"name": "Parasites", "unit": "", "ref_range": "Not Found"},
    ],
    "Platelet Count": [
        {"name": "Platelet Count", "unit": "/cumm", "ref_range": "150000-450000"},
    ],
    "Reticulocyte Count": [
        {"name": "Reticulocyte Count", "unit": "%", "ref_range": "0.5-2.5"},
    ],
    "Bleeding Time (BT)": [
        {"name": "Bleeding Time", "unit": "min", "ref_range": "1-7"},
    ],
    "Clotting Time (CT)": [
        {"name": "Clotting Time", "unit": "min", "ref_range": "4-10"},
    ],
    "PT (Prothrombin Time)": [
        {"name": "PT (Patient)", "unit": "sec", "ref_range": "11-13.5"},
        {"name": "PT (Control)", "unit": "sec", "ref_range": "11-13.5"},
        {"name": "INR", "unit": "", "ref_range": "0.8-1.2"},
    ],
    "APTT (Activated Partial Thromboplastin Time)": [
        {"name": "APTT (Patient)", "unit": "sec", "ref_range": "25-35"},
        {"name": "APTT (Control)", "unit": "sec", "ref_range": "25-35"},
    ],
    "D-Dimer": [
        {"name": "D-Dimer", "unit": "ng/mL", "ref_range": "<500"},
    ],
    "Coagulation Profile": [
        {"name": "PT", "unit": "sec", "ref_range": "11-13.5"},
        {"name": "INR", "unit": "", "ref_range": "0.8-1.2"},
        {"name": "APTT", "unit": "sec", "ref_range": "25-35"},
        {"name": "Bleeding Time", "unit": "min", "ref_range": "1-7"},
        {"name": "Clotting Time", "unit": "min", "ref_range": "4-10"},
    ],
    "Total WBC Count": [
        {"name": "Total WBC Count", "unit": "/cumm", "ref_range": "4000-11000"},
    ],
    "Differential Count (DC)": [
        {"name": "Neutrophils", "unit": "%", "ref_range": "40-70"},
        {"name": "Lymphocytes", "unit": "%", "ref_range": "20-40"},
        {"name": "Monocytes", "unit": "%", "ref_range": "2-8"},
        {"name": "Eosinophils", "unit": "%", "ref_range": "1-6"},
        {"name": "Basophils", "unit": "%", "ref_range": "0-1"},
    ],
    # ── Biochemistry: Sugar ─────────────────────────────────────
    "Blood Sugar (Fasting)": [
        {"name": "Fasting Blood Sugar", "unit": "mmol/L", "ref_range": "3.9-6.1"},
    ],
    "Blood Sugar (Random)": [
        {"name": "Random Blood Sugar", "unit": "mmol/L", "ref_range": "<7.8"},
    ],
    "Blood Sugar (2hr ABF / PP)": [
        {"name": "Blood Sugar (2hr PP)", "unit": "mmol/L", "ref_range": "<7.8"},
    ],
    "HbA1c (Glycated Hemoglobin)": [
        {
            "name": "HbA1c",
            "unit": "%",
            "ref_range": "4.0-5.6 (Normal) / 5.7-6.4 (Pre-DM)",
        },
    ],
    "OGTT (Oral Glucose Tolerance Test)": [
        {"name": "Fasting", "unit": "mmol/L", "ref_range": "<6.1"},
        {"name": "1 Hour", "unit": "mmol/L", "ref_range": "<10.0"},
        {"name": "2 Hour", "unit": "mmol/L", "ref_range": "<7.8"},
    ],
    # ── Biochemistry: Lipid ─────────────────────────────────────
    "Lipid Profile": [
        {"name": "Total Cholesterol", "unit": "mg/dL", "ref_range": "<200"},
        {"name": "Triglycerides", "unit": "mg/dL", "ref_range": "<150"},
        {"name": "HDL Cholesterol", "unit": "mg/dL", "ref_range": ">40"},
        {"name": "LDL Cholesterol", "unit": "mg/dL", "ref_range": "<100"},
        {"name": "VLDL", "unit": "mg/dL", "ref_range": "5-40"},
        {"name": "TC/HDL Ratio", "unit": "", "ref_range": "<5.0"},
    ],
    "Total Cholesterol": [
        {"name": "Total Cholesterol", "unit": "mg/dL", "ref_range": "<200"},
    ],
    "Triglycerides (TG)": [
        {"name": "Triglycerides", "unit": "mg/dL", "ref_range": "<150"},
    ],
    "HDL Cholesterol": [
        {"name": "HDL Cholesterol", "unit": "mg/dL", "ref_range": "M: >40 / F: >50"},
    ],
    "LDL Cholesterol": [
        {"name": "LDL Cholesterol", "unit": "mg/dL", "ref_range": "<100"},
    ],
    # ── Biochemistry: Liver ─────────────────────────────────────
    "Liver Function Test (LFT)": [
        {"name": "Bilirubin (Total)", "unit": "mg/dL", "ref_range": "0.1-1.2"},
        {"name": "Bilirubin (Direct)", "unit": "mg/dL", "ref_range": "0.0-0.3"},
        {"name": "SGPT / ALT", "unit": "U/L", "ref_range": "7-56"},
        {"name": "SGOT / AST", "unit": "U/L", "ref_range": "10-40"},
        {"name": "Alkaline Phosphatase", "unit": "U/L", "ref_range": "44-147"},
        {"name": "Total Protein", "unit": "g/dL", "ref_range": "6.0-8.3"},
        {"name": "Albumin", "unit": "g/dL", "ref_range": "3.5-5.5"},
        {"name": "Globulin", "unit": "g/dL", "ref_range": "2.0-3.5"},
        {"name": "A/G Ratio", "unit": "", "ref_range": "1.0-2.5"},
    ],
    "SGPT / ALT": [
        {"name": "SGPT / ALT", "unit": "U/L", "ref_range": "7-56"},
    ],
    "SGOT / AST": [
        {"name": "SGOT / AST", "unit": "U/L", "ref_range": "10-40"},
    ],
    "Bilirubin (Total & Direct)": [
        {"name": "Bilirubin (Total)", "unit": "mg/dL", "ref_range": "0.1-1.2"},
        {"name": "Bilirubin (Direct)", "unit": "mg/dL", "ref_range": "0.0-0.3"},
        {"name": "Bilirubin (Indirect)", "unit": "mg/dL", "ref_range": "0.1-0.9"},
    ],
    "Alkaline Phosphatase (ALP)": [
        {"name": "Alkaline Phosphatase", "unit": "U/L", "ref_range": "44-147"},
    ],
    "GGT (Gamma-GT)": [
        {"name": "GGT", "unit": "U/L", "ref_range": "M: 8-61 / F: 5-36"},
    ],
    "Total Protein": [
        {"name": "Total Protein", "unit": "g/dL", "ref_range": "6.0-8.3"},
    ],
    "Serum Albumin": [
        {"name": "Serum Albumin", "unit": "g/dL", "ref_range": "3.5-5.5"},
    ],
    # ── Biochemistry: Renal ─────────────────────────────────────
    "Renal Function Test (RFT)": [
        {
            "name": "Serum Creatinine",
            "unit": "mg/dL",
            "ref_range": "M: 0.7-1.3 / F: 0.6-1.1",
        },
        {"name": "Blood Urea", "unit": "mg/dL", "ref_range": "15-40"},
        {"name": "BUN", "unit": "mg/dL", "ref_range": "7-20"},
        {
            "name": "Serum Uric Acid",
            "unit": "mg/dL",
            "ref_range": "M: 3.4-7.0 / F: 2.4-6.0",
        },
        {"name": "Sodium (Na+)", "unit": "mmol/L", "ref_range": "136-145"},
        {"name": "Potassium (K+)", "unit": "mmol/L", "ref_range": "3.5-5.1"},
        {"name": "Chloride (Cl-)", "unit": "mmol/L", "ref_range": "98-106"},
    ],
    "Serum Creatinine": [
        {
            "name": "Serum Creatinine",
            "unit": "mg/dL",
            "ref_range": "M: 0.7-1.3 / F: 0.6-1.1",
        },
    ],
    "Blood Urea / BUN": [
        {"name": "Blood Urea", "unit": "mg/dL", "ref_range": "15-40"},
        {"name": "BUN", "unit": "mg/dL", "ref_range": "7-20"},
    ],
    "Serum Uric Acid": [
        {
            "name": "Serum Uric Acid",
            "unit": "mg/dL",
            "ref_range": "M: 3.4-7.0 / F: 2.4-6.0",
        },
    ],
    "Serum Electrolytes": [
        {"name": "Sodium (Na+)", "unit": "mmol/L", "ref_range": "136-145"},
        {"name": "Potassium (K+)", "unit": "mmol/L", "ref_range": "3.5-5.1"},
        {"name": "Chloride (Cl-)", "unit": "mmol/L", "ref_range": "98-106"},
        {"name": "Bicarbonate (HCO3-)", "unit": "mmol/L", "ref_range": "22-29"},
    ],
    "Serum Calcium": [
        {"name": "Serum Calcium", "unit": "mg/dL", "ref_range": "8.5-10.5"},
    ],
    "Serum Phosphorus": [
        {"name": "Serum Phosphorus", "unit": "mg/dL", "ref_range": "2.5-4.5"},
    ],
    "Serum Magnesium": [
        {"name": "Serum Magnesium", "unit": "mg/dL", "ref_range": "1.7-2.2"},
    ],
    # ── Iron Studies ────────────────────────────────────────────
    "Serum Iron": [
        {"name": "Serum Iron", "unit": "μg/dL", "ref_range": "M: 65-176 / F: 50-170"},
    ],
    "TIBC (Total Iron Binding Capacity)": [
        {"name": "TIBC", "unit": "μg/dL", "ref_range": "250-370"},
    ],
    "Serum Ferritin": [
        {
            "name": "Serum Ferritin",
            "unit": "ng/mL",
            "ref_range": "M: 12-300 / F: 12-150",
        },
    ],
    # ── Inflammatory Markers ────────────────────────────────────
    "CRP (C-Reactive Protein)": [
        {"name": "CRP", "unit": "mg/L", "ref_range": "<6"},
    ],
    "hs-CRP (High Sensitivity CRP)": [
        {
            "name": "hs-CRP",
            "unit": "mg/L",
            "ref_range": "<1.0 (Low Risk) / 1.0-3.0 (Moderate)",
        },
    ],
    "ASO Titre": [
        {"name": "ASO Titre", "unit": "IU/mL", "ref_range": "<200"},
    ],
    "RA Factor (Rheumatoid Factor)": [
        {"name": "RA Factor", "unit": "IU/mL", "ref_range": "<14"},
    ],
    "ANA (Anti-Nuclear Antibody)": [
        {"name": "ANA", "unit": "", "ref_range": "Negative"},
    ],
    # ── Thyroid ─────────────────────────────────────────────────
    "Thyroid Profile (T3, T4, TSH)": [
        {"name": "T3 (Total)", "unit": "ng/dL", "ref_range": "80-200"},
        {"name": "T4 (Total)", "unit": "μg/dL", "ref_range": "5.1-14.1"},
        {"name": "TSH", "unit": "μIU/mL", "ref_range": "0.27-4.20"},
    ],
    "TSH (Thyroid Stimulating Hormone)": [
        {"name": "TSH", "unit": "μIU/mL", "ref_range": "0.27-4.20"},
    ],
    "Free T3 (FT3)": [
        {"name": "Free T3", "unit": "pg/mL", "ref_range": "2.0-4.4"},
    ],
    "Free T4 (FT4)": [
        {"name": "Free T4", "unit": "ng/dL", "ref_range": "0.93-1.70"},
    ],
    "Total T3": [
        {"name": "Total T3", "unit": "ng/dL", "ref_range": "80-200"},
    ],
    "Total T4": [
        {"name": "Total T4", "unit": "μg/dL", "ref_range": "5.1-14.1"},
    ],
    # ── Hormones ────────────────────────────────────────────────
    "Testosterone": [
        {
            "name": "Testosterone",
            "unit": "ng/dL",
            "ref_range": "M: 270-1070 / F: 15-70",
        },
    ],
    "Prolactin": [
        {"name": "Prolactin", "unit": "ng/mL", "ref_range": "M: 2-18 / F: 2-29"},
    ],
    "FSH (Follicle Stimulating Hormone)": [
        {"name": "FSH", "unit": "mIU/mL", "ref_range": "Phase dependent"},
    ],
    "LH (Luteinizing Hormone)": [
        {"name": "LH", "unit": "mIU/mL", "ref_range": "Phase dependent"},
    ],
    "Estradiol (E2)": [
        {"name": "Estradiol", "unit": "pg/mL", "ref_range": "Phase dependent"},
    ],
    "Progesterone": [
        {"name": "Progesterone", "unit": "ng/mL", "ref_range": "Phase dependent"},
    ],
    "Beta hCG (Pregnancy Test - Quantitative)": [
        {"name": "Beta hCG", "unit": "mIU/mL", "ref_range": "<5 (Non-pregnant)"},
    ],
    "Cortisol (Morning)": [
        {"name": "Cortisol (AM)", "unit": "μg/dL", "ref_range": "6.2-19.4"},
    ],
    "Insulin (Fasting)": [
        {"name": "Fasting Insulin", "unit": "μIU/mL", "ref_range": "2.6-24.9"},
    ],
    "Growth Hormone (GH)": [
        {"name": "Growth Hormone", "unit": "ng/mL", "ref_range": "M: 0-3 / F: 0-8"},
    ],
    "PTH (Parathyroid Hormone)": [
        {"name": "PTH (Intact)", "unit": "pg/mL", "ref_range": "15-65"},
    ],
    # ── Vitamins ────────────────────────────────────────────────
    "Vitamin D (25-OH)": [
        {
            "name": "Vitamin D (25-OH)",
            "unit": "ng/mL",
            "ref_range": "30-100 (Sufficient)",
        },
    ],
    "Vitamin B12": [
        {"name": "Vitamin B12", "unit": "pg/mL", "ref_range": "200-900"},
    ],
    "Folic Acid (Folate)": [
        {"name": "Folic Acid", "unit": "ng/mL", "ref_range": "3.1-17.5"},
    ],
    # ── Serology / Infectious ───────────────────────────────────
    "HBsAg (Hepatitis B Surface Antigen)": [
        {"name": "HBsAg", "unit": "", "ref_range": "Negative"},
    ],
    "Anti-HCV (Hepatitis C Antibody)": [
        {"name": "Anti-HCV", "unit": "", "ref_range": "Negative"},
    ],
    "HIV 1 & 2 (Antibody)": [
        {"name": "HIV 1 & 2", "unit": "", "ref_range": "Non-Reactive"},
    ],
    "VDRL / RPR": [
        {"name": "VDRL", "unit": "", "ref_range": "Non-Reactive"},
    ],
    "Widal Test": [
        {"name": "S. Typhi O", "unit": "", "ref_range": "<1:80"},
        {"name": "S. Typhi H", "unit": "", "ref_range": "<1:80"},
        {"name": "S. Paratyphi AH", "unit": "", "ref_range": "<1:80"},
        {"name": "S. Paratyphi BH", "unit": "", "ref_range": "<1:80"},
    ],
    "Typhidot (IgG/IgM)": [
        {"name": "IgG", "unit": "", "ref_range": "Negative"},
        {"name": "IgM", "unit": "", "ref_range": "Negative"},
    ],
    "Dengue NS1 Antigen": [
        {"name": "Dengue NS1 Ag", "unit": "", "ref_range": "Negative"},
    ],
    "Dengue IgG / IgM": [
        {"name": "Dengue IgG", "unit": "", "ref_range": "Negative"},
        {"name": "Dengue IgM", "unit": "", "ref_range": "Negative"},
    ],
    "Malaria (ICT/Rapid)": [
        {"name": "P. falciparum", "unit": "", "ref_range": "Not Detected"},
        {"name": "P. vivax", "unit": "", "ref_range": "Not Detected"},
    ],
    "Malaria Parasite (MP) - Smear": [
        {"name": "MP (Thick Film)", "unit": "", "ref_range": "Not Found"},
        {"name": "MP (Thin Film)", "unit": "", "ref_range": "Not Found"},
    ],
    # ── Cardiac Markers ─────────────────────────────────────────
    "Troponin I": [
        {"name": "Troponin I", "unit": "ng/mL", "ref_range": "<0.04"},
    ],
    "Pro-BNP / NT-proBNP": [
        {"name": "NT-proBNP", "unit": "pg/mL", "ref_range": "<125 (<75 yrs)"},
    ],
    "Procalcitonin": [
        {"name": "Procalcitonin", "unit": "ng/mL", "ref_range": "<0.05"},
    ],
    # ── Urine ───────────────────────────────────────────────────
    "Urine Routine (R/E)": [
        {"name": "Color", "unit": "", "ref_range": "Pale Yellow"},
        {"name": "Appearance", "unit": "", "ref_range": "Clear"},
        {"name": "pH", "unit": "", "ref_range": "4.6-8.0"},
        {"name": "Specific Gravity", "unit": "", "ref_range": "1.005-1.030"},
        {"name": "Protein", "unit": "", "ref_range": "Nil"},
        {"name": "Sugar", "unit": "", "ref_range": "Nil"},
        {"name": "Ketone", "unit": "", "ref_range": "Nil"},
        {"name": "Blood", "unit": "", "ref_range": "Nil"},
        {"name": "Bilirubin", "unit": "", "ref_range": "Nil"},
        {"name": "Pus Cells", "unit": "/HPF", "ref_range": "0-5"},
        {"name": "RBC", "unit": "/HPF", "ref_range": "0-2"},
        {"name": "Epithelial Cells", "unit": "/HPF", "ref_range": "Few"},
        {"name": "Casts", "unit": "", "ref_range": "Nil"},
        {"name": "Crystals", "unit": "", "ref_range": "Nil"},
    ],
    "Urine Culture & Sensitivity": [
        {"name": "Organism", "unit": "", "ref_range": "No Growth"},
        {"name": "Colony Count", "unit": "CFU/mL", "ref_range": "<10000"},
    ],
    "Urine Microalbumin (ACR)": [
        {"name": "Microalbumin", "unit": "mg/L", "ref_range": "<20"},
        {"name": "ACR", "unit": "mg/g", "ref_range": "<30"},
    ],
    "24-hour Urine Protein": [
        {"name": "24hr Urine Protein", "unit": "mg/24hr", "ref_range": "<150"},
    ],
    "Urine for Pregnancy Test": [
        {"name": "Pregnancy Test (Urine)", "unit": "", "ref_range": "Negative"},
    ],
    "Urine Sugar (Benedict)": [
        {"name": "Urine Sugar (Benedict)", "unit": "", "ref_range": "Nil"},
    ],
    # ── Stool ───────────────────────────────────────────────────
    "Stool Routine (R/E)": [
        {"name": "Color", "unit": "", "ref_range": "Brown"},
        {"name": "Consistency", "unit": "", "ref_range": "Formed"},
        {"name": "Mucus", "unit": "", "ref_range": "Nil"},
        {"name": "Blood", "unit": "", "ref_range": "Nil"},
        {"name": "Pus Cells", "unit": "/HPF", "ref_range": "0-5"},
        {"name": "RBC", "unit": "/HPF", "ref_range": "Nil"},
        {"name": "Ova/Parasite", "unit": "", "ref_range": "Not Found"},
    ],
    "Stool Culture & Sensitivity": [
        {"name": "Organism", "unit": "", "ref_range": "No Growth"},
    ],
    "Stool Occult Blood (OBT)": [
        {"name": "Occult Blood", "unit": "", "ref_range": "Negative"},
    ],
    "Stool for Reducing Substance": [
        {"name": "Reducing Substance", "unit": "", "ref_range": "Negative"},
    ],
    # ── Culture & Sensitivity ───────────────────────────────────
    "Blood Culture & Sensitivity": [
        {"name": "Organism", "unit": "", "ref_range": "No Growth (after 48-72 hrs)"},
    ],
    "Sputum Culture & Sensitivity": [
        {"name": "Organism", "unit": "", "ref_range": "Normal Flora"},
    ],
    "Sputum for AFB (Acid-Fast Bacilli)": [
        {"name": "AFB (ZN Stain)", "unit": "", "ref_range": "Not Found"},
    ],
    "Wound / Pus Culture & Sensitivity": [
        {"name": "Organism", "unit": "", "ref_range": "No Growth"},
    ],
    "Throat Swab Culture": [
        {"name": "Organism", "unit": "", "ref_range": "Normal Flora"},
    ],
    "Gram Stain": [
        {"name": "Gram Stain Result", "unit": "", "ref_range": "No Organism Seen"},
    ],
    "KOH Mount (Fungal Smear)": [
        {"name": "KOH Mount", "unit": "", "ref_range": "No Fungal Element Seen"},
    ],
    # ── Tumor Markers ───────────────────────────────────────────
    "AFP (Alpha-Fetoprotein)": [
        {"name": "AFP", "unit": "ng/mL", "ref_range": "<7.0"},
    ],
    "PSA (Prostate Specific Antigen)": [
        {"name": "Total PSA", "unit": "ng/mL", "ref_range": "<4.0"},
    ],
    "CEA (Carcinoembryonic Antigen)": [
        {"name": "CEA", "unit": "ng/mL", "ref_range": "<5.0"},
    ],
    "CA-125": [
        {"name": "CA-125", "unit": "U/mL", "ref_range": "<35"},
    ],
    "CA 19-9": [
        {"name": "CA 19-9", "unit": "U/mL", "ref_range": "<37"},
    ],
    "CA 15-3": [
        {"name": "CA 15-3", "unit": "U/mL", "ref_range": "<31.3"},
    ],
    # ── Enzymes ─────────────────────────────────────────────────
    "Amylase (Serum)": [
        {"name": "Serum Amylase", "unit": "U/L", "ref_range": "28-100"},
    ],
    "Lipase (Serum)": [
        {"name": "Serum Lipase", "unit": "U/L", "ref_range": "0-160"},
    ],
    "LDH (Lactate Dehydrogenase)": [
        {"name": "LDH", "unit": "U/L", "ref_range": "140-280"},
    ],
    "CPK (Creatine Phosphokinase)": [
        {"name": "CPK (Total)", "unit": "U/L", "ref_range": "M: 39-308 / F: 26-192"},
    ],
    "CPK-MB": [
        {"name": "CPK-MB", "unit": "U/L", "ref_range": "<25"},
    ],
    # ── Body Fluid Analysis ─────────────────────────────────────
    "CSF Analysis": [
        {"name": "Appearance", "unit": "", "ref_range": "Clear, Colorless"},
        {"name": "Protein", "unit": "mg/dL", "ref_range": "15-45"},
        {"name": "Sugar", "unit": "mg/dL", "ref_range": "40-70"},
        {"name": "Chloride", "unit": "mmol/L", "ref_range": "118-132"},
        {"name": "Cell Count (Total)", "unit": "/cumm", "ref_range": "0-5"},
        {"name": "Cell Type", "unit": "", "ref_range": "Lymphocytes"},
    ],
    "Pleural Fluid Analysis": [
        {"name": "Appearance", "unit": "", "ref_range": "Clear"},
        {"name": "Protein", "unit": "g/dL", "ref_range": "Transudate <3 / Exudate >3"},
        {"name": "Sugar", "unit": "mg/dL", "ref_range": "~Serum level"},
        {"name": "Cell Count", "unit": "/cumm", "ref_range": "<1000"},
        {"name": "LDH", "unit": "U/L", "ref_range": ""},
    ],
    "Peritoneal (Ascitic) Fluid Analysis": [
        {"name": "Appearance", "unit": "", "ref_range": "Clear, Straw colored"},
        {"name": "Protein", "unit": "g/dL", "ref_range": "Transudate <2.5"},
        {"name": "Cell Count", "unit": "/cumm", "ref_range": "<250"},
        {"name": "SAAG", "unit": "g/dL", "ref_range": ">1.1 (Portal HTN)"},
    ],
    "Synovial Fluid Analysis": [
        {"name": "Appearance", "unit": "", "ref_range": "Clear, Pale Yellow"},
        {"name": "Viscosity", "unit": "", "ref_range": "High"},
        {"name": "WBC Count", "unit": "/cumm", "ref_range": "<200"},
        {"name": "Crystals", "unit": "", "ref_range": "None"},
    ],
    # ── Semen ───────────────────────────────────────────────────
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
    # ── Allergy ─────────────────────────────────────────────────
    "Serum IgE (Total)": [
        {"name": "Total IgE", "unit": "IU/mL", "ref_range": "<100"},
    ],
    "Specific IgE Panel": [
        {"name": "Specific IgE", "unit": "kU/L", "ref_range": "<0.35 (Class 0)"},
    ],
    # ── Imaging / Other ─────────────────────────────────────────
    "ECG (Electrocardiogram)": [
        {"name": "Heart Rate", "unit": "bpm", "ref_range": "60-100"},
        {"name": "Rhythm", "unit": "", "ref_range": "Regular Sinus"},
        {"name": "Axis", "unit": "", "ref_range": "Normal"},
        {"name": "Interpretation", "unit": "", "ref_range": "Normal ECG"},
    ],
    "X-Ray Chest (PA View)": [
        {"name": "Findings", "unit": "", "ref_range": "Normal"},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
    "X-Ray (Other)": [
        {"name": "Findings", "unit": "", "ref_range": ""},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
    "Ultrasound - Whole Abdomen": [
        {"name": "Liver", "unit": "", "ref_range": "Normal"},
        {"name": "Gallbladder", "unit": "", "ref_range": "Normal"},
        {"name": "Spleen", "unit": "", "ref_range": "Normal"},
        {"name": "Kidneys (R/L)", "unit": "", "ref_range": "Normal"},
        {"name": "Pancreas", "unit": "", "ref_range": "Normal"},
        {"name": "Urinary Bladder", "unit": "", "ref_range": "Normal"},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
    "Ultrasound - Lower Abdomen": [
        {"name": "Urinary Bladder", "unit": "", "ref_range": "Normal"},
        {"name": "Prostate / Uterus", "unit": "", "ref_range": "Normal"},
        {"name": "Adnexa", "unit": "", "ref_range": "Normal"},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
    "Ultrasound - Pregnancy (Obstetric)": [
        {"name": "Gestational Age", "unit": "weeks", "ref_range": ""},
        {"name": "Fetal Heart Rate", "unit": "bpm", "ref_range": "120-160"},
        {"name": "BPD", "unit": "mm", "ref_range": ""},
        {"name": "FL", "unit": "mm", "ref_range": ""},
        {"name": "AC", "unit": "mm", "ref_range": ""},
        {"name": "EFW", "unit": "gm", "ref_range": ""},
        {"name": "Placenta", "unit": "", "ref_range": ""},
        {"name": "Amniotic Fluid (AFI)", "unit": "cm", "ref_range": "5-25"},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
    "Color Doppler (Vascular)": [
        {"name": "Findings", "unit": "", "ref_range": "Normal flow pattern"},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
    "Echocardiography (Echo)": [
        {"name": "LV EF", "unit": "%", "ref_range": "55-70"},
        {"name": "LV Function", "unit": "", "ref_range": "Normal"},
        {"name": "Valve Status", "unit": "", "ref_range": "Normal"},
        {"name": "Wall Motion", "unit": "", "ref_range": "Normal"},
        {"name": "Pericardium", "unit": "", "ref_range": "Normal"},
        {"name": "Impression", "unit": "", "ref_range": ""},
    ],
}

"""
Seed all common Bangladeshi diagnostic lab test types with standard prices (BDT).
Also creates CenterTestPricing for all existing centers.
"""

from django.db import migrations

TESTS = [
    # ── Hematology ──────────────────────────────────────────────
    (
        "CBC (Complete Blood Count)",
        "Complete blood count including WBC, RBC, Hb, Hct, MCV, MCH, MCHC, Platelet count, and differential count.",
        500,
    ),
    ("ESR (Erythrocyte Sedimentation Rate)", "Westergren method ESR.", 200),
    ("Blood Group & Rh Typing", "ABO and Rh blood grouping.", 200),
    ("Hemoglobin (Hb)", "Hemoglobin estimation.", 150),
    (
        "Peripheral Blood Film (PBF)",
        "Microscopic examination of blood smear for morphology.",
        400,
    ),
    ("Platelet Count", "Platelet count from venous blood.", 200),
    ("Reticulocyte Count", "Percentage of reticulocytes in blood.", 300),
    ("Bleeding Time (BT)", "Duke method bleeding time.", 150),
    ("Clotting Time (CT)", "Lee-White clotting time.", 150),
    ("PT (Prothrombin Time)", "Prothrombin time with INR.", 500),
    (
        "APTT (Activated Partial Thromboplastin Time)",
        "Coagulation screening test.",
        500,
    ),
    ("D-Dimer", "Quantitative D-Dimer for thrombosis screening.", 1500),
    ("Coagulation Profile", "PT, APTT, INR, Fibrinogen.", 1200),
    ("Total WBC Count", "Total white blood cell count.", 150),
    ("Differential Count (DC)", "Differential leucocyte count.", 200),
    # ── Blood Sugar / Diabetes ──────────────────────────────────
    ("Blood Sugar (Fasting)", "Fasting blood glucose.", 200),
    ("Blood Sugar (Random)", "Random blood glucose.", 200),
    (
        "Blood Sugar (2hr ABF / PP)",
        "Post-prandial blood sugar, 2 hours after meal.",
        200,
    ),
    ("HbA1c (Glycated Hemoglobin)", "3-month average blood sugar level.", 800),
    (
        "OGTT (Oral Glucose Tolerance Test)",
        "Fasting + 1hr + 2hr glucose after 75g glucose load.",
        500,
    ),
    # ── Lipid Profile ───────────────────────────────────────────
    (
        "Lipid Profile",
        "Total Cholesterol, HDL, LDL, Triglycerides, VLDL, TC/HDL ratio.",
        800,
    ),
    ("Total Cholesterol", "Serum total cholesterol.", 300),
    ("Triglycerides (TG)", "Serum triglycerides.", 300),
    ("HDL Cholesterol", "High-density lipoprotein cholesterol.", 300),
    ("LDL Cholesterol", "Low-density lipoprotein cholesterol.", 300),
    # ── Liver Function ──────────────────────────────────────────
    (
        "Liver Function Test (LFT)",
        "SGPT, SGOT, Bilirubin (Total & Direct), ALP, Total Protein, Albumin, Globulin, A/G Ratio.",
        1200,
    ),
    ("SGPT / ALT", "Serum Glutamic-Pyruvic Transaminase.", 300),
    ("SGOT / AST", "Serum Glutamic-Oxaloacetic Transaminase.", 300),
    ("Bilirubin (Total & Direct)", "Serum bilirubin total and direct.", 400),
    ("Alkaline Phosphatase (ALP)", "Serum alkaline phosphatase.", 300),
    ("GGT (Gamma-GT)", "Gamma-glutamyl transferase.", 400),
    ("Total Protein", "Serum total protein.", 250),
    ("Serum Albumin", "Serum albumin level.", 250),
    # ── Kidney / Renal Function ─────────────────────────────────
    (
        "Renal Function Test (RFT)",
        "Creatinine, BUN, Urea, Uric Acid, Electrolytes.",
        1200,
    ),
    ("Serum Creatinine", "Kidney function marker.", 300),
    ("Blood Urea / BUN", "Blood urea nitrogen.", 300),
    ("Serum Uric Acid", "Uric acid level for gout screening.", 300),
    ("Serum Electrolytes", "Na+, K+, Cl-, HCO3-.", 800),
    ("Serum Calcium", "Total serum calcium.", 350),
    ("Serum Phosphorus", "Inorganic phosphorus.", 350),
    ("Serum Magnesium", "Magnesium level.", 400),
    # ── Iron Studies ────────────────────────────────────────────
    ("Serum Iron", "Iron level in blood.", 400),
    ("TIBC (Total Iron Binding Capacity)", "Iron binding capacity.", 500),
    ("Serum Ferritin", "Iron stores marker.", 700),
    # ── Inflammatory Markers ────────────────────────────────────
    ("CRP (C-Reactive Protein)", "Inflammation marker, quantitative.", 500),
    ("hs-CRP (High Sensitivity CRP)", "Cardiac risk marker.", 800),
    ("ASO Titre", "Anti-Streptolysin O for rheumatic fever.", 400),
    ("RA Factor (Rheumatoid Factor)", "Rheumatoid arthritis screening.", 500),
    ("ANA (Anti-Nuclear Antibody)", "Autoimmune screening.", 1500),
    # ── Hormones / Thyroid ──────────────────────────────────────
    ("Thyroid Profile (T3, T4, TSH)", "Complete thyroid function test.", 1200),
    ("TSH (Thyroid Stimulating Hormone)", "Thyroid screening.", 500),
    ("Free T3 (FT3)", "Free triiodothyronine.", 500),
    ("Free T4 (FT4)", "Free thyroxine.", 500),
    ("Total T3", "Total triiodothyronine.", 400),
    ("Total T4", "Total thyroxine.", 400),
    # ── Other Hormones ──────────────────────────────────────────
    ("Testosterone", "Total testosterone level.", 800),
    ("Prolactin", "Serum prolactin.", 800),
    ("FSH (Follicle Stimulating Hormone)", "Reproductive hormone.", 800),
    ("LH (Luteinizing Hormone)", "Reproductive hormone.", 800),
    ("Estradiol (E2)", "Estrogen level.", 800),
    ("Progesterone", "Serum progesterone.", 800),
    (
        "Beta hCG (Pregnancy Test - Quantitative)",
        "Quantitative pregnancy hormone.",
        700,
    ),
    ("Cortisol (Morning)", "Serum cortisol.", 800),
    ("Insulin (Fasting)", "Fasting insulin level.", 900),
    ("Growth Hormone (GH)", "Serum growth hormone.", 1000),
    ("PTH (Parathyroid Hormone)", "Parathyroid hormone level.", 1200),
    # ── Vitamins ────────────────────────────────────────────────
    ("Vitamin D (25-OH)", "25-hydroxy vitamin D level.", 1500),
    ("Vitamin B12", "Serum B12 level.", 1200),
    ("Folic Acid (Folate)", "Serum folate level.", 1000),
    # ── Serology / Infectious Disease ───────────────────────────
    ("HBsAg (Hepatitis B Surface Antigen)", "Hepatitis B screening.", 400),
    ("Anti-HCV (Hepatitis C Antibody)", "Hepatitis C screening.", 600),
    ("HIV 1 & 2 (Antibody)", "HIV screening test.", 500),
    ("VDRL / RPR", "Syphilis screening.", 300),
    ("Widal Test", "Typhoid fever antibody test.", 350),
    ("Typhidot (IgG/IgM)", "Rapid typhoid detection.", 600),
    ("Dengue NS1 Antigen", "Early dengue detection.", 800),
    ("Dengue IgG / IgM", "Dengue antibody detection.", 1000),
    (
        "Malaria (ICT/Rapid)",
        "Rapid malaria antigen test (P. falciparum / P. vivax).",
        500,
    ),
    (
        "Malaria Parasite (MP) - Smear",
        "Thick and thin blood film for malaria parasite.",
        300,
    ),
    ("Troponin I", "Cardiac biomarker for heart attack.", 1000),
    ("Pro-BNP / NT-proBNP", "Heart failure biomarker.", 2000),
    ("Procalcitonin", "Bacterial infection / sepsis marker.", 2500),
    # ── Urine Tests ─────────────────────────────────────────────
    (
        "Urine Routine (R/E)",
        "Routine urine examination — color, pH, specific gravity, sugar, protein, microscopy.",
        200,
    ),
    ("Urine Culture & Sensitivity", "Urine culture with antibiotic sensitivity.", 800),
    (
        "Urine Microalbumin (ACR)",
        "Albumin-creatinine ratio for diabetic kidney screening.",
        600,
    ),
    ("24-hour Urine Protein", "Quantitative protein in 24hr urine.", 500),
    ("Urine for Pregnancy Test", "Qualitative hCG in urine.", 200),
    ("Urine Sugar (Benedict)", "Benedict test for glucose in urine.", 100),
    # ── Stool Tests ─────────────────────────────────────────────
    (
        "Stool Routine (R/E)",
        "Routine stool examination — color, consistency, microscopy, OBT.",
        200,
    ),
    ("Stool Culture & Sensitivity", "Stool culture with antibiotic sensitivity.", 800),
    ("Stool Occult Blood (OBT)", "Fecal occult blood test.", 250),
    ("Stool for Reducing Substance", "Reducing substance in stool.", 200),
    # ── Microbiology / Culture ──────────────────────────────────
    (
        "Blood Culture & Sensitivity",
        "Aerobic blood culture with antibionic sensitivity.",
        1200,
    ),
    ("Sputum Culture & Sensitivity", "Sputum culture for respiratory infections.", 800),
    ("Sputum for AFB (Acid-Fast Bacilli)", "ZN stain for tuberculosis screening.", 300),
    ("Wound / Pus Culture & Sensitivity", "Culture from wound or abscess.", 800),
    ("Throat Swab Culture", "Throat culture for bacterial pharyngitis.", 700),
    ("Gram Stain", "Gram staining for bacteria identification.", 250),
    (
        "KOH Mount (Fungal Smear)",
        "Potassium hydroxide preparation for fungal elements.",
        250,
    ),
    # ── Tumor Markers ───────────────────────────────────────────
    ("AFP (Alpha-Fetoprotein)", "Liver cancer / pregnancy screening marker.", 1200),
    ("PSA (Prostate Specific Antigen)", "Prostate cancer screening.", 1200),
    ("CEA (Carcinoembryonic Antigen)", "Colorectal / GI cancer marker.", 1200),
    ("CA-125", "Ovarian cancer marker.", 1500),
    ("CA 19-9", "Pancreatic / GI cancer marker.", 1500),
    ("CA 15-3", "Breast cancer marker.", 1500),
    # ── Enzymes / Special Biochemistry ──────────────────────────
    ("Amylase (Serum)", "Pancreatic enzyme.", 500),
    ("Lipase (Serum)", "Pancreatic lipase.", 500),
    ("LDH (Lactate Dehydrogenase)", "Tissue damage marker.", 500),
    ("CPK (Creatine Phosphokinase)", "Muscle / cardiac enzyme.", 500),
    ("CPK-MB", "Cardiac-specific CPK isoenzyme.", 700),
    # ── Body Fluid Analysis ─────────────────────────────────────
    (
        "CSF Analysis",
        "Cerebrospinal fluid — cell count, protein, glucose, Gram stain.",
        1000,
    ),
    ("Pleural Fluid Analysis", "Pleural fluid cytology and biochemistry.", 800),
    ("Peritoneal (Ascitic) Fluid Analysis", "Ascitic fluid analysis.", 800),
    ("Synovial Fluid Analysis", "Joint fluid analysis for gout / infection.", 800),
    ("Semen Analysis", "Sperm count, motility, morphology.", 500),
    # ── Allergy / Immunoglobulin ────────────────────────────────
    ("Serum IgE (Total)", "Total immunoglobulin E for allergy screening.", 1000),
    ("Specific IgE Panel", "Allergen-specific IgE panel.", 3000),
    # ── Imaging / ECG (commonly done in labs) ───────────────────
    ("ECG (Electrocardiogram)", "12-lead resting ECG.", 300),
    ("X-Ray Chest (PA View)", "Posteroanterior chest X-ray.", 500),
    ("X-Ray (Other)", "X-ray of specified body part.", 500),
    ("Ultrasound - Whole Abdomen", "USG of whole abdomen.", 1500),
    ("Ultrasound - Lower Abdomen", "USG of lower abdomen / pelvic.", 1200),
    ("Ultrasound - Pregnancy (Obstetric)", "Obstetric ultrasound.", 1500),
    ("Color Doppler (Vascular)", "Doppler ultrasound for vascular study.", 3000),
    ("Echocardiography (Echo)", "Cardiac ultrasound.", 3000),
]


def seed_tests(apps, schema_editor):
    TestType = apps.get_model("diagnostics", "TestType")
    CenterTestPricing = apps.get_model("diagnostics", "CenterTestPricing")
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")

    centers = list(DiagnosticCenter.objects.all())

    for name, description, base_price in TESTS:
        test_type, created = TestType.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "base_price": base_price,
            },
        )
        # Create pricing for each center
        for center in centers:
            CenterTestPricing.objects.get_or_create(
                center=center,
                test_type=test_type,
                defaults={
                    "price": base_price,
                    "is_available": True,
                },
            )


def remove_tests(apps, schema_editor):
    TestType = apps.get_model("diagnostics", "TestType")
    names = [t[0] for t in TESTS]
    TestType.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("diagnostics", "0005_bangladesh_workflow"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tests, remove_tests),
    ]

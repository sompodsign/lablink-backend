"""Runtime diagnostics catalog seeding helpers.

Historical migrations keep their own frozen seed snapshots. This module is the
runtime source of truth used by management commands and signals.
"""

import logging

from apps.diagnostics.models import CenterTestPricing, ReportTemplate, TestType
from apps.diagnostics.template_fields import TEMPLATE_FIELDS

logger = logging.getLogger(__name__)

SEEDED_TEST_TYPES = [
    (
        "CBC (Complete Blood Count)",
        "Complete blood count including WBC, RBC, Hb, Hct, MCV, MCH, MCHC, "
        "Platelet count, and differential count.",
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
    (
        "CBC + ESR",
        "Combined complete blood count and erythrocyte sedimentation rate.",
        700,
    ),
    ("PCV (Packed Cell Volume)", "Packed cell volume / hematocrit estimation.", 300),
    ("Reticulocyte Count", "Percentage of reticulocytes in blood.", 300),
    ("Bleeding Time (BT)", "Duke method bleeding time.", 150),
    ("Clotting Time (CT)", "Lee-White clotting time.", 150),
    (
        "Hb Electrophoresis",
        "Hemoglobin electrophoresis for hemoglobinopathy screening.",
        1800,
    ),
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
    (
        "Lipid Profile",
        "Total Cholesterol, HDL, LDL, Triglycerides, VLDL, TC/HDL ratio.",
        800,
    ),
    ("Total Cholesterol", "Serum total cholesterol.", 300),
    ("Triglycerides (TG)", "Serum triglycerides.", 300),
    ("HDL Cholesterol", "High-density lipoprotein cholesterol.", 300),
    ("LDL Cholesterol", "Low-density lipoprotein cholesterol.", 300),
    (
        "Liver Function Test (LFT)",
        "SGPT, SGOT, Bilirubin (Total & Direct), ALP, Total Protein, Albumin, "
        "Globulin, A/G Ratio.",
        1200,
    ),
    ("SGPT / ALT", "Serum Glutamic-Pyruvic Transaminase.", 300),
    ("SGOT / AST", "Serum Glutamic-Oxaloacetic Transaminase.", 300),
    ("Bilirubin (Total & Direct)", "Serum bilirubin total and direct.", 400),
    ("Alkaline Phosphatase (ALP)", "Serum alkaline phosphatase.", 300),
    ("A/G Ratio", "Albumin globulin ratio.", 1200),
    ("GGT (Gamma-GT)", "Gamma-glutamyl transferase.", 400),
    ("Total Protein", "Serum total protein.", 250),
    ("Serum Albumin", "Serum albumin level.", 250),
    (
        "Renal Function Test (RFT)",
        "Creatinine, BUN, Urea, Uric Acid, Electrolytes.",
        1200,
    ),
    ("Serum Creatinine", "Kidney function marker.", 300),
    ("Blood Urea / BUN", "Blood urea nitrogen.", 300),
    ("Serum Uric Acid", "Uric acid level for gout screening.", 300),
    (
        "Creatinine / Blood Urea / Uric Acid Profile",
        "Combined renal profile with creatinine, blood urea, and uric acid.",
        600,
    ),
    (
        "Total Protein / Albumin / Phosphate",
        "Combined protein, albumin, and phosphate profile.",
        700,
    ),
    ("Serum Electrolytes", "Na+, K+, Cl-, HCO3-.", 800),
    ("Bilirubin (Total)", "Serum total bilirubin.", 500),
    ("Serum Calcium", "Total serum calcium.", 350),
    ("Serum Phosphorus", "Inorganic phosphorus.", 350),
    ("Serum Magnesium", "Magnesium level.", 400),
    ("Serum Iron", "Iron level in blood.", 400),
    ("TIBC (Total Iron Binding Capacity)", "Iron binding capacity.", 500),
    ("Serum Ferritin", "Iron stores marker.", 700),
    ("CRP (C-Reactive Protein)", "Inflammation marker, quantitative.", 500),
    ("hs-CRP (High Sensitivity CRP)", "Cardiac risk marker.", 800),
    ("ASO Titre", "Anti-Streptolysin O for rheumatic fever.", 400),
    ("RA Factor (Rheumatoid Factor)", "Rheumatoid arthritis screening.", 500),
    ("ANA (Anti-Nuclear Antibody)", "Autoimmune screening.", 1500),
    ("Thyroid Profile (T3, T4, TSH)", "Complete thyroid function test.", 1200),
    ("TSH (Thyroid Stimulating Hormone)", "Thyroid screening.", 500),
    ("Free T3 (FT3)", "Free triiodothyronine.", 500),
    ("Free T4 (FT4)", "Free thyroxine.", 500),
    ("Total T3", "Total triiodothyronine.", 400),
    ("Total T4", "Total thyroxine.", 400),
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
    ("Vitamin D (25-OH)", "25-hydroxy vitamin D level.", 1500),
    ("Vitamin B12", "Serum B12 level.", 1200),
    ("Folic Acid (Folate)", "Serum folate level.", 1000),
    ("HBsAg (Hepatitis B Surface Antigen)", "Hepatitis B screening.", 400),
    ("Anti-HCV (Hepatitis C Antibody)", "Hepatitis C screening.", 600),
    ("HIV 1 & 2 (Antibody)", "HIV screening test.", 500),
    ("VDRL / RPR", "Syphilis screening.", 300),
    ("Widal Test", "Typhoid fever antibody test.", 350),
    (
        "Triple Antigen / Febrile Antigen Panel",
        "Rapid febrile antigen screening panel.",
        600,
    ),
    (
        "TPHA (Treponema pallidum Hemagglutination Assay)",
        "TPHA serology test for syphilis.",
        600,
    ),
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
    ("H. pylori (ICT)", "Rapid ICT screening for Helicobacter pylori.", 800),
    ("Kala-azar (ICT)", "Rapid ICT screening for kala-azar.", 800),
    ("Pro-BNP / NT-proBNP", "Heart failure biomarker.", 2000),
    ("Procalcitonin", "Bacterial infection / sepsis marker.", 2500),
    (
        "Urine Routine (R/E)",
        "Routine urine examination — color, pH, specific gravity, sugar, "
        "protein, microscopy.",
        200,
    ),
    (
        "Urine Culture & Sensitivity",
        "Urine culture with antibiotic sensitivity.",
        800,
    ),
    (
        "Urine Microalbumin (ACR)",
        "Albumin-creatinine ratio for diabetic kidney screening.",
        600,
    ),
    ("24-hour Urine Protein", "Quantitative protein in 24hr urine.", 500),
    ("Urine for Pregnancy Test", "Qualitative hCG in urine.", 200),
    ("Urine Sugar (Benedict)", "Benedict test for glucose in urine.", 100),
    (
        "Stool Routine (R/E)",
        "Routine stool examination — color, consistency, microscopy, OBT.",
        200,
    ),
    (
        "Stool Culture & Sensitivity",
        "Stool culture with antibiotic sensitivity.",
        800,
    ),
    ("Stool Occult Blood (OBT)", "Fecal occult blood test.", 250),
    ("Stool for Reducing Substance", "Reducing substance in stool.", 200),
    (
        "Blood Culture & Sensitivity",
        "Aerobic blood culture with antibionic sensitivity.",
        1200,
    ),
    (
        "Sputum Culture & Sensitivity",
        "Sputum culture for respiratory infections.",
        800,
    ),
    (
        "Sputum for AFB (Acid-Fast Bacilli)",
        "ZN stain for tuberculosis screening.",
        300,
    ),
    (
        "Wound / Pus Culture & Sensitivity",
        "Culture from wound or abscess.",
        800,
    ),
    ("Throat Swab Culture", "Throat culture for bacterial pharyngitis.", 700),
    ("Gram Stain", "Gram staining for bacteria identification.", 250),
    (
        "KOH Mount (Fungal Smear)",
        "Potassium hydroxide preparation for fungal elements.",
        250,
    ),
    (
        "Skin / Nail Scraping for Fungus",
        "Microscopic examination of skin or nail scrapings for fungus.",
        600,
    ),
    ("P/S for Gram Stain", "Pus sample examination by Gram stain.", 1000),
    ("Crossmatching", "Blood crossmatching compatibility test.", 1000),
    (
        "Swab for Culture & Sensitivity",
        "Culture and antibiotic sensitivity from a swab specimen.",
        1200,
    ),
    (
        "AFP (Alpha-Fetoprotein)",
        "Liver cancer / pregnancy screening marker.",
        1200,
    ),
    ("PSA (Prostate Specific Antigen)", "Prostate cancer screening.", 1200),
    ("CEA (Carcinoembryonic Antigen)", "Colorectal / GI cancer marker.", 1200),
    ("CA-125", "Ovarian cancer marker.", 1500),
    ("CA 19-9", "Pancreatic / GI cancer marker.", 1500),
    ("CA 15-3", "Breast cancer marker.", 1500),
    ("Amylase (Serum)", "Pancreatic enzyme.", 500),
    ("Lipase (Serum)", "Pancreatic lipase.", 500),
    ("LDH (Lactate Dehydrogenase)", "Tissue damage marker.", 500),
    ("CPK (Creatine Phosphokinase)", "Muscle / cardiac enzyme.", 500),
    ("CPK-MB", "Cardiac-specific CPK isoenzyme.", 700),
    ("ADA (Adenosine Deaminase)", "Adenosine deaminase test.", 1500),
    ("Fluid Study", "Laboratory examination of body fluid samples.", 2500),
    (
        "CSF Analysis",
        "Cerebrospinal fluid — cell count, protein, glucose, Gram stain.",
        1000,
    ),
    (
        "Pleural Fluid Analysis",
        "Pleural fluid cytology and biochemistry.",
        800,
    ),
    ("Peritoneal (Ascitic) Fluid Analysis", "Ascitic fluid analysis.", 800),
    ("Synovial Fluid Analysis", "Joint fluid analysis for gout / infection.", 800),
    ("Semen Analysis", "Sperm count, motility, morphology.", 500),
    (
        "Serum IgE (Total)",
        "Total immunoglobulin E for allergy screening.",
        1000,
    ),
    ("Specific IgE Panel", "Allergen-specific IgE panel.", 3000),
    ("ECG (Electrocardiogram)", "12-lead resting ECG.", 300),
    ("X-Ray Chest (PA View)", "Posteroanterior chest X-ray.", 500),
    ("X-Ray (Other)", "X-ray of specified body part.", 500),
    (
        "CT Scan of Brain / Face / Skull",
        "CT imaging of the brain, face, or skull.",
        3500,
    ),
    ("CT Scan of Chest / HRCT", "CT or HRCT imaging of the chest.", 6000),
    (
        "CT Scan of Lower Abdomen / Pelvis",
        "CT imaging of the lower abdomen or pelvis.",
        6000,
    ),
    (
        "CT Scan of Upper Abdomen / HBS",
        "CT imaging of the upper abdomen or hepatobiliary system.",
        6000,
    ),
    ("CT Scan of Neck", "CT imaging of the neck.", 5000),
    ("CT Scan of PNS", "CT imaging of the paranasal sinuses.", 5000),
    ("CT Scan of KUB", "CT imaging of the kidneys, ureters, and bladder.", 6000),
    (
        "CT Scan of Liver / Pancreas / Kidneys",
        "CT imaging focused on the liver, pancreas, or kidneys.",
        10000,
    ),
    ("CT Urogram", "CT urography of the urinary tract.", 10000),
    ("X-Ray KUB", "Plain X-ray of the kidneys, ureters, and bladder.", 1000),
    ("X-Ray Plain Abdomen", "Plain abdominal X-ray.", 1000),
    ("X-Ray Mastoids Towne View", "Towne view X-ray of the mastoids.", 500),
    ("X-Ray Mastoids L/V", "Lateral view X-ray of the mastoids.", 400),
    ("X-Ray OPG", "Orthopantomogram dental panoramic X-ray.", 400),
    ("X-Ray Dental", "Dental X-ray imaging.", 300),
    ("X-Ray IVU (With Medicine)", "Intravenous urography with contrast.", 4500),
    ("X-Ray MCU (With Medicine)", "Micturating cystourethrogram with contrast.", 3500),
    ("X-Ray Urethrogram (With Medicine)", "Contrast urethrogram imaging.", 4000),
    ("X-Ray Barium Meal (With Medicine)", "Barium meal imaging with contrast.", 4500),
    (
        "X-Ray Barium Swallow / Oesophagus",
        "Barium swallow imaging of the oesophagus.",
        1800,
    ),
    (
        "X-Ray Retrograde Cystourethrogram",
        "Retrograde cystourethrogram imaging.",
        1800,
    ),
    (
        "X-Ray Barium Meal of Stomach & Duodenum",
        "Barium imaging of the stomach and duodenum.",
        1800,
    ),
    ("X-Ray Barium Follow Through", "Barium follow-through imaging study.", 3500),
    (
        "X-Ray Barium Enema of Large Gut",
        "Barium enema imaging of the large intestine.",
        3500,
    ),
    ("Ultrasound - Whole Abdomen", "USG of whole abdomen.", 1500),
    ("Ultrasound - Lower Abdomen", "USG of lower abdomen / pelvic.", 1200),
    ("USG of Upper Abdomen", "Ultrasonography of the upper abdomen.", 1200),
    ("USG of HBS", "Ultrasonography of the hepatobiliary system.", 1200),
    ("USG of KUB", "Ultrasonography of the kidneys, ureters, and bladder.", 1200),
    (
        "USG of Uterus & Adnexa",
        "Ultrasonography of the uterus and adnexa.",
        1200,
    ),
    (
        "USG of Pregnancy Profile",
        "Pregnancy profile ultrasonography.",
        1000,
    ),
    ("USG of Anomaly Scan", "Obstetric anomaly scan ultrasonography.", 2200),
    ("USG of Parathyroid", "Ultrasonography of the parathyroid glands.", 1200),
    ("USG of Thyroid", "Ultrasonography of the thyroid gland.", 1200),
    ("USG of Testis / Scrotum", "Ultrasonography of the testis or scrotum.", 1200),
    ("USG of Both Breast", "Ultrasonography of both breasts.", 2200),
    ("USG of Breast", "Breast ultrasonography.", 1400),
    ("USG of Pelvic Organ", "Ultrasonography of the pelvic organs.", 1400),
    ("USG of TVS", "Transvaginal sonography.", 2200),
    ("Ultrasound - Pregnancy (Obstetric)", "Obstetric ultrasound.", 1500),
    ("Color Doppler (Vascular)", "Doppler ultrasound for vascular study.", 3000),
    ("Echocardiography 2D & M-Mode", "2D and M-mode echocardiography.", 1500),
    (
        "Echocardiography Color Doppler / 4D M-Mode",
        "Colour Doppler and advanced echocardiography study.",
        2500,
    ),
    ("Echocardiography (Echo)", "Cardiac ultrasound.", 3000),
    ("Endoscopy Upper GIT", "Upper gastrointestinal endoscopy.", 2000),
    ("ECG (12CH)", "12-channel electrocardiogram.", 400),
    ("ECG (12CH) With Report", "12-channel ECG with interpretation report.", 500),
    ("ECG (6CH)", "6-channel ECG.", 300),
]


def seed_test_types() -> dict[str, object]:
    test_types: dict[str, TestType] = {}
    created = 0
    skipped = 0

    for name, description, base_price in SEEDED_TEST_TYPES:
        test_type, was_created = TestType.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "base_price": base_price,
            },
        )
        test_types[name] = test_type
        if was_created:
            created += 1
        else:
            skipped += 1

    return {
        "test_types": test_types,
        "created": created,
        "skipped": skipped,
    }


def load_test_types_by_name() -> dict[str, TestType]:
    return {test_type.name: test_type for test_type in TestType.objects.all()}


def seed_center_pricing(
    center,
    *,
    test_types: dict[str, TestType] | None = None,
    default_is_available: bool = False,
) -> dict[str, int]:
    if test_types is None:
        test_types = load_test_types_by_name()

    existing = set(
        CenterTestPricing.objects.filter(center=center).values_list(
            "test_type_id",
            flat=True,
        )
    )
    to_create = []
    for test_type in test_types.values():
        if test_type.id in existing:
            continue
        to_create.append(
            CenterTestPricing(
                center=center,
                test_type=test_type,
                price=test_type.base_price,
                is_available=default_is_available,
            )
        )

    if to_create:
        CenterTestPricing.objects.bulk_create(to_create, ignore_conflicts=True)

    return {
        "created": len(to_create),
        "skipped": len(existing),
    }


def seed_center_templates(
    center,
    *,
    test_types: dict[str, TestType] | None = None,
    force: bool = False,
) -> dict[str, int]:
    if test_types is None:
        test_types = load_test_types_by_name()

    existing = set(
        ReportTemplate.objects.filter(center=center).values_list(
            "test_type_id",
            flat=True,
        )
    )
    to_create = []
    updated = 0
    skipped = 0

    for test_name, fields in TEMPLATE_FIELDS.items():
        test_type = test_types.get(test_name)
        if test_type is None:
            continue

        if test_type.id in existing:
            if force:
                ReportTemplate.objects.filter(
                    center=center,
                    test_type=test_type,
                ).update(fields=fields)
                updated += 1
            else:
                skipped += 1
            continue

        to_create.append(
            ReportTemplate(center=center, test_type=test_type, fields=fields)
        )

    if to_create:
        ReportTemplate.objects.bulk_create(to_create, ignore_conflicts=True)

    return {
        "created": len(to_create),
        "updated": updated,
        "skipped": skipped,
    }


def seed_center_defaults(
    center,
    *,
    test_types: dict[str, TestType] | None = None,
    force_templates: bool = False,
    default_is_available: bool = False,
) -> dict[str, dict[str, int]]:
    if test_types is None:
        test_types = load_test_types_by_name()

    pricing = seed_center_pricing(
        center,
        test_types=test_types,
        default_is_available=default_is_available,
    )
    templates = seed_center_templates(
        center,
        test_types=test_types,
        force=force_templates,
    )

    logger.info(
        "Seeded diagnostics defaults for center %s: pricing=%s templates=%s",
        center.id,
        pricing,
        templates,
    )

    return {
        "pricing": pricing,
        "templates": templates,
    }

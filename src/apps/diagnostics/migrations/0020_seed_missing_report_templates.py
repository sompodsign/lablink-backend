"""Backfill report templates for the expanded diagnostics catalog."""

from django.db import migrations


def _copy_fields(fields):
    return [field.copy() for field in fields]


def _single_field(name, unit='', ref_range=''):
    return [{'name': name, 'unit': unit, 'ref_range': ref_range}]


def _findings_template(default='Normal'):
    return [
        {'name': 'Findings', 'unit': '', 'ref_range': default},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ]


def _culture_template(default='No Growth'):
    return [
        {'name': 'Organism', 'unit': '', 'ref_range': default},
        {'name': 'Sensitivity Pattern', 'unit': '', 'ref_range': 'Sensitive'},
    ]


CBC_FIELDS = [
    {'name': 'Hemoglobin (Hb)', 'unit': 'g/dL', 'ref_range': 'M: 13.5-17.5 / F: 12.0-16.0'},
    {'name': 'RBC Count', 'unit': 'million/cumm', 'ref_range': 'M: 4.5-5.9 / F: 3.8-5.2'},
    {'name': 'Total WBC Count', 'unit': '/cumm', 'ref_range': '4000-11000'},
    {'name': 'Neutrophils', 'unit': '%', 'ref_range': '40-70'},
    {'name': 'Lymphocytes', 'unit': '%', 'ref_range': '20-40'},
    {'name': 'Monocytes', 'unit': '%', 'ref_range': '2-8'},
    {'name': 'Eosinophils', 'unit': '%', 'ref_range': '1-6'},
    {'name': 'Basophils', 'unit': '%', 'ref_range': '0-1'},
    {'name': 'Platelet Count', 'unit': '/cumm', 'ref_range': '150000-450000'},
    {'name': 'Hematocrit (HCT/PCV)', 'unit': '%', 'ref_range': 'M: 38-50 / F: 36-44'},
    {'name': 'MCV', 'unit': 'fL', 'ref_range': '80-100'},
    {'name': 'MCH', 'unit': 'pg', 'ref_range': '27-33'},
    {'name': 'MCHC', 'unit': 'g/dL', 'ref_range': '32-36'},
    {'name': 'RDW', 'unit': '%', 'ref_range': '11.5-14.5'},
]

ECG_FIELDS = [
    {'name': 'Heart Rate', 'unit': 'bpm', 'ref_range': '60-100'},
    {'name': 'Rhythm', 'unit': '', 'ref_range': 'Regular Sinus'},
    {'name': 'Axis', 'unit': '', 'ref_range': 'Normal'},
    {'name': 'Interpretation', 'unit': '', 'ref_range': 'Normal ECG'},
]

ECHO_FIELDS = [
    {'name': 'LV EF', 'unit': '%', 'ref_range': '55-70'},
    {'name': 'LV Function', 'unit': '', 'ref_range': 'Normal'},
    {'name': 'Valve Status', 'unit': '', 'ref_range': 'Normal'},
    {'name': 'Wall Motion', 'unit': '', 'ref_range': 'Normal'},
    {'name': 'Pericardium', 'unit': '', 'ref_range': 'Normal'},
    {'name': 'Impression', 'unit': '', 'ref_range': ''},
]

MISSING_TEMPLATE_FIELDS = {
    'CBC': _copy_fields(CBC_FIELDS),
    'CBC + ESR': _copy_fields(CBC_FIELDS)
    + [
        {
            'name': 'ESR (Westergren)',
            'unit': 'mm/1st hr',
            'ref_range': 'M: 0-15 / F: 0-20',
        }
    ],
    'PCV (Packed Cell Volume)': [
        {'name': 'PCV', 'unit': '%', 'ref_range': 'M: 38-50 / F: 36-44'},
    ],
    'Hb Electrophoresis': [
        {'name': 'HbA', 'unit': '%', 'ref_range': '95-98'},
        {'name': 'HbA2', 'unit': '%', 'ref_range': '2.0-3.5'},
        {'name': 'HbF', 'unit': '%', 'ref_range': '<1.0'},
        {'name': 'Interpretation', 'unit': '', 'ref_range': 'Normal Pattern'},
    ],
    'A/G Ratio': _single_field('A/G Ratio', '', '1.0-2.5'),
    'Creatinine / Blood Urea / Uric Acid Profile': [
        {'name': 'Serum Creatinine', 'unit': 'mg/dL', 'ref_range': 'M: 0.7-1.3 / F: 0.6-1.1'},
        {'name': 'Blood Urea', 'unit': 'mg/dL', 'ref_range': '15-40'},
        {'name': 'Serum Uric Acid', 'unit': 'mg/dL', 'ref_range': 'M: 3.4-7.0 / F: 2.4-6.0'},
    ],
    'Total Protein / Albumin / Phosphate': [
        {'name': 'Total Protein', 'unit': 'g/dL', 'ref_range': '6.0-8.3'},
        {'name': 'Albumin', 'unit': 'g/dL', 'ref_range': '3.5-5.5'},
        {'name': 'Phosphate', 'unit': 'mg/dL', 'ref_range': '2.5-4.5'},
    ],
    'Bilirubin (Total)': _single_field('Bilirubin (Total)', 'mg/dL', '0.1-1.2'),
    'TPHA (Treponema pallidum Hemagglutination Assay)': _single_field(
        'TPHA', '', 'Negative'
    ),
    'Triple Antigen / Febrile Antigen Panel': [
        {'name': 'S. typhi O', 'unit': '', 'ref_range': 'Negative'},
        {'name': 'S. typhi H', 'unit': '', 'ref_range': 'Negative'},
        {'name': 'S. paratyphi AH', 'unit': '', 'ref_range': 'Negative'},
        {'name': 'S. paratyphi BH', 'unit': '', 'ref_range': 'Negative'},
    ],
    'H. pylori (ICT)': _single_field('H. pylori', '', 'Negative'),
    'Kala-azar (ICT)': _single_field('Kala-azar', '', 'Negative'),
    'Crossmatching': [
        {'name': 'ABO Group', 'unit': '', 'ref_range': ''},
        {'name': 'Rh Factor', 'unit': '', 'ref_range': ''},
        {'name': 'Crossmatch Compatibility', 'unit': '', 'ref_range': 'Compatible'},
    ],
    'ADA (Adenosine Deaminase)': _single_field('ADA', 'U/L', '<24'),
    'Fluid Study': [
        {'name': 'Appearance', 'unit': '', 'ref_range': 'Clear'},
        {'name': 'Protein', 'unit': 'g/dL', 'ref_range': ''},
        {'name': 'Glucose', 'unit': 'mg/dL', 'ref_range': ''},
        {'name': 'Cell Count', 'unit': '/cumm', 'ref_range': ''},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'P/S for Gram Stain': [
        {'name': 'Gram Stain Result', 'unit': '', 'ref_range': 'No Organism Seen'},
        {'name': 'Pus Cells', 'unit': '/HPF', 'ref_range': '0-5'},
    ],
    'Skin / Nail Scraping for Fungus': _single_field(
        'Fungal Elements', '', 'Not Seen'
    ),
    'Swab for Culture & Sensitivity': _culture_template(),
    'ECG (12CH)': _copy_fields(ECG_FIELDS),
    'ECG (12CH) With Report': _copy_fields(ECG_FIELDS),
    'ECG (6CH)': _copy_fields(ECG_FIELDS),
    'Echocardiography 2D & M-Mode': _copy_fields(ECHO_FIELDS),
    'Echocardiography Color Doppler / 4D M-Mode': _copy_fields(ECHO_FIELDS),
    'Endoscopy Upper GIT': [
        {'name': 'Esophagus', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Stomach', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Duodenum', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'CT Scan of Brain / Face / Skull': _findings_template(),
    'CT Scan of Chest / HRCT': _findings_template(),
    'CT Scan of Lower Abdomen / Pelvis': _findings_template(),
    'CT Scan of Upper Abdomen / HBS': _findings_template(),
    'CT Scan of Neck': _findings_template(),
    'CT Scan of PNS': _findings_template(),
    'CT Scan of KUB': _findings_template(),
    'CT Scan of Liver / Pancreas / Kidneys': _findings_template(),
    'CT Urogram': _findings_template(),
    'X-Ray KUB': _findings_template(),
    'X-Ray Plain Abdomen': _findings_template(),
    'X-Ray Mastoids Towne View': _findings_template(),
    'X-Ray Mastoids L/V': _findings_template(),
    'X-Ray OPG': _findings_template(),
    'X-Ray Dental': _findings_template(),
    'X-Ray IVU (With Medicine)': _findings_template(),
    'X-Ray MCU (With Medicine)': _findings_template(),
    'X-Ray Urethrogram (With Medicine)': _findings_template(),
    'X-Ray Barium Meal (With Medicine)': _findings_template(),
    'X-Ray Barium Swallow / Oesophagus': _findings_template(),
    'X-Ray Retrograde Cystourethrogram': _findings_template(),
    'X-Ray Barium Meal of Stomach & Duodenum': _findings_template(),
    'X-Ray Barium Follow Through': _findings_template(),
    'X-Ray Barium Enema of Large Gut': _findings_template(),
    'USG of Upper Abdomen': [
        {'name': 'Liver', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Gallbladder', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Pancreas', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Spleen', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Kidneys', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of HBS': [
        {'name': 'Liver', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Gallbladder', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'CBD', 'unit': 'mm', 'ref_range': '<6'},
        {'name': 'Pancreas', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of KUB': [
        {'name': 'Right Kidney', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Left Kidney', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Urinary Bladder', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Prostate / Uterus', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Uterus & Adnexa': [
        {'name': 'Uterus', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Endometrium', 'unit': 'mm', 'ref_range': ''},
        {'name': 'Right Adnexa', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Left Adnexa', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Pregnancy Profile': [
        {'name': 'Gestational Age', 'unit': 'weeks', 'ref_range': ''},
        {'name': 'Fetal Heart Rate', 'unit': 'bpm', 'ref_range': '120-160'},
        {'name': 'Placenta', 'unit': '', 'ref_range': ''},
        {'name': 'Amniotic Fluid (AFI)', 'unit': 'cm', 'ref_range': '5-25'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Anomaly Scan': [
        {'name': 'Gestational Age', 'unit': 'weeks', 'ref_range': ''},
        {'name': 'Fetal Heart Rate', 'unit': 'bpm', 'ref_range': '120-160'},
        {'name': 'Fetal Anatomy', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Placenta', 'unit': '', 'ref_range': ''},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Parathyroid': [
        {'name': 'Parathyroid Findings', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Thyroid': [
        {'name': 'Right Lobe', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Left Lobe', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Isthmus', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Nodules', 'unit': '', 'ref_range': 'None'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Testis / Scrotum': [
        {'name': 'Right Testis', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Left Testis', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Epididymis', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Hydrocele / Varicocele', 'unit': '', 'ref_range': 'Absent'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Both Breast': [
        {'name': 'Right Breast', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Left Breast', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Axillary Nodes', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Breast': [
        {'name': 'Breast Parenchyma', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Mass / Cyst', 'unit': '', 'ref_range': 'Absent'},
        {'name': 'Axillary Nodes', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of Pelvic Organ': [
        {'name': 'Uterus', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Ovaries', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Urinary Bladder', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Pouch of Douglas', 'unit': '', 'ref_range': 'No Free Fluid'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
    'USG of TVS': [
        {'name': 'Uterus', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Endometrium', 'unit': 'mm', 'ref_range': ''},
        {'name': 'Ovaries', 'unit': '', 'ref_range': 'Normal'},
        {'name': 'Pouch of Douglas', 'unit': '', 'ref_range': 'No Free Fluid'},
        {'name': 'Impression', 'unit': '', 'ref_range': ''},
    ],
}


def seed_missing_templates(apps, schema_editor):
    CenterTestPricing = apps.get_model('diagnostics', 'CenterTestPricing')
    ReportTemplate = apps.get_model('diagnostics', 'ReportTemplate')
    TestType = apps.get_model('diagnostics', 'TestType')

    for test_name, fields in MISSING_TEMPLATE_FIELDS.items():
        test_type = TestType.objects.filter(name=test_name).first()
        if not test_type:
            continue

        center_ids = CenterTestPricing.objects.filter(
            test_type=test_type
        ).values_list('center_id', flat=True)

        for center_id in center_ids:
            ReportTemplate.objects.get_or_create(
                center_id=center_id,
                test_type=test_type,
                defaults={'fields': fields},
            )


class Migration(migrations.Migration):
    dependencies = [
        ('diagnostics', '0019_seed_full_diagnostics_catalog'),
    ]

    operations = [
        migrations.RunPython(seed_missing_templates, migrations.RunPython.noop),
    ]

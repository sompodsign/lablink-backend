"""Tests for the auto-calculation service."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.diagnostics.services.calculations import _safe_decimal, auto_calculate


class SafeDecimalTest(SimpleTestCase):
    """Tests for _safe_decimal helper."""

    def test_integer_string(self):
        self.assertEqual(_safe_decimal('14'), Decimal('14'))

    def test_decimal_string(self):
        self.assertEqual(_safe_decimal('14.5'), Decimal('14.5'))

    def test_with_spaces(self):
        self.assertEqual(_safe_decimal(' 14.5 '), Decimal('14.5'))

    def test_empty_string(self):
        self.assertIsNone(_safe_decimal(''))

    def test_none(self):
        self.assertIsNone(_safe_decimal(None))

    def test_text_only(self):
        self.assertIsNone(_safe_decimal('Positive'))

    def test_value_with_unit(self):
        self.assertEqual(_safe_decimal('14.5 g/dL'), Decimal('14.5'))


class AutoCalculateTest(SimpleTestCase):
    """Tests for auto_calculate function."""

    def test_ag_ratio(self):
        result_data = {
            'Albumin': {'value': '4.0', 'unit': 'g/dL', 'ref_range': '3.5-5.0'},
            'Globulin': {'value': '2.0', 'unit': 'g/dL', 'ref_range': '2.0-3.5'},
            'A/G Ratio': {'value': '', 'unit': '', 'ref_range': '1.0-2.0'},
        }
        result = auto_calculate(result_data)
        self.assertEqual(result['A/G Ratio']['value'], '2.00')
        self.assertTrue(result['A/G Ratio']['auto_calculated'])

    def test_ldl_friedewald(self):
        result_data = {
            'Total Cholesterol': {'value': '200', 'unit': 'mg/dL', 'ref_range': '< 200'},
            'HDL Cholesterol': {'value': '50', 'unit': 'mg/dL', 'ref_range': '> 40'},
            'Triglycerides': {'value': '150', 'unit': 'mg/dL', 'ref_range': '< 150'},
            'LDL Cholesterol': {'value': '', 'unit': 'mg/dL', 'ref_range': '< 100'},
        }
        result = auto_calculate(result_data)
        # LDL = 200 - 50 - (150/5) = 120.0
        self.assertEqual(result['LDL Cholesterol']['value'], '120.0')

    def test_vldl(self):
        result_data = {
            'Triglycerides': {'value': '150', 'unit': 'mg/dL', 'ref_range': '< 150'},
            'VLDL': {'value': '', 'unit': 'mg/dL', 'ref_range': ''},
        }
        result = auto_calculate(result_data)
        # VLDL = 150/5 = 30
        self.assertEqual(result['VLDL']['value'], '30.0')

    def test_mchc(self):
        result_data = {
            'Hemoglobin': {'value': '14.0', 'unit': 'g/dL', 'ref_range': '13-17'},
            'Hematocrit': {'value': '42.0', 'unit': '%', 'ref_range': '38-52'},
            'MCHC': {'value': '', 'unit': 'g/dL', 'ref_range': '32-36'},
        }
        result = auto_calculate(result_data)
        # MCHC = (14.0/42.0)*100 = 33.3
        self.assertEqual(result['MCHC']['value'], '33.3')

    def test_tc_hdl_ratio(self):
        result_data = {
            'Total Cholesterol': {'value': '200', 'unit': 'mg/dL', 'ref_range': '< 200'},
            'HDL Cholesterol': {'value': '50', 'unit': 'mg/dL', 'ref_range': '> 40'},
            'TC/HDL Ratio': {'value': '', 'unit': '', 'ref_range': '< 5'},
        }
        result = auto_calculate(result_data)
        self.assertEqual(result['TC/HDL Ratio']['value'], '4.00')

    def test_skips_already_filled(self):
        """Should not overwrite a value the user has manually entered."""
        result_data = {
            'Albumin': {'value': '4.0', 'unit': 'g/dL', 'ref_range': '3.5-5.0'},
            'Globulin': {'value': '2.0', 'unit': 'g/dL', 'ref_range': '2.0-3.5'},
            'A/G Ratio': {'value': '1.8', 'unit': '', 'ref_range': '1.0-2.0'},
        }
        result = auto_calculate(result_data)
        self.assertEqual(result['A/G Ratio']['value'], '1.8')
        self.assertNotIn('auto_calculated', result['A/G Ratio'])

    def test_skips_missing_operands(self):
        """Should not calculate if an operand field is missing."""
        result_data = {
            'Albumin': {'value': '4.0', 'unit': 'g/dL', 'ref_range': '3.5-5.0'},
            'A/G Ratio': {'value': '', 'unit': '', 'ref_range': '1.0-2.0'},
        }
        result = auto_calculate(result_data)
        self.assertEqual(result['A/G Ratio']['value'], '')

    def test_skips_zero_operand(self):
        """Should not divide by zero."""
        result_data = {
            'Albumin': {'value': '4.0', 'unit': 'g/dL', 'ref_range': '3.5-5.0'},
            'Globulin': {'value': '0', 'unit': 'g/dL', 'ref_range': '2.0-3.5'},
            'A/G Ratio': {'value': '', 'unit': '', 'ref_range': '1.0-2.0'},
        }
        result = auto_calculate(result_data)
        self.assertEqual(result['A/G Ratio']['value'], '')

    def test_skips_non_numeric_operand(self):
        result_data = {
            'Albumin': {'value': 'Positive', 'unit': '', 'ref_range': ''},
            'Globulin': {'value': '2.0', 'unit': 'g/dL', 'ref_range': '2.0-3.5'},
            'A/G Ratio': {'value': '', 'unit': '', 'ref_range': '1.0-2.0'},
        }
        result = auto_calculate(result_data)
        self.assertEqual(result['A/G Ratio']['value'], '')

    def test_field_not_in_result_data_ignored(self):
        """Should not add calculated fields that aren't in result_data."""
        result_data = {
            'Albumin': {'value': '4.0', 'unit': 'g/dL', 'ref_range': '3.5-5.0'},
            'Globulin': {'value': '2.0', 'unit': 'g/dL', 'ref_range': '2.0-3.5'},
        }
        result = auto_calculate(result_data)
        self.assertNotIn('A/G Ratio', result)

    def test_none_input(self):
        self.assertIsNone(auto_calculate(None))

    def test_empty_input(self):
        self.assertEqual(auto_calculate({}), {})

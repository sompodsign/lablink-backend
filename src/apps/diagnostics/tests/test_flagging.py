"""Tests for the abnormal value flagging service."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.diagnostics.services.flagging import (
    _parse_numeric,
    _parse_range,
    compute_flag,
    flag_report_results,
)


class ParseNumericTest(SimpleTestCase):
    """Tests for _parse_numeric helper."""

    def test_integer(self):
        self.assertEqual(_parse_numeric('14'), Decimal('14'))

    def test_decimal(self):
        self.assertEqual(_parse_numeric('14.5'), Decimal('14.5'))

    def test_with_spaces(self):
        self.assertEqual(_parse_numeric(' 14.5 '), Decimal('14.5'))

    def test_empty_string(self):
        self.assertIsNone(_parse_numeric(''))

    def test_none(self):
        self.assertIsNone(_parse_numeric(None))

    def test_text(self):
        self.assertIsNone(_parse_numeric('Positive'))

    def test_mixed(self):
        # Should strip non-numeric chars
        self.assertEqual(_parse_numeric('14.5 g/dL'), Decimal('14.5'))


class ParseRangeTest(SimpleTestCase):
    """Tests for _parse_range helper."""

    def test_simple_range(self):
        result = _parse_range('13.5-17.5')
        self.assertEqual(result['low'], Decimal('13.5'))
        self.assertEqual(result['high'], Decimal('17.5'))

    def test_range_with_spaces(self):
        result = _parse_range('13.5 - 17.5')
        self.assertEqual(result['low'], Decimal('13.5'))
        self.assertEqual(result['high'], Decimal('17.5'))

    def test_less_than(self):
        result = _parse_range('< 200')
        self.assertNotIn('low', result)
        self.assertEqual(result['high'], Decimal('200'))

    def test_less_than_no_space(self):
        result = _parse_range('<200')
        self.assertEqual(result['high'], Decimal('200'))

    def test_greater_than(self):
        result = _parse_range('> 40')
        self.assertEqual(result['low'], Decimal('40'))
        self.assertNotIn('high', result)

    def test_empty(self):
        self.assertIsNone(_parse_range(''))

    def test_none(self):
        self.assertIsNone(_parse_range(None))

    def test_qualitative(self):
        self.assertIsNone(_parse_range('Negative'))

    def test_phase_dependent(self):
        self.assertIsNone(_parse_range('Phase dependent'))


class ComputeFlagTest(SimpleTestCase):
    """Tests for compute_flag function."""

    def test_normal_value(self):
        self.assertEqual(compute_flag('15.0', '13.5-17.5'), 'N')

    def test_high_value(self):
        self.assertEqual(compute_flag('18.0', '13.5-17.5'), 'H')

    def test_low_value(self):
        self.assertEqual(compute_flag('12.0', '13.5-17.5'), 'L')

    def test_at_lower_bound(self):
        # 13.5 is at the lower bound (inclusive), should be normal
        self.assertEqual(compute_flag('13.5', '13.5-17.5'), 'N')

    def test_at_upper_bound(self):
        # 17.5 is at the upper bound (inclusive), should be normal
        self.assertEqual(compute_flag('17.5', '13.5-17.5'), 'N')

    def test_less_than_format_normal(self):
        self.assertEqual(compute_flag('150', '< 200'), 'N')

    def test_less_than_format_high(self):
        self.assertEqual(compute_flag('250', '< 200'), 'H')

    def test_greater_than_format_normal(self):
        self.assertEqual(compute_flag('50', '> 40'), 'N')

    def test_greater_than_format_low(self):
        self.assertEqual(compute_flag('30', '> 40'), 'L')

    def test_critical_high(self):
        self.assertEqual(
            compute_flag('25.0', '13.5-17.5', critical_high='20.0'),
            'CRITICAL_H',
        )

    def test_critical_low(self):
        self.assertEqual(
            compute_flag('5.0', '13.5-17.5', critical_low='7.0'),
            'CRITICAL_L',
        )

    def test_non_numeric_value(self):
        self.assertIsNone(compute_flag('Positive', '13.5-17.5'))

    def test_qualitative_range(self):
        self.assertIsNone(compute_flag('Negative', 'Negative'))

    def test_empty_value(self):
        self.assertIsNone(compute_flag('', '13.5-17.5'))

    def test_empty_range(self):
        self.assertIsNone(compute_flag('14.5', ''))


class FlagReportResultsTest(SimpleTestCase):
    """Tests for flag_report_results function."""

    def test_basic_flagging(self):
        result_data = {
            'Hemoglobin': {
                'value': '14.5',
                'unit': 'g/dL',
                'ref_range': '13.5-17.5',
            },
            'WBC': {
                'value': '12000',
                'unit': 'cells/mcL',
                'ref_range': '4000-11000',
            },
        }
        flagged = flag_report_results(result_data)
        self.assertEqual(flagged['Hemoglobin']['flag'], 'N')
        self.assertEqual(flagged['WBC']['flag'], 'H')

    def test_preserves_original_data(self):
        result_data = {
            'Hemoglobin': {
                'value': '14.5',
                'unit': 'g/dL',
                'ref_range': '13.5-17.5',
                'finding': 'Normal',
            },
        }
        flagged = flag_report_results(result_data)
        self.assertEqual(flagged['Hemoglobin']['value'], '14.5')
        self.assertEqual(flagged['Hemoglobin']['unit'], 'g/dL')
        self.assertEqual(flagged['Hemoglobin']['finding'], 'Normal')
        self.assertEqual(flagged['Hemoglobin']['flag'], 'N')

    def test_with_template_critical_thresholds(self):
        result_data = {
            'Potassium': {
                'value': '6.8',
                'unit': 'mEq/L',
                'ref_range': '3.5-5.0',
            },
        }
        template_fields = [
            {
                'name': 'Potassium',
                'unit': 'mEq/L',
                'ref_range': '3.5-5.0',
                'critical_low': '2.5',
                'critical_high': '6.0',
            },
        ]
        flagged = flag_report_results(result_data, template_fields)
        self.assertEqual(flagged['Potassium']['flag'], 'CRITICAL_H')

    def test_qualitative_result(self):
        result_data = {
            'Culture': {
                'value': 'No Growth',
                'unit': '',
                'ref_range': '',
            },
        }
        flagged = flag_report_results(result_data)
        self.assertIsNone(flagged['Culture']['flag'])

    def test_empty_result_data(self):
        self.assertEqual(flag_report_results({}), {})
        self.assertIsNone(flag_report_results(None))

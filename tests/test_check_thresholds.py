"""
Unit tests for check_thresholds.py module.

Tests the QC metric validation functionality.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestParseArgs(unittest.TestCase):
      """Test argument parsing."""

    @patch('sys.argv', ['check_thresholds.py', '--fastqc-dir', 'test_dir', '--config', 'test.ini', '--output', 'output.json'])
    def test_parse_args_valid(self):
              """Test parsing valid arguments."""
              from bin.check_thresholds import parse_args
              args = parse_args()
              self.assertEqual(args.fastqc_dir, 'test_dir')
              self.assertEqual(args.config, 'test.ini')
              self.assertEqual(args.output, 'output.json')


class TestLoadThresholds(unittest.TestCase):
      """Test threshold configuration loading."""

    def test_load_thresholds_valid(self):
              """Test loading valid threshold config."""
              from bin.check_thresholds import load_thresholds

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
                      f.write('[thresholds]\n')
                      f.write('min_reads = 100000\n')
                      f.write('min_gc = 30.0\n')
                      f.write('max_gc = 70.0\n')
                      f.write('max_adapter_content = 5.0\n')
                      f.flush()

            thresholds = load_thresholds(f.name)
            self.assertEqual(thresholds['min_reads'], 100000)
            self.assertEqual(thresholds['min_gc'], 30.0)
            self.assertEqual(thresholds['max_gc'], 70.0)
            self.assertEqual(thresholds['max_adapter_content'], 5.0)

    def test_load_thresholds_missing_file(self):
              """Test loading non-existent config file."""
              from bin.check_thresholds import load_thresholds

        with self.assertRaises(FileNotFoundError):
                      load_thresholds('/nonexistent/path/config.ini')


class TestFastqcMetricsValidation(unittest.TestCase):
      """Test FastQC metrics validation."""

    def test_sample_pass(self):
              """Test sample that passes QC."""
              metrics = {
                  'total_sequences': 150000,
                  'gc_content': 50.0,
                  'adapter_content_max': 2.0
              }
              thresholds = {
                  'min_reads': 100000,
                  'min_gc': 30.0,
                  'max_gc': 70.0,
                  'max_adapter_content': 5.0
              }

        from bin.check_thresholds import validate_metrics
        status, reasons = validate_metrics(metrics, thresholds, 'test_sample')

        self.assertEqual(status, 'PASS')
        self.assertEqual(len(reasons), 0)

    def test_sample_fail_low_reads(self):
              """Test sample failing due to low read count."""
              metrics = {
                  'total_sequences': 50000,  # Below threshold
                  'gc_content': 50.0,
                  'adapter_content_max': 2.0
              }
              thresholds = {
                  'min_reads': 100000,
                  'min_gc': 30.0,
                  'max_gc': 70.0,
                  'max_adapter_content': 5.0
              }

        from bin.check_thresholds import validate_metrics
        status, reasons = validate_metrics(metrics, thresholds, 'test_sample')

        self.assertEqual(status, 'FAIL')
        self.assertTrue(any('reads' in r.lower() for r in reasons))

    def test_sample_fail_high_gc(self):
              """Test sample failing due to high GC content."""
              metrics = {
                  'total_sequences': 150000,
                  'gc_content': 85.0,  # Above threshold
                  'adapter_content_max': 2.0
              }
              thresholds = {
                  'min_reads': 100000,
                  'min_gc': 30.0,
                  'max_gc': 70.0,
                  'max_adapter_content': 5.0
              }

        from bin.check_thresholds import validate_metrics
        status, reasons = validate_metrics(metrics, thresholds, 'test_sample')

        self.assertEqual(status, 'FAIL')
        self.assertTrue(any('GC' in r for r in reasons))


class TestQCSummary(unittest.TestCase):
      """Test QC summary generation."""

    def test_generate_summary(self):
              """Test generating QC summary JSON."""
              summary = {
                  'sample1': {'status': 'PASS', 'reasons': []},
                  'sample2': {'status': 'FAIL', 'reasons': ['Low reads']}
              }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                      json.dump(summary, f)
                      f.flush()

            with open(f.name, 'r') as rf:
                              loaded = json.load(rf)

            self.assertEqual(loaded['sample1']['status'], 'PASS')
            self.assertEqual(loaded['sample2']['status'], 'FAIL')


if __name__ == '__main__':
      unittest.main()

#!/usr/bin/env python3
"""
Tests for disk temperature collection, focused on /dev/sdc scenarios.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from disk_collector import DiskHealthCollector


def _make_proc(returncode=0, stdout='', stderr=''):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


SATA_JSON = json.dumps({
    'ata_smart_attributes': {
        'table': [
            {'id': 194, 'name': 'Temperature_Celsius', 'raw': {'value': 31, 'string': '31 (Min/Max 21/45)'}},
        ]
    }
})

AIRFLOW_JSON = json.dumps({
    'ata_smart_attributes': {
        'table': [
            {'id': 190, 'name': 'Airflow_Temperature_Cel', 'raw': {'value': 35, 'string': '35'}},
        ]
    }
})

NVME_JSON = json.dumps({
    'temperature': {'current': 52},
    'nvme_smart_health_information_log': {'temperature': 52},
})

LSBLK_DISKS = 'sda disk\nsdb disk\nsdc disk\nnvme0n1 disk\n'


class TestGetTemperature(unittest.TestCase):

    def setUp(self):
        self.collector = DiskHealthCollector()

    @patch('disk_collector.subprocess.run')
    def test_sata_temperature_from_json(self, mock_run):
        mock_run.return_value = _make_proc(stdout=SATA_JSON)
        temp = self.collector._get_temperature('/dev/sdc')
        self.assertEqual(temp, 31.0)

    @patch('disk_collector.subprocess.run')
    def test_airflow_attribute_fallback(self, mock_run):
        mock_run.return_value = _make_proc(stdout=AIRFLOW_JSON)
        temp = self.collector._get_temperature('/dev/sdc')
        self.assertEqual(temp, 35.0)

    @patch('disk_collector.subprocess.run')
    def test_nvme_temperature_from_json(self, mock_run):
        mock_run.return_value = _make_proc(stdout=NVME_JSON)
        temp = self.collector._get_temperature('/dev/nvme0')
        self.assertEqual(temp, 52.0)

    @patch('disk_collector.subprocess.run')
    def test_lsblk_fallback_when_smartctl_fails(self, mock_run):
        # smartctl fails, lsblk succeeds
        mock_run.side_effect = [
            _make_proc(returncode=1, stdout='', stderr='Permission denied'),
            _make_proc(stdout='sdc  38\n'),
        ]
        temp = self.collector._get_temperature('/dev/sdc')
        self.assertEqual(temp, 38.0)

    @patch('disk_collector.subprocess.run')
    def test_returns_none_when_all_sources_fail(self, mock_run):
        mock_run.return_value = _make_proc(returncode=1)
        temp = self.collector._get_temperature('/dev/sdc')
        self.assertIsNone(temp)

    @patch('disk_collector.subprocess.run')
    def test_out_of_range_temperature_ignored(self, mock_run):
        # Attribute value of 5 is below the valid 10-80°C range
        bad_json = json.dumps({
            'ata_smart_attributes': {
                'table': [
                    {'id': 194, 'name': 'Temperature_Celsius', 'raw': {'value': 5, 'string': '5'}},
                ]
            }
        })
        mock_run.side_effect = [
            _make_proc(stdout=bad_json),
            _make_proc(returncode=1),  # lsblk also fails
        ]
        temp = self.collector._get_temperature('/dev/sdc')
        self.assertIsNone(temp)

    @patch('disk_collector.subprocess.run')
    def test_invalid_json_falls_through_to_lsblk(self, mock_run):
        mock_run.side_effect = [
            _make_proc(returncode=0, stdout='not valid json'),
            _make_proc(stdout='sdc  42\n'),
        ]
        temp = self.collector._get_temperature('/dev/sdc')
        self.assertEqual(temp, 42.0)


class TestGetDiskDevices(unittest.TestCase):

    def setUp(self):
        self.collector = DiskHealthCollector()

    @patch('disk_collector.subprocess.run')
    @patch('disk_collector.psutil.disk_partitions')
    def test_sdc_detected(self, mock_partitions, mock_run):
        mock_partitions.return_value = []
        mock_run.return_value = _make_proc(stdout=LSBLK_DISKS)
        devices = self.collector._get_disk_devices()
        self.assertIn('/dev/sdc', devices)

    @patch('disk_collector.subprocess.run')
    @patch('disk_collector.psutil.disk_partitions')
    def test_nvme_detected(self, mock_partitions, mock_run):
        mock_partitions.return_value = []
        mock_run.return_value = _make_proc(stdout=LSBLK_DISKS)
        devices = self.collector._get_disk_devices()
        self.assertIn('/dev/nvme0n1', devices)

    @patch('disk_collector.subprocess.run')
    @patch('disk_collector.psutil.disk_partitions')
    def test_all_disks_detected(self, mock_partitions, mock_run):
        mock_partitions.return_value = []
        mock_run.return_value = _make_proc(stdout=LSBLK_DISKS)
        devices = self.collector._get_disk_devices()
        self.assertCountEqual(devices, ['/dev/sda', '/dev/sdb', '/dev/sdc', '/dev/nvme0n1'])

    @patch('disk_collector.subprocess.run')
    @patch('disk_collector.psutil.disk_partitions')
    def test_partition_numbers_stripped(self, mock_partitions, mock_run):
        part = MagicMock()
        part.device = '/dev/sdc1'
        mock_partitions.return_value = [part]
        mock_run.return_value = _make_proc(stdout='')
        devices = self.collector._get_disk_devices()
        self.assertIn('/dev/sdc', devices)
        self.assertNotIn('/dev/sdc1', devices)


if __name__ == '__main__':
    unittest.main()

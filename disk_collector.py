#!/usr/bin/env python3
"""
Disk Health Data Collector

This module collects comprehensive disk health information from Ubuntu systems
including SMART data, disk usage, temperature, and I/O statistics.
"""

import subprocess
import json
import psutil
import os
import re
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime


class DiskHealthCollector:
    """Collects disk health information from the system."""

    def __init__(self):
        self.disks = []
        self.system_info = {}

    def collect_all_data(self) -> Dict[str, Any]:
        """Collect all disk health data."""
        print("🔍 Collecting disk health data...")

        try:
            # Collect system information
            self.system_info = self._collect_system_info()

            # Get all disk devices
            self.disks = self._get_disk_devices()

            # Collect data for each disk
            disk_data = []
            for disk in self.disks:
                try:
                    disk_info = self._collect_disk_data(disk)
                    if disk_info:
                        disk_data.append(disk_info)
                except Exception as e:
                    print(f"⚠️  Warning: Could not collect data for disk {disk}: {e}")
                    continue

            return {
                'timestamp': datetime.now().isoformat(),
                'system_info': self.system_info,
                'disks': disk_data,
                'summary': self._generate_summary(disk_data)
            }

        except Exception as e:
            print(f"❌ Error collecting disk health data: {e}")
            return {'error': str(e)}

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect basic system information."""
        try:
            return {
                'hostname': os.uname().nodename,
                'platform': os.uname().sysname,
                'release': os.uname().release,
                'uptime': datetime.now().isoformat(),
                'python_version': sys.version.split()[0]
            }
        except Exception:
            return {'error': 'Could not collect system information'}

    def _get_disk_devices(self) -> List[str]:
        """Get list of disk devices to monitor."""
        disks = []

        # Get physical disks from psutil
        disk_partitions = psutil.disk_partitions()
        for partition in disk_partitions:
            if partition.device.startswith(('/dev/sd', '/dev/nvme', '/dev/hd', '/dev/vd')):
                # Extract base device name (remove partition number)
                device = partition.device
                if device.endswith(('p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9')):
                    device = device[:-2]  # Remove partition number for NVMe (e.g., nvme0n1p1 -> nvme0n1)
                elif device[-1].isdigit() and not device[-2:].isdigit():
                    device = device[:-1]  # Remove single digit partition number (e.g., sda1 -> sda)
                elif device[-2:].isdigit():
                    device = device[:-2]  # Remove two digit partition number (e.g., sda10 -> sda)

                if device not in disks:
                    disks.append(device)

        # Also check for additional devices that might not have mounted partitions
        try:
            result = subprocess.run(['lsblk', '-d', '-n', '-o', 'NAME,TYPE'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] == 'disk':
                            device_name = f"/dev/{parts[0]}"
                            if device_name not in disks:
                                disks.append(device_name)
        except Exception:
            pass

        return sorted(list(set(disks)))

    def _collect_disk_data(self, device: str) -> Optional[Dict[str, Any]]:
        """Collect comprehensive data for a specific disk."""
        disk_info = {
            'device': device,
            'smart_data': {},
            'usage_data': {},
            'io_stats': {},
            'temperature': None,
            'health_status': 'unknown'
        }

        # Collect SMART data
        smart_data = self._get_smart_data(device)
        if smart_data:
            disk_info['smart_data'] = smart_data
            disk_info['health_status'] = self._assess_smart_health(smart_data)

        # Collect usage data
        usage_data = self._get_usage_data(device)
        if usage_data:
            disk_info['usage_data'] = usage_data

        # Collect I/O statistics
        io_stats = self._get_io_stats(device)
        if io_stats:
            disk_info['io_stats'] = io_stats

        # Get temperature if available
        temperature = self._get_temperature(device)
        if temperature is not None:
            disk_info['temperature'] = temperature

        return disk_info if any([smart_data, usage_data, io_stats]) else None

    def _get_smart_data(self, device: str) -> Dict[str, Any]:
        """Get SMART data for the disk."""
        try:
            # Check if smartctl is available
            result = subprocess.run(['which', 'smartctl'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {'error': 'smartctl not available'}

            # Initialize variables
            health_status = 'UNKNOWN'
            attributes = {}
            device_info = {}

            # Get SMART overall health
            try:
                result = subprocess.run(['sudo', 'smartctl', '-H', device],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    health_output = result.stdout
                    if 'PASSED' in health_output:
                        health_status = 'PASSED'
                    elif 'FAILED' in health_output:
                        health_status = 'FAILED'
                    else:
                        health_status = 'UNKNOWN'
                else:
                    # Health check failed, but we can still get other SMART data
                    health_status = 'UNKNOWN'
            except Exception:
                # Health check failed, but we can still get other SMART data
                health_status = 'UNKNOWN'

            # Get detailed SMART attributes
            try:
                result = subprocess.run(['sudo', 'smartctl', '-A', device],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.strip() and not line.startswith('#') and not line.startswith('ID#'):
                            parts = line.split()
                            if len(parts) >= 10:
                                try:
                                    attr_id = parts[0]
                                    attr_name = parts[1]
                                    raw_value = parts[-1]
                                    attributes[attr_name] = {
                                        'id': attr_id,
                                        'raw_value': raw_value,
                                        'normalized': parts[3] if len(parts) > 3 else 'N/A'
                                    }
                                except IndexError:
                                    continue
            except Exception:
                pass

            # Get device information
            try:
                result = subprocess.run(['sudo', 'smartctl', '-i', device],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            device_info[key.strip()] = value.strip()
            except Exception:
                pass

            return {
                'health_status': health_status,
                'attributes': attributes,
                'device_info': device_info,
                'raw_output_available': True
            }

        except Exception as e:
            return {'error': f'SMART data collection failed: {str(e)}'}

    def _get_usage_data(self, device: str) -> Dict[str, Any]:
        """Get disk usage information."""
        try:
            # Get disk usage for mounted partitions
            partitions = psutil.disk_partitions()
            usage_data = {}

            for partition in partitions:
                if partition.device.startswith(device):
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        usage_data[partition.mountpoint] = {
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0,
                            'fstype': partition.fstype,
                            'mountpoint': partition.mountpoint
                        }
                    except PermissionError:
                        continue

            # Check for unmounted partitions on this device using lsblk
            try:
                result = subprocess.run(['lsblk', '-n', '-o', 'NAME,SIZE,MOUNTPOINT,FSTYPE', device],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            # Clean up the line by removing tree structure characters
                            clean_line = line.replace('├─', '').replace('└─', '').replace('│', '').replace(' ', ' ').strip()
                            parts = clean_line.split()
                            if len(parts) >= 2:  # At minimum we need NAME and SIZE
                                partition_name = parts[0]
                                size = parts[1]
                                mountpoint = ''
                                fstype = ''

                                # Find mountpoint and fstype - they might be empty
                                for i in range(2, len(parts)):
                                    # If the part doesn't look like a size (no K/M/G suffix), it's likely mountpoint or fstype
                                    if not any(suffix in parts[i] for suffix in ['K', 'M', 'G', 'T']):
                                        if mountpoint == '':
                                            mountpoint = parts[i]
                                        elif fstype == '':
                                            fstype = parts[i]
                                            break

                                # If partition is not mounted (mountpoint is empty or '-'), add it to usage data
                                if mountpoint == '' or mountpoint == '-' or mountpoint == '':
                                    partition_device = f"{device}{partition_name.replace(device.replace('/dev/', ''), '')}"
                                    usage_data[f"unmounted_{partition_name}"] = {
                                        'device': partition_device,
                                        'size': size,
                                        'fstype': fstype,
                                        'mountpoint': 'Not mounted',
                                        'status': 'unmounted'
                                    }
            except Exception:
                pass

            # Get disk I/O counters
            io_counters = psutil.disk_io_counters(perdisk=True)
            if device.replace('/dev/', '') in io_counters:
                counter = io_counters[device.replace('/dev/', '')]
                usage_data['io_counters'] = {
                    'read_count': counter.read_count,
                    'write_count': counter.write_count,
                    'read_bytes': counter.read_bytes,
                    'write_bytes': counter.write_bytes,
                    'read_time': counter.read_time,
                    'write_time': counter.write_time
                }

            return usage_data

        except Exception as e:
            return {'error': f'Usage data collection failed: {str(e)}'}

    def _get_io_stats(self, device: str) -> Dict[str, Any]:
        """Get I/O statistics for the disk."""
        try:
            # Read from /proc/diskstats
            with open('/proc/diskstats', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 14 and parts[2] == device.replace('/dev/', ''):
                        return {
                            'reads_completed': int(parts[3]),
                            'reads_merged': int(parts[4]),
                            'sectors_read': int(parts[5]),
                            'time_reading': int(parts[6]),
                            'writes_completed': int(parts[7]),
                            'writes_merged': int(parts[8]),
                            'sectors_written': int(parts[9]),
                            'time_writing': int(parts[10]),
                            'io_in_progress': int(parts[11]),
                            'time_doing_io': int(parts[12]),
                            'weighted_time_doing_io': int(parts[13])
                        }
            return {}
        except Exception as e:
            return {'error': f'I/O stats collection failed: {str(e)}'}

    def _get_temperature(self, device: str) -> Optional[float]:
        """Get disk temperature if available."""
        try:
            # Try smartctl temperature
            result = subprocess.run(['smartctl', '-A', device],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Temperature_Celsius' in line or 'Airflow_Temperature_Cel' in line:
                        parts = line.split()
                        if len(parts) >= 10:
                            try:
                                return float(parts[-1])
                            except ValueError:
                                continue

            # Try hddtemp if available
            result = subprocess.run(['hddtemp', device],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                match = re.search(r'(\d+)\s*°C', result.stdout)
                if match:
                    return float(match.group(1))

            return None
        except Exception:
            return None

    def _assess_smart_health(self, smart_data: Dict[str, Any]) -> str:
        """Assess disk health based on SMART data."""
        if 'error' in smart_data:
            return 'ERROR'

        health_status = smart_data.get('health_status', 'UNKNOWN')
        if health_status == 'PASSED':
            return 'GOOD'
        elif health_status == 'FAILED':
            return 'CRITICAL'
        else:
            return 'WARNING'

    def _generate_summary(self, disk_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of all disk health data."""
        if not disk_data:
            return {'status': 'no_disks_found', 'count': 0}

        summary = {
            'total_disks': len(disk_data),
            'health_status': {
                'good': 0,
                'warning': 0,
                'critical': 0,
                'unknown': 0,
                'error': 0
            },
            'issues': []
        }

        for disk in disk_data:
            status = disk.get('health_status', 'unknown')
            if status in summary['health_status']:
                summary['health_status'][status] += 1

            # Check for specific issues
            if disk.get('temperature') and disk['temperature'] > 50:
                summary['issues'].append(f"{disk['device']}: High temperature ({disk['temperature']}°C)")

            for mount, usage in disk.get('usage_data', {}).items():
                if isinstance(usage, dict) and 'percent' in usage:
                    if usage['percent'] > 90:
                        summary['issues'].append(f"{disk['device']} ({mount}): Critical disk usage ({usage['percent']:.1f}%)")
                    elif usage['percent'] > 80:
                        summary['issues'].append(f"{disk['device']} ({mount}): High disk usage ({usage['percent']:.1f}%)")

        # Determine overall status
        if summary['health_status']['critical'] > 0:
            summary['status'] = 'CRITICAL'
        elif summary['health_status']['warning'] > 0 or summary['issues']:
            summary['status'] = 'WARNING'
        else:
            summary['status'] = 'GOOD'

        return summary


def main():
    """Main function for testing the collector."""
    collector = DiskHealthCollector()
    data = collector.collect_all_data()
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()

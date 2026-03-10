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
            print(f"✅ Found {len(self.disks)} disk devices: {', '.join(self.disks)}")

            # Collect data for each disk
            disk_data = []
            for disk in self.disks:
                try:
                    print(f"📊 Collecting data for {disk}...")
                    disk_info = self._collect_disk_data(disk)
                    if disk_info:
                        disk_data.append(disk_info)
                        print(f"✅ Successfully collected data for {disk}")
                    else:
                        print(f"⚠️  No data collected for {disk}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not collect data for disk {disk}: {e}")
                    continue

            # Validate that we have unique data for each disk
            if disk_data:
                self._validate_disk_data_uniqueness(disk_data)

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

                # Handle NVMe devices (e.g., /dev/nvme0n1p1 -> /dev/nvme0n1)
                if 'nvme' in device:
                    # For NVMe, remove the partition number (p1, p2, etc.)
                    if 'p' in device:
                        device = device.split('p')[0]

                # Handle traditional devices (e.g., /dev/sda1 -> /dev/sda)
                else:
                    # Remove trailing digits to get base device name
                    while device and device[-1].isdigit():
                        device = device[:-1]

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
                            # Ensure we get the base device name
                            if 'nvme' in device_name and 'p' in device_name:
                                device_name = device_name.split('p')[0]
                            elif not 'nvme' in device_name:
                                # Remove trailing digits for traditional devices
                                while device_name and device_name[-1].isdigit():
                                    device_name = device_name[:-1]

                            if device_name not in disks:
                                disks.append(device_name)
        except Exception as e:
            print(f"Warning: Could not get additional devices from lsblk: {e}")

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

            # Try to get SMART data without sudo first, then fallback to sudo
            smartctl_commands = [
                ['smartctl', '-H', device],  # Try without sudo first
                ['sudo', 'smartctl', '-H', device]  # Fallback to sudo
            ]

            # Get SMART overall health
            for cmd in smartctl_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        health_output = result.stdout
                        if 'PASSED' in health_output:
                            health_status = 'PASSED'
                            break
                        elif 'FAILED' in health_output:
                            health_status = 'FAILED'
                            break
                        else:
                            health_status = 'UNKNOWN'
                    else:
                        continue  # Try next command
                except Exception:
                    continue  # Try next command

            # Try to get SMART attributes without sudo first, then fallback to sudo
            smartctl_attr_commands = [
                ['smartctl', '-A', device],  # Try without sudo first
                ['sudo', 'smartctl', '-A', device]  # Fallback to sudo
            ]

            for cmd in smartctl_attr_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.strip() and not line.startswith('#') and not line.startswith('ID#'):
                                parts = line.split()
                                if len(parts) >= 10:
                                    try:
                                        attr_id = parts[0]
                                        attr_name = parts[1]
                                        raw_value = parts[-1]
                                        normalized = parts[3] if len(parts) > 3 else 'N/A'
                                        attributes[attr_name] = {
                                            'id': attr_id,
                                            'raw_value': raw_value,
                                            'normalized': normalized
                                        }
                                    except IndexError:
                                        continue
                        break  # Successfully got attributes, exit loop
                    else:
                        continue  # Try next command
                except Exception:
                    continue  # Try next command

            # Try to get device information without sudo first, then fallback to sudo
            smartctl_info_commands = [
                ['smartctl', '-i', device],  # Try without sudo first
                ['sudo', 'smartctl', '-i', device]  # Fallback to sudo
            ]

            for cmd in smartctl_info_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                device_info[key.strip()] = value.strip()
                        break  # Successfully got device info, exit loop
                    else:
                        continue  # Try next command
                except Exception:
                    continue  # Try next command

            return {
                'health_status': health_status,
                'attributes': attributes,
                'device_info': device_info,
                'raw_output_available': True
            }

        except Exception as e:
            return {'error': f'SMART data collection failed for {device}: {str(e)}'}

    def _get_usage_data(self, device: str) -> Dict[str, Any]:
        """Get disk usage information."""
        try:
            # Get disk usage for mounted partitions
            partitions = psutil.disk_partitions()
            usage_data = {}

            for partition in partitions:
                # Check if this partition belongs to our device
                partition_device = partition.device
                if partition_device.startswith(device):
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        usage_data[partition.mountpoint] = {
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0,
                            'fstype': partition.fstype,
                            'mountpoint': partition.mountpoint,
                            'device': partition_device
                        }
                    except PermissionError:
                        continue
                    except Exception as e:
                        print(f"Warning: Could not get usage for {partition.mountpoint}: {e}")
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
            except Exception as e:
                print(f"Warning: Could not get unmounted partitions for {device}: {e}")

            # Get disk I/O counters
            try:
                io_counters = psutil.disk_io_counters(perdisk=True)
                device_name = device.replace('/dev/', '')
                if device_name in io_counters:
                    counter = io_counters[device_name]
                    usage_data['io_counters'] = {
                        'read_count': counter.read_count,
                        'write_count': counter.write_count,
                        'read_bytes': counter.read_bytes,
                        'write_bytes': counter.write_bytes,
                        'read_time': counter.read_time,
                        'write_time': counter.write_time
                    }
            except Exception as e:
                print(f"Warning: Could not get I/O counters for {device}: {e}")

            return usage_data

        except Exception as e:
            return {'error': f'Usage data collection failed for {device}: {str(e)}'}

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
                                temp_str = parts[-1]
                                # Handle cases where temperature might be in hex or have extra characters
                                if temp_str.startswith('0x'):
                                    # Convert hex to decimal
                                    temp_value = int(temp_str, 16)
                                else:
                                    # Try to extract just the number
                                    temp_clean = re.sub(r'[^\d.-]', '', temp_str)
                                    if temp_clean:
                                        temp_value = float(temp_clean)
                                    else:
                                        continue

                                # Validate temperature range (reasonable disk temps are usually 0-80°C)
                                if 0 <= temp_value <= 100:
                                    return temp_value
                            except (ValueError, IndexError):
                                continue

            # Try hddtemp if available
            try:
                result = subprocess.run(['hddtemp', device],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # Parse hddtemp output format: "/dev/sda: KINGSTON SA400S37960G: 35°C"
                    match = re.search(r':\s*(\d+)\s*°C', result.stdout)
                    if match:
                        temp_value = float(match.group(1))
                        if 0 <= temp_value <= 100:
                            return temp_value
            except Exception:
                pass

            return None
        except Exception as e:
            print(f"Warning: Could not get temperature for {device}: {e}")
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
        elif health_status == 'UNKNOWN':
            return 'UNKNOWN'
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

    def _validate_disk_data_uniqueness(self, disk_data: List[Dict[str, Any]]) -> None:
        """Validate that each disk has unique data to detect collection issues."""
        if len(disk_data) <= 1:
            return

        print("🔍 Validating disk data uniqueness...")

        # Check for duplicate temperatures
        temperatures = {}
        for disk in disk_data:
            temp = disk.get('temperature')
            if temp is not None:
                if temp in temperatures:
                    # Only warn if these are actually different devices (not just different partitions)
                    existing_device = temperatures[temp]
                    if disk['device'] != existing_device:
                        print(f"⚠️  Warning: Same temperature ({temp}°C) found for {disk['device']} and {existing_device}")
                else:
                    temperatures[temp] = disk['device']

        # Check for duplicate SMART data patterns
        smart_signatures = {}
        for disk in disk_data:
            smart_data = disk.get('smart_data', {})
            if smart_data and 'device_info' in smart_data:
                device_info = smart_data['device_info']
                model = device_info.get('Device Model', '')
                serial = device_info.get('Serial Number', '')
                signature = f"{model}_{serial}"

                if signature in smart_signatures and signature != '_':
                    existing_device = smart_signatures[signature]
                    if disk['device'] != existing_device:
                        print(f"⚠️  Warning: Similar device info found for {disk['device']} and {existing_device}")
                else:
                    smart_signatures[signature] = disk['device']

        # Check for duplicate usage patterns (this is less critical but helpful)
        usage_signatures = {}
        for disk in disk_data:
            usage_data = disk.get('usage_data', {})
            if usage_data:
                # Create a signature based on usage patterns, but be more lenient
                total_usage = sum(usage.get('percent', 0) for mount, usage in usage_data.items()
                                if isinstance(usage, dict) and 'percent' in usage)
                partition_count = len([u for u in usage_data.values() if isinstance(u, dict) and 'percent' in u])
                signature = f"{partition_count}_partitions_{total_usage:.0f}%"

                if signature in usage_signatures:
                    existing_device = usage_signatures[signature]
                    if disk['device'] != existing_device:
                        # Only warn if the usage is very similar (within 5%)
                        try:
                            existing_parts = usage_signatures[signature].split('_')
                            if len(existing_parts) >= 3:
                                existing_total_str = existing_parts[-1].replace('%', '')
                                existing_total = float(existing_total_str)
                                if abs(total_usage - existing_total) < 5:
                                    print(f"⚠️  Warning: Similar usage pattern found for {disk['device']} and {existing_device}")
                        except (ValueError, IndexError):
                            # Skip validation if we can't parse the existing signature
                            pass
                else:
                    usage_signatures[signature] = disk['device']

        print("✅ Disk data uniqueness validation completed")


def main():
    """Main function for testing the collector."""
    collector = DiskHealthCollector()
    data = collector.collect_all_data()
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()

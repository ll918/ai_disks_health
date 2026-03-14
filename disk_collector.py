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

            # Determine if this is an NVMe drive
            is_nvme = 'nvme' in device.lower()

            # Try to get SMART data with sudo first, then fallback to without sudo
            smartctl_commands = [
                ['sudo', 'smartctl', '-H', device],  # Try with sudo first
                ['smartctl', '-H', device]  # Fallback without sudo
            ]

            # For NVMe drives, use different command format
            if is_nvme:
                smartctl_commands = [
                    ['smartctl', '-H', '-d', 'nvme', device],
                    ['sudo', 'smartctl', '-H', '-d', 'nvme', device]
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
                        elif 'CRITICAL WARNING' in health_output:
                            # For NVMe drives, check for critical warnings
                            health_status = 'CRITICAL'
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

            # For NVMe drives, use different command format
            if is_nvme:
                smartctl_attr_commands = [
                    ['smartctl', '-A', '-d', 'nvme', device],
                    ['sudo', 'smartctl', '-A', '-d', 'nvme', device]
                ]

            for cmd in smartctl_attr_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        # Parse SMART attributes based on drive type
                        if is_nvme:
                            attributes = self._parse_nvme_attributes(result.stdout)
                        else:
                            attributes = self._parse_sata_attributes(result.stdout)
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

            # For NVMe drives, use different command format
            if is_nvme:
                smartctl_info_commands = [
                    ['smartctl', '-i', '-d', 'nvme', device],
                    ['sudo', 'smartctl', '-i', '-d', 'nvme', device]
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

    def _parse_sata_attributes(self, smart_output: str) -> Dict[str, Dict[str, str]]:
        """Parse SMART attributes for SATA drives."""
        attributes = {}
        for line in smart_output.split('\n'):
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
        return attributes

    def _parse_nvme_attributes(self, smart_output: str) -> Dict[str, Dict[str, str]]:
        """Parse SMART attributes for NVMe drives."""
        attributes = {}
        lines = smart_output.split('\n')

        # Look for NVMe-specific attributes
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Parse critical warning
            if 'Critical Warning' in line:
                try:
                    # Extract the hex value - look for pattern like "Critical Warning: 0x00"
                    warning_match = re.search(r'Critical Warning:\s*(0x[0-9a-fA-F]+)', line)
                    if warning_match:
                        attributes['Critical Warning'] = {
                            'id': '0x01',
                            'raw_value': warning_match.group(1),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse temperature
            elif 'Temperature' in line and 'Sensor' in line:
                try:
                    # Look for temperature value in Kelvin or Celsius
                    temp_match = re.search(r'(\d+)\s*(K|°C|C)', line, re.IGNORECASE)
                    if temp_match:
                        temp_value = temp_match.group(1)
                        temp_unit = temp_match.group(2).upper()

                        # Convert Kelvin to Celsius if needed
                        if temp_unit == 'K':
                            temp_c = int(temp_value) - 273
                        else:
                            temp_c = int(temp_value)

                        attributes['Temperature'] = {
                            'id': '0x02',
                            'raw_value': str(temp_c),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse available spare
            elif 'Available Spare' in line:
                try:
                    # Extract percentage value - look for pattern like "Available Spare: 100%"
                    percent_match = re.search(r'Available Spare:\s*(\d+)%', line)
                    if percent_match:
                        attributes['Available Spare'] = {
                            'id': '0x03',
                            'raw_value': percent_match.group(1),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse media and data integrity errors
            elif 'Media and Data Integrity Errors' in line:
                try:
                    # Extract error count - look for pattern like "Media and Data Integrity Errors: 0"
                    error_match = re.search(r'Media and Data Integrity Errors:\s*(\d+)', line)
                    if error_match:
                        attributes['Media and Data Integrity Error Count'] = {
                            'id': '0x04',
                            'raw_value': error_match.group(1),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse error information log entries
            elif 'Error Information Log Entries' in line:
                try:
                    # Extract entry count - look for pattern like "Error Information Log Entries: 0"
                    entry_match = re.search(r'Error Information Log Entries:\s*(\d+)', line)
                    if entry_match:
                        attributes['Error Info Log Entries'] = {
                            'id': '0x05',
                            'raw_value': entry_match.group(1),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse percentage used
            elif 'Percentage Used' in line:
                try:
                    # Extract percentage value - look for pattern like "Percentage Used: 10%"
                    percent_match = re.search(r'Percentage Used:\s*(\d+)%', line)
                    if percent_match:
                        attributes['Percentage Used'] = {
                            'id': '0x06',
                            'raw_value': percent_match.group(1),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse data units read
            elif 'Data Units Read' in line:
                try:
                    # Extract TB value - look for pattern like "Data Units Read: 123,456,789 [62.2 TB]"
                    tb_match = re.search(r'Data Units Read:\s*(\d+),(\d+),(\d+)', line)
                    if tb_match:
                        # Convert to bytes for consistency
                        tb_value = int(tb_match.group(1)) * 1000000000000  # Approximate conversion
                        attributes['Data Units Read'] = {
                            'id': '0x07',
                            'raw_value': str(tb_value),
                            'normalized': 'N/A'
                        }
                except:
                    pass

            # Parse data units written
            elif 'Data Units Written' in line:
                try:
                    # Extract TB value - look for pattern like "Data Units Written: 123,456,789 [62.2 TB]"
                    tb_match = re.search(r'Data Units Written:\s*(\d+),(\d+),(\d+)', line)
                    if tb_match:
                        # Convert to bytes for consistency
                        tb_value = int(tb_match.group(1)) * 1000000000000  # Approximate conversion
                        attributes['Data Units Written'] = {
                            'id': '0x08',
                            'raw_value': str(tb_value),
                            'normalized': 'N/A'
                        }
                except:
                    pass

        return attributes

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
        """Get disk temperature via smartctl --json, with lsblk fallback."""
        try:
            print(f"🔍 Attempting to get temperature for {device}...")

            # Primary: smartctl --json gives us a clean numeric value, no text parsing needed.
            result = subprocess.run(
                ['sudo', 'smartctl', '--json', '-A', device],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)

                    # NVMe: temperature lives at the top level
                    nvme_temp = (data.get('temperature') or {}).get('current')
                    if nvme_temp is not None:
                        temp = float(nvme_temp)
                        if 10 <= temp <= 80:
                            print(f"  ✅ NVMe temperature: {temp}°C")
                            return temp

                    # SATA/SAS: find attribute id 194 (Temperature_Celsius) or 190 (Airflow)
                    for attr in data.get('ata_smart_attributes', {}).get('table', []):
                        if attr.get('id') in (190, 194):
                            temp = float(attr['raw']['value'])
                            if 10 <= temp <= 80:
                                print(f"  ✅ SATA temperature (attr {attr['id']}): {temp}°C")
                                return temp
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"  ⚠️  JSON parse error: {e}")
            else:
                print(f"  ❌ smartctl failed (rc={result.returncode})")

            # Fallback: lsblk --output TEMP
            result = subprocess.run(
                ['lsblk', '-d', '-n', '-o', 'NAME,TEMP', device],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            temp = float(parts[-1])
                            if 0 <= temp <= 100:
                                print(f"  ✅ lsblk temperature: {temp}°C")
                                return temp
                        except ValueError:
                            continue

            print(f"  ❌ No temperature data found for {device}")
            return None

        except Exception as e:
            print(f"❌ Critical error getting temperature for {device}: {e}")
            return None

    def _assess_smart_health(self, smart_data: Dict[str, Any]) -> str:
        """Assess disk health based on SMART data with enhanced NVMe support."""
        if 'error' in smart_data:
            return 'ERROR'

        # First check the overall health status
        health_status = smart_data.get('health_status', 'UNKNOWN')

        # For traditional drives, use the standard logic
        if health_status == 'PASSED':
            return 'GOOD'
        elif health_status == 'FAILED':
            return 'CRITICAL'
        elif health_status == 'UNKNOWN':
            # For UNKNOWN status, analyze individual SMART attributes
            return self._assess_health_from_attributes(smart_data)
        else:
            return 'WARNING'

    def _assess_health_from_attributes(self, smart_data: Dict[str, Any]) -> str:
        """Assess health by analyzing individual SMART attributes when overall status is unknown."""
        attributes = smart_data.get('attributes', {})
        device_info = smart_data.get('device_info', {})

        # Check if this is an NVMe drive
        is_nvme = self._is_nvme_drive(device_info)

        critical_issues = 0
        warning_issues = 0

        # Analyze key SMART attributes for critical issues
        for attr_name, attr_data in attributes.items():
            attr_name_upper = attr_name.upper()
            raw_value = attr_data.get('raw_value', '0')

            # Convert raw value to numeric for analysis
            numeric_value = self._parse_smart_value(raw_value)

            # NVMe-specific critical attributes
            if is_nvme:
                if any(keyword in attr_name_upper for keyword in ['CRITICAL WARNING', 'CRITICAL WARNING']):
                    if numeric_value > 0:
                        critical_issues += 1

                if 'AVAILABLE_SPARE' in attr_name_upper:
                    if numeric_value < 10:  # Less than 10% spare blocks
                        critical_issues += 1

                if 'MEDIA_AND_DATA_INTEGRITY_ERROR_COUNT' in attr_name_upper:
                    if numeric_value > 0:
                        critical_issues += 1

                if 'ERROR_INFO_LOG_ENTRIES' in attr_name_upper:
                    if numeric_value > 0:
                        critical_issues += 1

                if 'WEAR_LEVELING_COUNT' in attr_name_upper or 'PERCENTAGE_USED' in attr_name_upper:
                    if numeric_value > 90:  # Drive is 90% worn
                        critical_issues += 1

                if 'TEMPERATURE' in attr_name_upper:
                    if numeric_value > 70:  # Over 70°C
                        critical_issues += 1
                    elif numeric_value > 55:  # Over 55°C
                        warning_issues += 1

            # Traditional drive critical attributes
            else:
                if any(keyword in attr_name_upper for keyword in ['REALLOCATED_SECTORS', 'REALLOCATED_EVENT_COUNT']):
                    if numeric_value > 0:
                        critical_issues += 1

                if 'READ_ERROR_RATE' in attr_name_upper:
                    # Parse percentage value from strings like "83.9%" or extract from raw value
                    if isinstance(raw_value, str) and '%' in raw_value:
                        try:
                            error_rate = float(raw_value.replace('%', '').strip())
                            if error_rate > 50:  # High error rate
                                critical_issues += 1
                            elif error_rate > 20:  # Moderate error rate
                                warning_issues += 1
                        except ValueError:
                            pass
                    elif numeric_value > 1000:  # High raw error count
                        critical_issues += 1

                if 'WEAR_LEVELING_COUNT' in attr_name_upper or 'WEAR_LEVELING' in attr_name_upper:
                    if numeric_value > 90:  # Drive is 90% worn
                        critical_issues += 1

                if 'TEMPERATURE' in attr_name_upper or 'TEMP' in attr_name_upper:
                    if numeric_value > 60:  # Over 60°C
                        critical_issues += 1
                    elif numeric_value > 45:  # Over 45°C
                        warning_issues += 1

                if 'POWER_ON_HOURS' in attr_name_upper:
                    if numeric_value > 60000:  # Over 60,000 hours (about 7 years)
                        warning_issues += 1

        # Determine health status based on issues found
        if critical_issues > 0:
            return 'CRITICAL'
        elif warning_issues > 0:
            return 'WARNING'
        else:
            return 'GOOD'

    def _is_nvme_drive(self, device_info: Dict[str, str]) -> bool:
        """Check if the device is an NVMe drive."""
        model = device_info.get('Device Model', '').upper()
        return 'NVME' in model or 'SAMSUNG' in model or 'KINGSTON' in model or 'CRUCIAL' in model

    def _parse_smart_value(self, raw_value: str) -> float:
        """Parse SMART attribute raw value to numeric."""
        if not raw_value:
            return 0.0

        # Handle percentage values
        if isinstance(raw_value, str) and '%' in raw_value:
            try:
                return float(raw_value.replace('%', '').strip())
            except ValueError:
                pass

        # Handle hex values
        if isinstance(raw_value, str) and raw_value.startswith('0x'):
            try:
                return float(int(raw_value, 16))
            except ValueError:
                pass

        # Handle comma-separated numbers
        if isinstance(raw_value, str):
            try:
                # Remove commas and convert to float
                clean_value = raw_value.replace(',', '').replace(' ', '')
                return float(clean_value)
            except ValueError:
                pass

        # Try direct conversion
        try:
            return float(raw_value)
        except (ValueError, TypeError):
            return 0.0

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

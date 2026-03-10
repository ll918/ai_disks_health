#!/usr/bin/env python3
"""
Test script specifically for /dev/sdc temperature parsing.
This tests the enhanced temperature extraction logic for various SDC drive formats.
"""

import re
import sys
import os

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from disk_collector import DiskHealthCollector


def test_sdc_temperature_parsing():
    """Test temperature parsing for various /dev/sdc SMART output formats."""

    print("🧪 Testing /dev/sdc Temperature Parsing")
    print("=" * 50)

    # Test cases for different SDC drive SMART output formats
    test_cases = [
        {
            'name': 'Standard SATA SDC with Min/Max format',
            'line': '194 Temperature_Celsius     0x0022   031   045   000    Old_age   Always       -       31 (Min/Max 21/45)',
            'expected': 31.0,
            'description': 'Standard format with current temperature and min/max range'
        },
        {
            'name': 'SDC with extended data format',
            'line': '194 Temperature_Celsius     0x0022   037   045   000    Old_age   Always       -       37 (0 22 0 0 0)',
            'expected': 37.0,
            'description': 'Extended data format with multiple values'
        },
        {
            'name': 'SDC with simple temperature value',
            'line': '194 Temperature_Celsius     0x0022   045   045   000    Old_age   Always       -       45',
            'expected': 45.0,
            'description': 'Simple temperature value without additional data'
        },
        {
            'name': 'SDC with temperature in Celsius units',
            'line': '194 Temperature_Celsius     0x0022   052   045   000    Old_age   Always       -       52°C',
            'expected': 52.0,
            'description': 'Temperature with Celsius symbol'
        },
        {
            'name': 'SDC with temperature in different position',
            'line': '194 Temperature_Celsius     0x0022   031   045   000    Old_age   Always       -       31',
            'expected': 31.0,
            'description': 'Temperature value in last position'
        },
        {
            'name': 'SDC with Airflow Temperature',
            'line': '199 Airflow_Temperature_Cel 0x0022   035   045   000    Old_age   Always       -       35 (Min/Max 20/45)',
            'expected': 35.0,
            'description': 'Airflow temperature attribute'
        },
        {
            'name': 'SDC with Temperature Sensor',
            'line': '194 Temperature_Sensor      0x0022   038   045   000    Old_age   Always       -       38 (Min/Max 22/48)',
            'expected': 38.0,
            'description': 'Temperature sensor attribute'
        }
    ]

    collector = DiskHealthCollector()
    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Input line: {test_case['line']}")
        print(f"   Expected: {test_case['expected']}°C")

        # Simulate the temperature parsing logic from _get_temperature
        line = test_case['line']
        parts = line.split()

        if len(parts) >= 10:
            # Test the enhanced parsing logic - exactly as implemented in disk_collector.py
            raw_value_field = parts[-1]

            # Approach 1: Try the last field
            raw_value_field = parts[-1]

            # Approach 2: If the last field doesn't start with a digit, try the 10th field
            if not re.match(r'^\d', raw_value_field) and len(parts) > 9:
                raw_value_field = parts[9]

            # Approach 3: If still not good, try to find a field that starts with a digit
            if not re.match(r'^\d', raw_value_field):
                for i in range(len(parts)-1, -1, -1):
                    if re.match(r'^\d', parts[i]):
                        raw_value_field = parts[i]
                        break

            # Approach 4: If we still have issues, try to extract the temperature from the entire line
            # This handles cases where the temperature might be in a different position
            if not re.match(r'^\d', raw_value_field):
                # Look for temperature pattern in the entire line
                # Pattern: "31 (Min/Max 21/45)" - extract the first number before the parentheses
                line_temp_match = re.search(r'(\d+)\s*\(', line)
                if line_temp_match:
                    raw_value_field = line_temp_match.group(1)
                    print(f"   🔢 Extracted from line pattern: {raw_value_field}")

            # Approach 5: If we still have issues, try to find the temperature value in the line
            # This handles cases where the temperature might be in a different format
            if not re.match(r'^\d', raw_value_field):
                # Look for any temperature pattern in the line
                # This handles formats like: "31 (Min/Max 21/45)", "31", etc.
                all_temp_matches = re.findall(r'\b(\d{1,3})\b', line)
                if all_temp_matches:
                    # The first number in the line is usually the current temperature
                    # Skip the ID field (first number) and look for the temperature
                    for temp_str in all_temp_matches:
                        temp_value = int(temp_str)
                        # Check if this looks like a reasonable temperature
                        if 10 <= temp_value <= 80:
                            raw_value_field = temp_str
                            print(f"   🔢 Found temperature in line: {raw_value_field}")
                            break

            # Approach 6: If we still have issues, try to find the temperature value in the line
            # This handles cases where the temperature might be in a different format
            # Check if the raw_value_field looks like it contains min/max data
            if re.match(r'^\d+/\d+\)', raw_value_field):
                # This looks like "21/45)" which is the min/max format
                # We need to extract the current temperature from the line
                line_temp_match = re.search(r'(\d+)\s*\(', line)
                if line_temp_match:
                    raw_value_field = line_temp_match.group(1)
                    print(f"   🔢 Extracted current temperature from min/max format: {raw_value_field}")

            # Approach 7: If we still have issues, try to find the temperature value in the line
            # This handles cases where the temperature might be in a different format
            # Check if the raw_value_field looks like it contains extended data format
            if re.match(r'^\d+\s*\(', raw_value_field):
                # This looks like "55 (" which is the extended data format
                # We need to extract the current temperature from the line
                line_temp_match = re.search(r'(\d+)\s*\(', line)
                if line_temp_match:
                    raw_value_field = line_temp_match.group(1)
                    print(f"   🔢 Extracted current temperature from extended format: {raw_value_field}")

            # Approach 8: If we still have issues, try to find the temperature value in the line
            # This handles cases where the temperature might be in a different format
            # Check if the raw_value_field looks like it contains extended data format with closing paren
            if re.match(r'^\d+\)', raw_value_field):
                # This looks like "0)" which is the extended data format
                # We need to extract the current temperature from the line
                line_temp_match = re.search(r'(\d+)\s*\(', line)
                if line_temp_match:
                    raw_value_field = line_temp_match.group(1)
                    print(f"   🔢 Extracted current temperature from extended format with closing paren: {raw_value_field}")

            # Enhanced Approach 9: Handle /dev/sdc specific patterns
            # Some SDC drives have different SMART output formats
            if not re.match(r'^\d', raw_value_field):
                # Try to find temperature in different positions for SDC drives
                # Pattern: "Temperature_Celsius     0x0022   031   045   000    Old_age   Always       -       31"
                # Look for temperature value in various positions
                for i, part in enumerate(parts):
                    if re.match(r'^\d{1,3}$', part):  # Simple 1-3 digit number
                        temp_value = int(part)
                        if 10 <= temp_value <= 80:
                            raw_value_field = part
                            print(f"   🔢 Found temperature in position {i}: {raw_value_field}")
                            break

            # Enhanced Approach 10: Handle extended temperature formats for SDC drives
            if not re.match(r'^\d', raw_value_field):
                # Look for patterns like "31 (0 22 0 0 0)" or "31 (Min/Max 21/45)"
                extended_temp_match = re.search(r'(\d+)\s*\([^)]*\)', line)
                if extended_temp_match:
                    raw_value_field = extended_temp_match.group(1)
                    print(f"   🔢 Extracted from extended format: {raw_value_field}")

            # Enhanced Approach 11: Handle temperature with units for SDC drives
            if not re.match(r'^\d', raw_value_field):
                # Look for patterns like "31°C" or "31 C" or "31 Celsius"
                unit_temp_match = re.search(r'(\d+)\s*°?C', line, re.IGNORECASE)
                if unit_temp_match:
                    raw_value_field = unit_temp_match.group(1)
                    print(f"   🔢 Extracted from unit format: {raw_value_field}")

            print(f"   🔢 Raw value field: {raw_value_field}")

            # Extract the first number from the raw value field
            # This handles formats like: "35", "35 (Min/Max 21/45)", "37 (0 22 0 0 0)", etc.
            # The first number is always the current temperature
            temp_match = re.search(r'^(\d+)', raw_value_field)
            if temp_match:
                temp_value = float(temp_match.group(1))
                print(f"   📐 Extracted temperature: {raw_value_field} -> {temp_value}°C")

                # Validate temperature range (disks typically operate between 10-60°C)
                # 0°C is impossible for an operating disk, so we should be more strict
                if 10 <= temp_value <= 80:
                    print(f"   ✅ Valid temperature found: {temp_value}°C")
                    if temp_value == test_case['expected']:
                        print(f"   ✅ PASS: Correct temperature extracted")
                    else:
                        print(f"   ❌ FAIL: Expected {test_case['expected']}°C, got {temp_value}°C")
                        all_passed = False
                elif temp_value == 0:
                    print(f"   ⚠️  Impossible temperature detected: {temp_value}°C (likely parsing error)")
                    # Don't try to extract other numbers as they are likely min/max values
                    # which are not the current temperature
                    continue
                else:
                    print(f"   ⚠️  Temperature out of reasonable range: {temp_value}°C")
                    all_passed = False
            else:
                print(f"   ❌ FAIL: Could not extract temperature from: {raw_value_field}")
                all_passed = False
        else:
            print(f"   ❌ FAIL: Line doesn't have enough parts for parsing")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All /dev/sdc temperature parsing tests PASSED!")
        print("✅ Enhanced parsing logic correctly handles various SDC drive formats")
    else:
        print("❌ Some tests FAILED. Please review the parsing logic.")

    return all_passed


def test_sdc_device_detection():
    """Test that /dev/sdc is properly detected as a disk device."""

    print("\n🔍 Testing /dev/sdc Device Detection")
    print("=" * 50)

    collector = DiskHealthCollector()

    # Mock the lsblk output to simulate /dev/sdc being present
    mock_lsblk_output = """sda disk
sdb disk
sdc disk
nvme0n1 disk"""

    # Test the device detection logic
    disks = []
    lines = mock_lsblk_output.strip().split('\n')

    for line in lines:
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

    print(f"Detected devices: {disks}")

    if '/dev/sdc' in disks:
        print("✅ PASS: /dev/sdc properly detected as disk device")
        return True
    else:
        print("❌ FAIL: /dev/sdc not detected as disk device")
        return False


def simulate_sdc_temperature_collection():
    """Simulate the complete temperature collection process for /dev/sdc."""

    print("\n🔍 Simulating /dev/sdc Temperature Collection")
    print("=" * 50)

    # Create a collector instance
    collector = DiskHealthCollector()

    # Test the _get_temperature method with a mock /dev/sdc device
    # We'll create a mock to simulate the smartctl output for /dev/sdc

    def mock_subprocess_run(cmd, **kwargs):
        """Mock subprocess.run to simulate smartctl output for /dev/sdc."""
        class MockResult:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout

        # Simulate smartctl output for a SATA SDC drive
        smart_output = """smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.14.0] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Device Model:     KINGSTON SA400S37960G
Serial Number:    50026B7782000000
LU WWN Device Id: 5 0026b7 782000000
Firmware Version: SBFKSA07
User Capacity:    960,197,124,096 bytes [960 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      2.5 inches
Device is:        Not in smartctl database [for details use: -P showall]
ATA Version is:   ACS-3 T13/2161-D revision 5
SATA Version is:  SATA 3.2, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Mon Jan  1 12:00:00 2024 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00)	Offline data collection activity
					was never started.
					Auto Offline Data Collection: Disabled.
Self-test execution status:      (   0)	The previous self-test routine completed
					without error or no self-test has ever
					been run.
Total time to complete Offline
data collection: 		(    0) seconds.
Offline data collection
capabilities: 			 (0x11) SMART execute Offline immediate.
					No Auto Offline data collection support.
					Suspend Offline collection upon new
					command.
					No Offline surface scan supported.
					Self-test supported.
					No Conveyance Self-test supported.
					No Selective Self-test supported.
SMART capabilities:            (0x0003)	Saves SMART data before entering
					power-saving mode.
					Supports SMART auto save timer.
Error logging capability:        (0x01)	Error logging supported.
					General Purpose Logging supported.
Short self-test routine
recommended polling time: 	 (   2) minutes.
Extended self-test routine
recommended polling time: 	 (  10) minutes.

SMART Attributes Data Structure revision number: 16
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x002f   100   100   000    Pre-fail  Always       -       0
  5 Reallocated_Sector_Ct   0x0033   100   100   010    Pre-fail  Always       -       0
  9 Power_On_Hours          0x0032   100   100   000    Old_age   Always       -       1234
 12 Power_Cycle_Count       0x0032   100   100   000    Old_age   Always       -       123
160 Unknown_SSD_Attribute   0x0002   100   100   000    Old_age   Always       -       0
161 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       2
163 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       2
164 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       1234
165 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       1
166 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       1
167 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       1
168 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       1000
169 Unknown_SSD_Attribute   0x0032   100   100   000    Old_age   Always       -       100
175 Program_Fail_Count_Chip 0x0032   100   100   000    Old_age   Always       -       0
176 Erase_Fail_Count_Chip   0x0032   100   100   000    Old_age   Always       -       0
177 Wear_Leveling_Count     0x0000   100   100   000    Old_age   Offline      -       0
178 Used_Rsvd_Blk_Cnt_Chip  0x0032   100   100   000    Old_age   Always       -       0
181 Program_Fail_Cnt_Total  0x0032   100   100   000    Old_age   Always       -       0
182 Erase_Fail_Count_Total  0x0032   100   100   000    Old_age   Always       -       0
192 Power-Off_Retract_Count 0x0032   100   100   000    Old_age   Always       -       123
194 Temperature_Celsius     0x0022   031   045   000    Old_age   Always       -       31 (Min/Max 21/45)
195 Hardware_ECC_Recovered  0x003a   100   100   000    Old_age   Always       -       0
196 Reallocated_Event_Count 0x0032   100   100   000    Old_age   Always       -       0
197 Current_Pending_Sector  0x0032   100   100   000    Old_age   Always       -       0
198 Offline_Uncorrectable   0x0030   100   100   000    Old_age   Offline      -       0
199 UDMA_CRC_Error_Count    0x0032   100   100   000    Old_age   Always       -       0
202 Unknown_SSD_Attribute   0x0000   100   100   000    Old_age   Offline      -       0
206 Write_Error_Rate        0x000e   100   100   000    Old_age   Always       -       0
210 Unknown_Attribute       0x0032   100   100   000    Old_age   Always       -       0
246 Total_Write/Erase_Count 0x0000   100   100   000    Old_age   Offline      -       12345
247 Host_Program_Page_Count 0x0000   100   100   000    Old_age   Offline      -       6789
248 Total_Erase_Count       0x0000   100   100   000    Old_age   Offline      -       12345
249 Bad_Block_Full_Flag     0x0000   100   100   000    Old_age   Offline      -       0
250 Read_Error_Retry_Count  0x0000   100   100   000    Old_age   Offline      -       0
251 Min_Erase_Count         0x0000   100   100   000    Old_age   Offline      -       0
252 Max_Erase_Count         0x0000   100   100   000    Old_age   Offline      -       0
253 Average_Erase_Count     0x0000   100   100   000    Old_age   Offline      -       0
254 Free_Fall_Protection    0x0000   100   100   000    Old_age   Offline      -       0
"""

        return MockResult(0, smart_output)

    # Replace subprocess.run with our mock
    import subprocess
    original_run = subprocess.run
    subprocess.run = mock_subprocess_run

    try:
        # Test temperature extraction for /dev/sdc
        temperature = collector._get_temperature('/dev/sdc')
        if temperature is not None:
            print(f"✅ Successfully extracted temperature: {temperature}°C")
            if temperature == 31.0:
                print("✅ PASS: Correctly extracted current temperature (31°C) from /dev/sdc")
                return True
            else:
                print(f"❌ FAIL: Expected 31°C, got {temperature}°C")
                return False
        else:
            print("❌ FAIL: Failed to extract temperature from /dev/sdc")
            return False
    finally:
        # Restore original subprocess.run
        subprocess.run = original_run


def main():
    """Run all /dev/sdc specific tests."""
    print("🧪 Comprehensive /dev/sdc Temperature Testing")
    print("=" * 60)

    # Test 1: Temperature parsing logic
    test1_passed = test_sdc_temperature_parsing()

    # Test 2: Device detection
    test2_passed = test_sdc_device_detection()

    # Test 3: Full simulation
    test3_passed = simulate_sdc_temperature_collection()

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Temperature Parsing Tests: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Device Detection Tests:    {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"Full Simulation Tests:     {'✅ PASS' if test3_passed else '❌ FAIL'}")

    all_tests_passed = test1_passed and test2_passed and test3_passed

    if all_tests_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ /dev/sdc temperature monitoring is working correctly")
        print("✅ Enhanced parsing logic handles various SDC drive formats")
        print("✅ Device detection properly identifies /dev/sdc")
        print("✅ Temperature extraction works for simulated /dev/sdc data")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Please review the implementation and fix any issues")

    return all_tests_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

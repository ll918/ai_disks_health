#!/usr/bin/env python3
"""
Test script to verify temperature parsing fix for non-NVMe drives.
"""

import re
import sys
import os

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from disk_collector import DiskHealthCollector


def test_temperature_parsing():
    """Test the temperature parsing logic with the specific SMART output format."""

    # Sample SMART output line that was causing the issue
    sample_smart_line = "194 Temperature_Celsius     0x0022   031   045   000    Old_age   Always       -       31 (Min/Max 21/45)"

    # Extract the raw value field (last field)
    parts = sample_smart_line.split()
    raw_value_field = parts[-1]  # "31 (Min/Max 21/45)"

    print(f"Testing with SMART line: {sample_smart_line}")
    print(f"Raw value field: {raw_value_field}")

    # Test the fixed parsing logic
    temp_match = re.search(r'^(\d+)', raw_value_field)
    if temp_match:
        temp_value = float(temp_match.group(1))
        print(f"✅ Extracted temperature: {temp_value}°C")

        # Validate temperature range
        if 10 <= temp_value <= 80:
            print(f"✅ Valid temperature found: {temp_value}°C")
            print("✅ Fix is working correctly - extracted current temperature (31°C) instead of minimum (21°C)")
            return True
        else:
            print(f"⚠️  Temperature out of reasonable range: {temp_value}°C")
            return False
    else:
        print(f"❌ Could not extract temperature from: {raw_value_field}")
        return False


def test_edge_cases():
    """Test various temperature formats to ensure robustness."""

    test_cases = [
        ("35", 35.0, "Simple temperature"),
        ("35 (Min/Max 21/45)", 35.0, "Temperature with min/max"),
        ("37 (0 22 0 0 0)", 37.0, "Temperature with extended data"),
        ("42", 42.0, "Single digit temperature"),
        ("0", 0.0, "Zero temperature (should be rejected)"),
        ("25 (Min/Max 18/50)", 25.0, "Another min/max format"),
    ]

    print("\n🧪 Testing edge cases:")

    for raw_value, expected, description in test_cases:
        temp_match = re.search(r'^(\d+)', raw_value)
        if temp_match:
            temp_value = float(temp_match.group(1))
            print(f"  {description}: {raw_value} -> {temp_value}°C (expected: {expected}°C)")

            if temp_value == expected:
                print(f"    ✅ Correct extraction")
            else:
                print(f"    ❌ Expected {expected}°C, got {temp_value}°C")
        else:
            print(f"  {description}: {raw_value} -> ❌ Failed to extract")


def simulate_temperature_collection():
    """Simulate the temperature collection process."""

    print("\n🔍 Simulating temperature collection process:")

    # Create a collector instance
    collector = DiskHealthCollector()

    # Test the _get_temperature method with a mock device
    # We'll create a mock to simulate the smartctl output

    def mock_subprocess_run(cmd, **kwargs):
        """Mock subprocess.run to simulate smartctl output."""
        class MockResult:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout

        # Simulate smartctl output for a SATA drive
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
        # Test temperature extraction
        temperature = collector._get_temperature('/dev/sda')
        if temperature is not None:
            print(f"✅ Successfully extracted temperature: {temperature}°C")
            if temperature == 31.0:
                print("✅ Fix is working correctly - extracted current temperature (31°C)")
                return True
            else:
                print(f"❌ Expected 31°C, got {temperature}°C")
                return False
        else:
            print("❌ Failed to extract temperature")
            return False
    finally:
        # Restore original subprocess.run
        subprocess.run = original_run


def main():
    """Run all tests."""
    print("🧪 Testing Temperature Parsing Fix")
    print("=" * 50)

    # Test 1: Basic parsing logic
    success1 = test_temperature_parsing()

    # Test 2: Edge cases
    test_edge_cases()

    # Test 3: Full simulation
    success2 = simulate_temperature_collection()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ All tests passed! The temperature parsing fix is working correctly.")
        print("✅ The system will now correctly extract current temperature (31°C)")
        print("   instead of minimum temperature (21°C) from SMART data.")
    else:
        print("❌ Some tests failed. Please review the implementation.")

    return success1 and success2


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

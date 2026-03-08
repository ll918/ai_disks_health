#!/usr/bin/env python3
"""
Disk Health Report Generator

This module formats and displays disk health analysis results in a user-friendly
text format with clear sections and actionable information.
"""

import json
import pytz
import re
from typing import Dict, Any, List
from datetime import datetime


class ReportGenerator:
    """Generates formatted reports from disk health analysis data."""

    def __init__(self):
        self.colors = self._get_color_codes()

    def _bytes_to_human_readable(self, bytes_value: int) -> str:
        """
        Convert bytes to human-readable format (GB, TB, etc.).

        Args:
            bytes_value (int): Size in bytes

        Returns:
            str: Human-readable size string
        """
        if bytes_value is None or bytes_value == 0:
            return "0 B"

        # Handle string input that might contain bytes
        if isinstance(bytes_value, str):
            # Try to extract numeric value from strings like "1,000,204,886,016 bytes"
            import re
            numeric_match = re.search(r'(\d{1,3}(?:,\d{3})*)', bytes_value.replace(',', ''))
            if numeric_match:
                try:
                    bytes_value = int(numeric_match.group(1).replace(',', ''))
                except ValueError:
                    return bytes_value  # Return original string if conversion fails
            else:
                return bytes_value  # Return original string if no numeric value found

        # Convert to integer if it's a float
        bytes_value = int(bytes_value)

        if bytes_value >= 1024**4:  # TB
            return f"{bytes_value / (1024**4):.2f} TB"
        elif bytes_value >= 1024**3:  # GB
            return f"{bytes_value / (1024**3):.2f} GB"
        elif bytes_value >= 1024**2:  # MB
            return f"{bytes_value / (1024**2):.2f} MB"
        elif bytes_value >= 1024:  # KB
            return f"{bytes_value / 1024:.2f} KB"
        else:  # Bytes
            return f"{bytes_value} B"

    def generate_report(self, analysis_data: Dict[str, Any], verbose: bool = False) -> str:
        """
        Generate a formatted report from analysis data.

        Args:
            analysis_data (Dict[str, Any]): AI analysis results
            verbose (bool): Whether to include detailed information

        Returns:
            str: Formatted report text
        """
        report_lines = []

        # Header
        report_lines.append(self._generate_header(analysis_data))
        report_lines.append("")

        # Storage Configuration
        report_lines.append(self._generate_storage_configuration(analysis_data))
        report_lines.append("")

        # Detailed Analysis
        if verbose:
            report_lines.append(self._generate_detailed_analysis(analysis_data))
            report_lines.append("")

        # Footer
        report_lines.append(self._generate_footer(analysis_data))

        return "\n".join(report_lines)

    def _generate_header(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the report header."""
        header_lines = []
        header_lines.append("=" * 80)
        header_lines.append("🔍 AI DISK HEALTH DIAGNOSTIC REPORT")
        header_lines.append("=" * 80)

        # Basic information
        model_used = analysis_data.get('model_used', 'Unknown')
        timestamp = analysis_data.get('timestamp', 'Unknown')

        # Convert timestamp to local time if it's a valid datetime string
        local_time = self._convert_to_local_time(timestamp)

        header_lines.append(f"Analysis Model: {model_used}")
        header_lines.append(f"Generated: {local_time}")

        if 'original_data_reference' in analysis_data:
            ref = analysis_data['original_data_reference']
            collection_time = ref.get('collection_time', 'Unknown')
            local_collection_time = self._convert_to_local_time(collection_time)
            header_lines.append(f"Disks Analyzed: {ref.get('total_disks', 'Unknown')}")
            header_lines.append(f"Data Collected: {local_collection_time}")

        # Add AI analysis timing if available
        if 'ai_analysis_time' in analysis_data:
            ai_time_seconds = analysis_data['ai_analysis_time']
            minutes = int(ai_time_seconds // 60)
            seconds = int(ai_time_seconds % 60)
            header_lines.append(f"AI Analysis Time: {minutes} min {seconds} sec")

        return "\n".join(header_lines)

    def _convert_to_local_time(self, timestamp: str) -> str:
        """Convert timestamp to local time (America/Toronto)."""
        try:
            # Parse the timestamp string
            if isinstance(timestamp, str):
                # Handle different timestamp formats
                if 'T' in timestamp:
                    # ISO format: 2024-01-01T12:00:00 or 2024-01-01T12:00:00Z or 2024-01-01T12:00:00+00:00
                    if timestamp.endswith('Z'):
                        # UTC timestamp with 'Z' suffix
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    elif '+' in timestamp or timestamp.count(':') > 1:
                        # Timestamp with timezone offset
                        dt = datetime.fromisoformat(timestamp)
                    else:
                        # Naive timestamp (no timezone info) - assume it's already local time
                        dt = datetime.fromisoformat(timestamp)
                else:
                    # Try other common formats
                    dt = datetime.fromisoformat(timestamp)
            else:
                return str(timestamp)

            # Convert to local timezone (America/Toronto)
            local_tz = pytz.timezone('America/Toronto')

            if dt.tzinfo is None:
                # If no timezone info, assume it's already local time (not UTC)
                # Just localize it to the local timezone for consistent formatting
                dt = local_tz.localize(dt)
            else:
                # If timezone info exists, convert to local time
                dt = dt.astimezone(local_tz)

            # Format with timezone info
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

        except Exception:
            # If conversion fails, return original timestamp
            return timestamp

    def _generate_executive_summary(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the executive summary section."""
        summary_lines = []
        summary_lines.append("📋 EXECUTIVE SUMMARY")
        summary_lines.append("-" * 40)

        # Get summary data
        summary = analysis_data.get('summary', {})
        risk_level = analysis_data.get('risk_level', 'Unknown')
        health_assessment = analysis_data.get('health_assessment', {})

        # Overall status with color coding
        health_status = summary.get('health_status', 'Unknown')
        system_rating = health_assessment.get('system_rating', 'Unknown')
        confidence = health_assessment.get('confidence', summary.get('confidence', 'Unknown'))

        status_color = self._get_status_color(health_status)

        summary_lines.append(f"Overall Health Status: {status_color}{health_status}{self.colors['reset']}")
        summary_lines.append(f"System Health Rating: {self._get_rating_color(system_rating)}{system_rating}{self.colors['reset']}")
        summary_lines.append(f"Analysis Confidence: {self._get_confidence_color(confidence)}{confidence}{self.colors['reset']}")

        # Key metrics
        critical_issues = health_assessment.get('critical_issues', summary.get('critical_issues', 0))
        total_recommendations = summary.get('total_recommendations', 0)
        # Get the correct disk count from original data reference instead of AI-extracted value
        disks_analyzed = analysis_data.get('original_data_reference', {}).get('total_disks', 'Unknown')

        summary_lines.append(f"Disks Analyzed: {self.colors['cyan']}{disks_analyzed}{self.colors['reset']}")
        summary_lines.append(f"Critical Issues: {self.colors['red']}{critical_issues}{self.colors['reset']}")
        summary_lines.append(f"Recommendations: {self.colors['blue']}{total_recommendations}{self.colors['reset']}")

        return "\n".join(summary_lines)

    def _generate_storage_configuration(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the storage configuration section."""
        config_lines = []
        config_lines.append("💾 STORAGE CONFIGURATION")
        config_lines.append("-" * 40)

        # Get device information from technical metrics or original data
        technical_metrics = analysis_data.get('technical_metrics', {})
        original_data_ref = analysis_data.get('original_data_reference', {})

        # Try to get device info from technical metrics
        smart_status = technical_metrics.get('smart_status', {})
        temperature_analysis = technical_metrics.get('temperature_analysis', {})
        device_models = technical_metrics.get('device_models', {})
        disk_capacities = technical_metrics.get('disk_capacities', {})
        filesystem_types = technical_metrics.get('filesystem_types', {})

        # If we have device info from technical metrics, use it
        if smart_status:
            # Create a unified device information structure
            all_devices = set(smart_status.keys())
            all_devices.update(temperature_analysis.keys())
            all_devices.update(device_models.keys())
            all_devices.update(disk_capacities.keys())
            all_devices.update(filesystem_types.keys())

            # Sort devices for consistent output
            sorted_devices = sorted(all_devices)

            for device in sorted_devices:
                config_lines.append(f"Device: {device}")

                # Add SMART Status
                if device in smart_status:
                    # Clean up SMART status to remove any trailing text
                    smart_status_clean = smart_status[device]
                    if "The disks are currently operating within acceptable parameters" in smart_status_clean:
                        # Extract just the status part
                        smart_status_clean = smart_status_clean.replace(" - The disks are currently operating within acceptable parameters", "")
                    config_lines.append(f"  SMART Status: {smart_status_clean}")

                # Add device model if available
                if device in device_models and device_models[device] != 'Unknown':
                    config_lines.append(f"  Model: {device_models[device]}")

                # Add disk capacity if available (convert to human-readable format)
                if device in disk_capacities and disk_capacities[device] != 'Unknown':
                    # Try to convert capacity to human-readable format
                    human_readable_capacity = self._bytes_to_human_readable(disk_capacities[device])
                    config_lines.append(f"  Capacity: {human_readable_capacity}")

                # Add temperature if available
                if device in temperature_analysis:
                    temp_info = temperature_analysis[device]
                    # Clean up temperature info to remove any trailing text
                    if "The disks are currently operating within acceptable parameters" in temp_info:
                        temp_info = temp_info.replace(" - The disks are currently operating within acceptable parameters", "")
                    config_lines.append(f"  Temperature: {temp_info}")

                # Add filesystem type if available
                if device in filesystem_types and filesystem_types[device] != 'Unknown':
                    config_lines.append(f"  Filesystem: {filesystem_types[device]}")

                config_lines.append("")

            # Add summary text at the end of the section
            config_lines.append("The disks are currently operating within acceptable parameters.")
        else:
            # Enhanced fallback: Try to extract device info from the AI analysis text
            analysis_text = analysis_data.get('analysis', '')
            if analysis_text:
                # Look for device information in the analysis text
                device_info = self._extract_device_info_from_analysis(analysis_text)
                if device_info:
                    for device, info in device_info.items():
                        config_lines.append(f"Device: {device}")
                        if 'model' in info and info['model'] != 'Unknown':
                            config_lines.append(f"  Model: {info['model']}")
                        if 'capacity' in info and info['capacity'] != 'Unknown':
                            config_lines.append(f"  Capacity: {info['capacity']}")
                        if 'status' in info:
                            config_lines.append(f"  Status: {info['status']}")
                        if 'temperature' in info:
                            config_lines.append(f"  Temperature: {info['temperature']}")
                        config_lines.append("")
                else:
                    # Final fallback to showing basic disk count
                    disks_analyzed = original_data_ref.get('total_disks', 'Unknown')
                    config_lines.append(f"Total Disks: {disks_analyzed}")
                    config_lines.append("Device details not available in this analysis")
            else:
                # Final fallback to showing basic disk count
                disks_analyzed = original_data_ref.get('total_disks', 'Unknown')
                config_lines.append(f"Total Disks: {disks_analyzed}")
                config_lines.append("Device details not available in this analysis")

        return "\n".join(config_lines)

    def _extract_device_info_from_analysis(self, analysis_text: str) -> Dict[str, Dict[str, str]]:
        """Extract device information from AI analysis text."""
        device_info = {}
        lines = analysis_text.split('\n')

        current_device = None

        for line in lines:
            line = line.strip()

            # Look for device identifiers
            if '/dev/' in line and ('DISK' in line.upper() or 'DEVICE' in line.upper()):
                device_match = re.search(r'/dev/[^,\s]+', line)
                if device_match:
                    current_device = device_match.group(0)
                    if current_device not in device_info:
                        device_info[current_device] = {}

            # Extract model information
            if current_device and ('model:' in line.lower() or 'device model:' in line.lower()):
                model_match = re.search(r'(?:model|device model):\s*([^,\n]+)', line, re.IGNORECASE)
                if model_match:
                    device_info[current_device]['model'] = model_match.group(1).strip()

            # Extract capacity information
            if current_device and ('capacity:' in line.lower() or 'size:' in line.lower()):
                capacity_match = re.search(r'(?:capacity|size):\s*([^,\n]+)', line, re.IGNORECASE)
                if capacity_match:
                    device_info[current_device]['capacity'] = capacity_match.group(1).strip()

            # Extract status information
            if current_device and ('status:' in line.lower() or 'health status:' in line.lower()):
                status_match = re.search(r'(?:status|health status):\s*([^,\n]+)', line, re.IGNORECASE)
                if status_match:
                    device_info[current_device]['status'] = status_match.group(1).strip()

            # Extract temperature information
            if current_device and 'temperature:' in line.lower():
                temp_match = re.search(r'temperature:\s*([^,\n]+)', line, re.IGNORECASE)
                if temp_match:
                    device_info[current_device]['temperature'] = temp_match.group(1).strip()

        return device_info

    def _generate_detailed_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the detailed analysis section."""
        detail_lines = []
        detail_lines.append("🔍 DETAILED ANALYSIS")
        detail_lines.append("-" * 40)

        # Include the full AI analysis
        analysis_text = analysis_data.get('analysis', '')
        if analysis_text:
            detail_lines.append("AI Analysis Results:")
            detail_lines.append("")
            # Format the analysis text with proper indentation
            for line in analysis_text.split('\n'):
                if line.strip():
                    detail_lines.append(f"  {line}")

        return "\n".join(detail_lines)

    def _generate_recommendations(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the recommendations section."""
        rec_lines = []
        rec_lines.append("💡 RECOMMENDATIONS")
        rec_lines.append("-" * 40)

        # Get recommendations from analysis
        recommendations = analysis_data.get('recommendations', [])

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                # Clean up the recommendation text
                clean_rec = rec.strip().lstrip('0123456789.-*• ').strip()
                rec_lines.append(f"{i}. {clean_rec}")
        else:
            rec_lines.append("No specific recommendations available.")
            rec_lines.append("Please review the detailed analysis above.")

        return "\n".join(rec_lines)

    def _generate_footer(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the report footer."""
        footer_lines = []
        footer_lines.append("=" * 80)
        footer_lines.append("⚠️  IMPORTANT NOTES")
        footer_lines.append("-" * 40)
        footer_lines.append("• This analysis is generated by AI and should be used as a guide")
        footer_lines.append("• Always verify critical issues with additional diagnostic tools")
        footer_lines.append("• Regular monitoring is recommended for optimal disk health")
        footer_lines.append("• Consider professional consultation for critical disk issues")
        footer_lines.append("=" * 80)

        return "\n".join(footer_lines)

    def _get_color_codes(self) -> Dict[str, str]:
        """Get ANSI color codes for terminal output."""
        return {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }

    def _get_status_color(self, status: str) -> str:
        """Get color code based on health status."""
        status = status.lower()
        if status in ['good', 'healthy']:
            return self.colors['green']
        elif status in ['warning', 'caution']:
            return self.colors['yellow']
        elif status in ['critical', 'failed']:
            return self.colors['red']
        else:
            return self.colors['white']

    def _get_risk_color(self, risk: str) -> str:
        """Get color code based on risk level."""
        risk = risk.lower()
        if risk == 'low':
            return self.colors['green']
        elif risk == 'medium':
            return self.colors['yellow']
        elif risk == 'high':
            return self.colors['red']
        else:
            return self.colors['white']

    def _get_rating_color(self, rating: str) -> str:
        """Get color code based on system health rating."""
        rating = rating.lower()
        if rating in ['excellent', 'good']:
            return self.colors['green']
        elif rating == 'fair':
            return self.colors['yellow']
        elif rating in ['poor', 'critical']:
            return self.colors['red']
        else:
            return self.colors['white']

    def _get_confidence_color(self, confidence: str) -> str:
        """Get color code based on analysis confidence."""
        confidence = confidence.lower()
        if confidence == 'high':
            return self.colors['green']
        elif confidence == 'medium':
            return self.colors['yellow']
        elif confidence == 'low':
            return self.colors['red']
        else:
            return self.colors['white']

    def save_report_to_file(self, report_text: str, filename: str | None = None) -> str | None:
        """
        Save the report to a file.

        Args:
            report_text (str): The formatted report text
            filename (str): Optional filename (auto-generated if not provided)

        Returns:
            str | None: Path to the saved file, or None if failed
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"disk_health_report_{timestamp}.txt"

        try:
            with open(filename, 'w') as f:
                f.write(report_text)
            return filename
        except Exception as e:
            print(f"❌ Failed to save report to {filename}: {e}")
            return None

    def print_json_output(self, analysis_data: Dict[str, Any]) -> None:
        """Print analysis data in JSON format."""
        print(json.dumps(analysis_data, indent=2, default=str))


def main():
    """Main function for testing the report generator."""
    # Sample analysis data
    sample_data = {
        'timestamp': '2024-01-01T12:00:00',
        'model_used': 'gemma3:1b',
        'summary': {
            'health_status': 'WARNING',
            'confidence': 'High',
            'critical_issues': 1,
            'total_recommendations': 5
        },
        'risk_level': 'Medium',
        'recommendations': [
            "1. Monitor disk temperatures regularly",
            "2. Check SMART data weekly for early warning signs",
            "3. Consider replacing disks showing critical SMART errors"
        ],
        'analysis': "The disk shows signs of elevated temperature and some SMART attribute warnings...",
        'original_data_reference': {
            'total_disks': 2,
            'collection_time': '2024-01-01T11:30:00'
        }
    }

    generator = ReportGenerator()

    # Generate and print text report
    report = generator.generate_report(sample_data, verbose=True)
    print(report)

    # Save to file
    filename = generator.save_report_to_file(report)
    if filename:
        print(f"\n📄 Report saved to: {filename}")


if __name__ == '__main__':
    main()

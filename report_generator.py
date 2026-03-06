#!/usr/bin/env python3
"""
Disk Health Report Generator

This module formats and displays disk health analysis results in a user-friendly
text format with clear sections and actionable information.
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class ReportGenerator:
    """Generates formatted reports from disk health analysis data."""

    def __init__(self):
        self.colors = self._get_color_codes()

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

        # Executive Summary
        report_lines.append(self._generate_executive_summary(analysis_data))
        report_lines.append("")

        # Detailed Analysis
        if verbose:
            report_lines.append(self._generate_detailed_analysis(analysis_data))
            report_lines.append("")

        # Recommendations
        report_lines.append(self._generate_recommendations(analysis_data))
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

        header_lines.append(f"Analysis Model: {model_used}")
        header_lines.append(f"Generated: {timestamp}")

        if 'original_data_reference' in analysis_data:
            ref = analysis_data['original_data_reference']
            header_lines.append(f"Disks Analyzed: {ref.get('total_disks', 'Unknown')}")
            header_lines.append(f"Data Collected: {ref.get('collection_time', 'Unknown')}")

        return "\n".join(header_lines)

    def _generate_executive_summary(self, analysis_data: Dict[str, Any]) -> str:
        """Generate the executive summary section."""
        summary_lines = []
        summary_lines.append("📋 EXECUTIVE SUMMARY")
        summary_lines.append("-" * 40)

        # Get summary data
        summary = analysis_data.get('summary', {})
        risk_level = analysis_data.get('risk_level', 'Unknown')

        # Overall status with color coding
        health_status = summary.get('health_status', 'Unknown')
        status_color = self._get_status_color(health_status)

        summary_lines.append(f"Overall Health Status: {status_color}{health_status}{self.colors['reset']}")
        summary_lines.append(f"Risk Level: {self._get_risk_color(risk_level)}{risk_level}{self.colors['reset']}")
        summary_lines.append(f"Analysis Confidence: {summary.get('confidence', 'Unknown')}")

        # Key metrics
        critical_issues = summary.get('critical_issues', 0)
        total_recommendations = summary.get('total_recommendations', 0)

        summary_lines.append(f"Critical Issues: {self.colors['red']}{critical_issues}{self.colors['reset']}")
        summary_lines.append(f"Recommendations: {self.colors['blue']}{total_recommendations}{self.colors['reset']}")

        return "\n".join(summary_lines)

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

    def save_report_to_file(self, report_text: str, filename: str = None) -> str | None:
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
        'model_used': 'gemma3:4b',
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

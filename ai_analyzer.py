#!/usr/bin/env python3
"""
AI Disk Health Analyzer

This module uses Ollama's LLM to analyze disk health data and generate
comprehensive diagnostic reports with actionable recommendations.
"""

import json
import ollama
import time
import re
from typing import Dict, Any, Optional, List
from datetime import datetime


class AIDiskAnalyzer:
    """Analyzes disk health data using AI and generates diagnostic reports."""

    def __init__(self, model: str = "gemma3:1b"):
        """
        Initialize the AI analyzer.

        Args:
            model (str): The Ollama model to use for analysis
        """
        self.model = model
        self.client = None

    def analyze_disk_health(self, disk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze disk health data using AI and generate a comprehensive report.

        Args:
            disk_data (Dict[str, Any]): Collected disk health data

        Returns:
            Dict[str, Any]: AI-generated analysis and recommendations
        """
        print("🤖 Analyzing disk health with AI...")

        try:
            # Check if Ollama is available
            if not self._check_ollama_availability():
                return {
                    'error': 'Ollama service not available',
                    'fallback_analysis': self._generate_fallback_analysis(disk_data)
                }

            # Generate analysis prompt
            prompt = self._generate_analysis_prompt(disk_data)

            # Get AI analysis
            response = self._get_ai_response(prompt)

            # Parse and structure the response
            analysis = self._parse_ai_response(response, disk_data)

            return analysis

        except Exception as e:
            print(f"❌ AI analysis failed: {e}")
            return {
                'error': f'AI analysis failed: {str(e)}',
                'fallback_analysis': self._generate_fallback_analysis(disk_data)
            }

    def _check_ollama_availability(self) -> bool:
        """Check if Ollama service is available."""
        try:
            # Try to list models to check if Ollama is running
            ollama.list()
            return True
        except Exception:
            return False

    def _generate_analysis_prompt(self, disk_data: Dict[str, Any]) -> str:
        """
        Generate a detailed prompt for disk health analysis.

        Args:
            disk_data (Dict[str, Any]): Raw disk health data

        Returns:
            str: Formatted prompt for AI analysis
        """
        # Format the data for the prompt
        formatted_data = self._format_data_for_prompt(disk_data)

        prompt = f"""You are an expert system administrator and disk health specialist.
Analyze the following disk health data and provide a comprehensive diagnostic report.

DISK HEALTH DATA:
{formatted_data}

Please provide a detailed analysis covering the following sections in EXACT order:

=== HEALTH ASSESSMENT ===
- Overall Health Status: [GOOD/WARNING/CRITICAL/UNKNOWN]
- System Health Rating: [EXCELLENT/GOOD/FAIR/POOR/CRITICAL]
- Assessment Confidence: [HIGH/MEDIUM/LOW]
- Total Disks Analyzed: [number]
- Critical Issues Detected: [number]

=== SPECIFIC ISSUES IDENTIFIED ===
For each issue found, provide:
- Issue Type: [SMART_ERROR/TEMPERATURE/CAPACITY/PERFORMANCE/UNKNOWN]
- Severity: [CRITICAL/HIGH/MEDIUM/LOW]
- Affected Component: [disk identifier or system component]
- Description: [technical description of the issue]

=== RISK ASSESSMENT ===
- Failure Probability: [LOW (<10%)/MEDIUM (10-50%)/HIGH (>50%)]
- Timeframe: [IMMEDIATE (<24h)/SHORT (1-7 days)/MEDIUM (1-4 weeks)/LONG (>1 month)]
- Risk Factors: [list specific factors contributing to risk]
- Impact Assessment: [LOW/MEDIUM/HIGH - potential impact on system operation]

=== TECHNICAL METRICS ANALYSIS ===
For each disk, analyze:
- SMART Health Status: [PASSED/FAILED/UNKNOWN]
- Temperature: [value]°C [NORMAL/ELEVATED/CRITICAL]
- Capacity Utilization: [percentage]% [NORMAL/ELEVATED/CRITICAL]
- I/O Performance: [NORMAL/DEGRADED/CRITICAL]
- Key SMART Attributes of Concern: [list specific attributes with values]

=== ACTIONABLE RECOMMENDATIONS ===
Provide numbered recommendations in order of priority:
1. [IMMEDIATE/URGENT/IMPORTANT/ROUTINE] - [specific action]
2. [IMMEDIATE/URGENT/IMPORTANT/ROUTINE] - [specific action]
3. [IMMEDIATE/URGENT/IMPORTANT/ROUTINE] - [specific action]

For each recommendation include:
- Priority Level: [IMMEDIATE/URGENT/IMPORTANT/ROUTINE]
- Action Type: [MONITOR/INVESTIGATE/REPLACE/CONFIGURE/OTHER]
- Implementation Window: [IMMEDIATE/24H/7DAYS/30DAYS/ROUTINE]
- Expected Outcome: [technical benefit of taking this action]

=== TECHNICAL SUMMARY ===
- Root Cause Analysis: [technical explanation of primary issues]
- Trend Analysis: [notable patterns or trends in the data]
- Monitoring Focus: [specific metrics to monitor going forward]
- Next Review Date: [recommended date for next comprehensive analysis]

IMPORTANT: Use consistent technical terminology throughout the report.
Maintain professional objectivity and technical accuracy.
Format the response exactly as shown above with section headers in ALL CAPS and triple equals signs.
Do not add additional sections or modify the structure."""
        return prompt

    def _format_data_for_prompt(self, disk_data: Dict[str, Any]) -> str:
        """Format disk data for AI prompt."""
        lines = []

        # System information
        if 'system_info' in disk_data:
            sys_info = disk_data['system_info']
            lines.append(f"System: {sys_info.get('hostname', 'Unknown')} ({sys_info.get('platform', 'Unknown')})")
            lines.append(f"Collection Time: {disk_data.get('timestamp', 'Unknown')}")
            lines.append("")

        # Summary information
        if 'summary' in disk_data:
            summary = disk_data['summary']
            lines.append(f"Total Disks: {summary.get('total_disks', 0)}")
            lines.append(f"Overall Status: {summary.get('status', 'Unknown')}")
            lines.append("")

        # Disk details
        if 'disks' in disk_data:
            for i, disk in enumerate(disk_data['disks'], 1):
                lines.append(f"=== DISK {i}: {disk.get('device', 'Unknown')} ===")
                lines.append(f"Health Status: {disk.get('health_status', 'Unknown')}")

                # Temperature
                if disk.get('temperature') is not None:
                    lines.append(f"Temperature: {disk['temperature']}°C")

                # SMART data
                smart = disk.get('smart_data', {})
                if smart and 'device_info' in smart:
                    device_info = smart['device_info']
                    model = device_info.get('Device Model', 'Unknown')
                    capacity = device_info.get('User Capacity', 'Unknown')
                    lines.append(f"Model: {model}")
                    lines.append(f"Capacity: {capacity}")

                # Usage data
                usage = disk.get('usage_data', {})
                if usage:
                    lines.append("Usage Information:")
                    for mount, data in usage.items():
                        if isinstance(data, dict) and 'percent' in data:
                            lines.append(f"  {mount}: {data['percent']:.1f}% used ({data['used']//1024//1024//1024}GB/{data['total']//1024//1024//1024}GB)")

                # Issues
                if disk.get('issues'):
                    lines.append("Issues:")
                    for issue in disk['issues']:
                        lines.append(f"  - {issue}")

                lines.append("")

        return "\n".join(lines)

    def _get_ai_response(self, prompt: str) -> str:
        """
        Get response from Ollama AI model.

        Args:
            prompt (str): The analysis prompt

        Returns:
            str: AI response text
        """
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.3,  # Lower temperature for more consistent, technical responses
                    'top_p': 0.9,
                    'max_tokens': 2000
                }
            )
            return response['response']
        except Exception as e:
            raise Exception(f"Failed to get AI response: {str(e)}")

    def _parse_ai_response(self, response: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and structure the AI response.

        Args:
            response (str): Raw AI response text
            original_data (Dict[str, Any]): Original disk data for reference

        Returns:
            Dict[str, Any]: Structured analysis report
        """
        # Extract key information from the response
        report = {
            'timestamp': datetime.now().isoformat(),
            'model_used': self.model,
            'analysis': response,
            'summary': self._extract_summary(response),
            'recommendations': self._extract_recommendations(response),
            'risk_level': self._extract_risk_level(response),
            'health_assessment': self._extract_health_assessment(response),
            'issues_identified': self._extract_issues(response),
            'technical_metrics': self._extract_technical_metrics(response),
            'original_data_reference': {
                'total_disks': len(original_data.get('disks', [])),
                'collection_time': original_data.get('timestamp', 'Unknown')
            }
        }

        return report

    def _extract_summary(self, response: str) -> Dict[str, Any]:
        """Extract summary information from AI response."""
        summary = {
            'health_status': 'Unknown',
            'confidence': 'Unknown',
            'critical_issues': 0,
            'total_recommendations': 0
        }

        # Simple pattern matching to extract key information
        response_lower = response.lower()

        if 'critical' in response_lower:
            summary['health_status'] = 'Critical'
        elif 'warning' in response_lower:
            summary['health_status'] = 'Warning'
        elif 'good' in response_lower or 'healthy' in response_lower:
            summary['health_status'] = 'Good'

        if 'high confidence' in response_lower:
            summary['confidence'] = 'High'
        elif 'medium confidence' in response_lower or 'moderate confidence' in response_lower:
            summary['confidence'] = 'Medium'
        elif 'low confidence' in response_lower:
            summary['confidence'] = 'Low'

        # Count critical issues and recommendations
        summary['critical_issues'] = response_lower.count('critical')
        summary['total_recommendations'] = response_lower.count('recommend') + response_lower.count('suggest')

        return summary

    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from AI response."""
        recommendations = []

        # Look for recommendation sections
        lines = response.split('\n')
        in_recommendations = False

        for line in lines:
            line_lower = line.lower().strip()

            if any(keyword in line_lower for keyword in ['recommendations', 'recommendation', 'suggestions', 'actions']):
                in_recommendations = True
                continue
            elif in_recommendations and line_lower.startswith('==='):
                # End of recommendations section
                in_recommendations = False
                continue

            if in_recommendations and line.strip() and not line.startswith('#'):
                # Extract properly formatted recommendations
                line_stripped = line.strip()

                # Check for numbered recommendations (1., 2., 3., etc.)
                if re.match(r'^\d+\.\s+', line_stripped):
                    recommendations.append(line_stripped)
                # Check for bullet points
                elif line_stripped.startswith(('-', '*', '•')):
                    recommendations.append(line_stripped)
                # Check for lines that start with priority levels
                elif any(priority in line_lower for priority in ['immediate:', 'urgent:', 'important:', 'routine:']):
                    recommendations.append(line_stripped)

        # Filter out non-recommendation lines that might have been captured
        filtered_recommendations = []
        for rec in recommendations:
            rec_lower = rec.lower()
            # Skip lines that are section headers or formatting
            if any(skip_word in rec_lower for skip_word in ['technical metrics analysis', 'detailed', 'trend analysis', 'monitoring focus', 'next review date']):
                continue
            # Only include lines that actually contain actionable items
            if len(rec) > 10 and any(action_word in rec_lower for action_word in ['investigate', 'check', 'monitor', 'run', 'consider', 'review', 'analyze']):
                filtered_recommendations.append(rec)

        return filtered_recommendations

    def _extract_risk_level(self, response: str) -> str:
        """Extract risk level from AI response."""
        response_lower = response.lower()

        if 'high risk' in response_lower or 'high probability' in response_lower:
            return 'High'
        elif 'medium risk' in response_lower or 'moderate risk' in response_lower or 'medium probability' in response_lower:
            return 'Medium'
        elif 'low risk' in response_lower or 'low probability' in response_lower:
            return 'Low'
        else:
            return 'Unknown'

    def _extract_health_assessment(self, response: str) -> Dict[str, Any]:
        """Extract structured health assessment from AI response."""
        assessment = {
            'overall_status': 'Unknown',
            'system_rating': 'Unknown',
            'confidence': 'Unknown',
            'disks_analyzed': 0,
            'critical_issues': 0
        }

        # Extract from HEALTH ASSESSMENT section
        lines = response.split('\n')
        in_health_section = False

        for line in lines:
            if '=== health assessment ===' in line.lower():
                in_health_section = True
                continue
            elif in_health_section and line.strip().startswith('==='):
                in_health_section = False
                continue

            if in_health_section:
                if 'overall health status:' in line.lower():
                    status = line.split(':')[1].strip().strip('[]')
                    assessment['overall_status'] = status
                elif 'system health rating:' in line.lower():
                    rating = line.split(':')[1].strip().strip('[]')
                    assessment['system_rating'] = rating
                elif 'assessment confidence:' in line.lower():
                    confidence = line.split(':')[1].strip().strip('[]')
                    assessment['confidence'] = confidence
                elif 'total disks analyzed:' in line.lower():
                    try:
                        assessment['disks_analyzed'] = int(line.split(':')[1].strip())
                    except ValueError:
                        pass
                elif 'critical issues detected:' in line.lower():
                    try:
                        assessment['critical_issues'] = int(line.split(':')[1].strip())
                    except ValueError:
                        pass

        return assessment

    def _extract_issues(self, response: str) -> List[Dict[str, Any]]:
        """Extract structured issues from AI response."""
        issues = []
        lines = response.split('\n')
        in_issues_section = False

        for line in lines:
            if '=== specific issues identified ===' in line.lower():
                in_issues_section = True
                continue
            elif in_issues_section and line.strip().startswith('==='):
                in_issues_section = False
                continue

            if in_issues_section and line.strip():
                # Look for structured issue format
                if 'issue type:' in line.lower() and 'severity:' in line.lower():
                    issue = {
                        'type': 'Unknown',
                        'severity': 'Unknown',
                        'component': 'Unknown',
                        'description': 'No description provided'
                    }

                    # Extract issue type
                    if 'issue type:' in line.lower():
                        type_part = line.split('issue type:')[1].split('severity:')[0].strip().strip('[]')
                        issue['type'] = type_part

                    # Extract severity
                    if 'severity:' in line.lower():
                        severity_part = line.split('severity:')[1].split('affected component:')[0].strip().strip('[]')
                        issue['severity'] = severity_part

                    issues.append(issue)

        return issues

    def _extract_technical_metrics(self, response: str) -> Dict[str, Any]:
        """Extract technical metrics from AI response."""
        metrics = {
            'disks': [],
            'smart_status': {},
            'temperature_analysis': {},
            'capacity_analysis': {},
            'io_performance': {},
            'device_models': {},
            'filesystem_types': {},
            'disk_capacities': {}
        }

        lines = response.split('\n')
        in_metrics_section = False
        current_disk = None

        for line in lines:
            if '=== technical metrics analysis ===' in line.lower():
                in_metrics_section = True
                continue
            elif in_metrics_section and line.strip().startswith('==='):
                in_metrics_section = False
                continue

            if in_metrics_section:
                # Look for disk-specific metrics
                if line.strip().startswith('for each disk') or line.strip().startswith('disk'):
                    continue
                elif 'smart health status:' in line.lower():
                    status = line.split(':')[1].strip().strip('[]')
                    if current_disk:
                        metrics['smart_status'][current_disk] = status
                elif 'temperature:' in line.lower():
                    temp_info = line.split(':')[1].strip()
                    if current_disk:
                        metrics['temperature_analysis'][current_disk] = temp_info
                elif 'capacity utilization:' in line.lower():
                    cap_info = line.split(':')[1].strip()
                    if current_disk:
                        metrics['capacity_analysis'][current_disk] = cap_info
                elif 'i/o performance:' in line.lower():
                    io_info = line.split(':')[1].strip()
                    if current_disk:
                        metrics['io_performance'][current_disk] = io_info
                elif 'model:' in line.lower():
                    model_info = line.split(':')[1].strip()
                    if current_disk:
                        metrics['device_models'][current_disk] = model_info
                elif 'capacity:' in line.lower():
                    capacity_info = line.split(':')[1].strip()
                    if current_disk:
                        metrics['disk_capacities'][current_disk] = capacity_info
                elif 'filesystem:' in line.lower() or 'fstype:' in line.lower():
                    fs_info = line.split(':')[1].strip()
                    if current_disk:
                        metrics['filesystem_types'][current_disk] = fs_info
                # Handle the format from the AI response (e.g., "SMART Health Status: FAILED")
                elif 'smart health status' in line.lower() and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        status = parts[1].strip()
                        # Try to find the disk from context or use a generic name
                        if current_disk:
                            metrics['smart_status'][current_disk] = status
                        else:
                            # Look for disk identifier in the line or previous lines
                            for prev_line in lines[max(0, lines.index(line)-5):lines.index(line)]:
                                if '/dev/' in prev_line:
                                    disk_match = re.search(r'/dev/[^,\s]+', prev_line)
                                    if disk_match:
                                        current_disk = disk_match.group(0)
                                        metrics['smart_status'][current_disk] = status
                                        break
                # Enhanced disk identification from AI response format
                elif '/dev/' in line and ('DISK' in line or 'Device' in line):
                    disk_match = re.search(r'/dev/[^,\s]+', line)
                    if disk_match:
                        current_disk = disk_match.group(0)
                        # Also extract model and capacity if mentioned in the same line
                        if 'Model:' in line:
                            model_match = re.search(r'Model:\s*([^,\n]+)', line)
                            if model_match:
                                metrics['device_models'][current_disk] = model_match.group(1).strip()
                        if 'Capacity:' in line:
                            capacity_match = re.search(r'Capacity:\s*([^,\n]+)', line)
                            if capacity_match:
                                metrics['disk_capacities'][current_disk] = capacity_match.group(1).strip()

        return metrics

    def _generate_fallback_analysis(self, disk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a basic analysis when AI is not available.

        Args:
            disk_data (Dict[str, Any]): Raw disk health data

        Returns:
            Dict[str, Any]: Basic analysis report
        """
        print("⚠️  Ollama not available, generating basic analysis...")

        summary = disk_data.get('summary', {})
        disks = disk_data.get('disks', [])

        fallback_analysis = {
            'timestamp': datetime.now().isoformat(),
            'model_used': 'fallback',
            'analysis': self._generate_fallback_text(summary, disks),
            'summary': {
                'health_status': summary.get('status', 'Unknown'),
                'confidence': 'Low (fallback analysis)',
                'critical_issues': len(summary.get('issues', [])),
                'total_recommendations': 3
            },
            'recommendations': self._generate_fallback_recommendations(summary, disks),
            'risk_level': self._assess_fallback_risk(summary, disks),
            'original_data_reference': {
                'total_disks': len(disks),
                'collection_time': disk_data.get('timestamp', 'Unknown')
            }
        }

        return fallback_analysis

    def _generate_fallback_text(self, summary: Dict[str, Any], disks: List[Dict[str, Any]]) -> str:
        """Generate fallback analysis text."""
        text = "=== DISK HEALTH ANALYSIS (FALLBACK) ===\n\n"

        text += f"Overall Status: {summary.get('status', 'Unknown')}\n"
        text += f"Total Disks: {len(disks)}\n\n"

        if summary.get('issues'):
            text += "IDENTIFIED ISSUES:\n"
            for issue in summary['issues']:
                text += f"- {issue}\n"
            text += "\n"

        text += "RECOMMENDATIONS:\n"
        text += "1. Monitor disk temperatures regularly\n"
        text += "2. Check SMART data weekly for early warning signs\n"
        text += "3. Consider replacing disks showing critical SMART errors\n"

        return text

    def _generate_fallback_recommendations(self, summary: Dict[str, Any], disks: List[Dict[str, Any]]) -> List[str]:
        """Generate fallback recommendations."""
        recommendations = [
            "Monitor disk health metrics regularly",
            "Check SMART data for warning signs",
            "Maintain adequate disk space (keep below 80% usage)"
        ]

        if summary.get('status') == 'CRITICAL':
            recommendations.insert(0, "IMMEDIATE: Review critical disk issues")

        if summary.get('issues'):
            recommendations.append("Address specific issues identified in the analysis")

        return recommendations

    def _assess_fallback_risk(self, summary: Dict[str, Any], disks: List[Dict[str, Any]]) -> str:
        """Assess risk level in fallback mode."""
        if summary.get('status') == 'CRITICAL':
            return 'High'
        elif summary.get('status') == 'WARNING' or summary.get('issues'):
            return 'Medium'
        else:
            return 'Low'


def main():
    """Main function for testing the AI analyzer."""
    # Sample disk data for testing
    sample_data = {
        'timestamp': '2024-01-01T12:00:00',
        'system_info': {'hostname': 'test-server'},
        'summary': {
            'status': 'WARNING',
            'total_disks': 2,
            'issues': ['Disk /dev/sda: High temperature (55°C)']
        },
        'disks': [
            {
                'device': '/dev/sda',
                'health_status': 'WARNING',
                'temperature': 55,
                'usage_data': {
                    '/': {
                        'percent': 75.5,
                        'total': 1000000000000,
                        'used': 755000000000
                    }
                }
            }
        ]
    }

    analyzer = AIDiskAnalyzer()
    result = analyzer.analyze_disk_health(sample_data)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

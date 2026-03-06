#!/usr/bin/env python3
"""
AI Disk Health Analyzer

This module uses Ollama's LLM to analyze disk health data and generate
comprehensive diagnostic reports with actionable recommendations.
"""

import json
import ollama
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

Please provide a detailed analysis covering:

1. **Overall Health Assessment**:
   - Current health status of each disk
   - Overall system disk health rating (Good/Warning/Critical)
   - Confidence level in your assessment

2. **Specific Issues Identified**:
   - Any hardware problems detected
   - Performance concerns
   - Capacity issues
   - Temperature problems
   - SMART attribute warnings

3. **Risk Assessment**:
   - Probability of disk failure (Low/Medium/High)
   - Timeframe for potential issues
   - Critical warnings that need immediate attention

4. **Actionable Recommendations**:
   - Immediate actions required (if any)
   - Preventive maintenance suggestions
   - Monitoring recommendations
   - When to consider disk replacement

5. **Technical Details**:
   - Key metrics that influenced your assessment
   - Specific SMART attributes of concern
   - Performance bottlenecks identified

Format your response as a structured report with clear sections and actionable items.
Use technical accuracy while keeping recommendations practical and implementable."""

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

            if in_recommendations and line.strip() and not line.startswith('#'):
                # Extract bullet points and numbered items
                if line.strip().startswith(('-', '*', '•', '1.', '2.', '3.')):
                    recommendations.append(line.strip())
                elif len(line.strip()) > 20:  # Likely a recommendation sentence
                    recommendations.append(line.strip())

        return recommendations[:10]  # Limit to first 10 recommendations

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

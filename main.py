#!/usr/bin/env python3
"""
AI Disk Health Monitor - Main CLI Application

This is the main entry point for the AI-powered disk health monitoring application.
It provides a command-line interface for analyzing disk health using Ollama AI.
"""

import sys
import argparse
import json
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from disk_collector import DiskHealthCollector
from ai_analyzer import AIDiskAnalyzer
from report_generator import ReportGenerator

# Load environment variables
load_dotenv()


class DiskHealthMonitor:
    """Main application class for disk health monitoring."""

    def __init__(self):
        # Get model from environment variable or use default
        model = os.getenv('OLLAMA_MODEL', 'gemma3:1b')
        self.collector = DiskHealthCollector()
        self.analyzer = AIDiskAnalyzer(model=model)
        self.reporter = ReportGenerator()

    def run_analysis(self, verbose: bool = False, save_report: bool = False,
                    json_output: bool = False, model: str = "gemma3:1b") -> Dict[str, Any]:
        """
        Run complete disk health analysis.

        Args:
            verbose (bool): Include detailed analysis in report
            save_report (bool): Save report to file
            json_output (bool): Output in JSON format
            model (str): Ollama model to use for analysis

        Returns:
            Dict[str, Any]: Analysis results
        """
        print("🚀 Starting AI Disk Health Analysis")
        print("=" * 60)

        # Update analyzer model if specified
        if model != self.analyzer.model:
            self.analyzer.model = model
            print(f"Using model: {model}")

        try:
            # Step 1: Collect disk health data
            print("\n📊 Step 1: Collecting disk health data...")
            disk_data = self.collector.collect_all_data()

            if 'error' in disk_data:
                print(f"❌ Failed to collect disk data: {disk_data['error']}")
                return disk_data

            print(f"✅ Collected data for {len(disk_data.get('disks', []))} disks")

            # Step 2: Analyze with AI
            print("\n🤖 Step 2: Analyzing with AI...")
            start_time = time.time()
            analysis_result = self.analyzer.analyze_disk_health(disk_data)
            end_time = time.time()
            ai_analysis_time = end_time - start_time

            # Handle fallback analysis
            if 'fallback_analysis' in analysis_result:
                print("⚠️  Using fallback analysis (AI not available)")
                final_result = analysis_result['fallback_analysis']
            else:
                final_result = analysis_result

            # Add timing information to the result
            final_result['ai_analysis_time'] = ai_analysis_time

            # Step 3: Generate and display report
            print("\n📋 Step 3: Generating report...")

            if json_output:
                self.reporter.print_json_output(final_result)
            else:
                report = self.reporter.generate_report(final_result, verbose=verbose)
                print(report)

            # Step 4: Save report if requested
            if save_report and not json_output:
                filename = self.reporter.save_report_to_file(report)
                if filename:
                    print(f"\n📄 Report saved to: {filename}")

            return final_result

        except KeyboardInterrupt:
            print("\n⚠️  Analysis interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            return {'error': str(e)}

    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        print("🔍 Checking dependencies...")

        # Check if Ollama is available
        try:
            self.analyzer._check_ollama_availability()
            print("✅ Ollama service is available")
        except Exception:
            print("⚠️  Ollama service not available (will use fallback analysis)")

        # Check if smartctl is available
        try:
            import subprocess
            result = subprocess.run(['which', 'smartctl'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ smartctl is available")
            else:
                print("⚠️  smartctl not found (limited SMART data collection)")
        except Exception:
            print("⚠️  Could not check smartctl availability")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Disk Health Monitor - Analyze disk health using Ollama AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Basic analysis
  python main.py --verbose          # Detailed analysis
  python main.py --save             # Save report to file
  python main.py --json             # JSON output
  python main.py --model gemma3:1b  # Use different model
        """
    )

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Include detailed analysis in report')
    parser.add_argument('--save', '-s', action='store_true',
                       help='Save report to file')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output analysis in JSON format')
    # Get default model from environment variable or use fallback
    default_model = os.getenv('OLLAMA_MODEL', 'gemma3:1b')
    parser.add_argument('--model', '-m', default=default_model,
                       help=f'Ollama model to use for analysis (default: {default_model})')
    parser.add_argument('--check-deps', action='store_true',
                       help='Check if required dependencies are available')
    parser.add_argument('--version', action='version', version='AI Disk Health Monitor v1.0.0')

    args = parser.parse_args()

    # Create monitor instance
    monitor = DiskHealthMonitor()

    # Check dependencies if requested
    if args.check_deps:
        monitor.check_dependencies()
        return

    # Run analysis
    result = monitor.run_analysis(
        verbose=args.verbose,
        save_report=args.save,
        json_output=args.json,
        model=args.model
    )

    # Exit with appropriate code
    if 'error' in result:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

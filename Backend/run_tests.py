#!/usr/bin/env python3
"""
Test runner script for AI Scribe backend tests.
Provides convenient commands for running different test suites.
"""

import sys
import subprocess
import argparse


def run_command(cmd):
    """Run a shell command and return the result."""
    print(f"\n🧪 Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run AI Scribe backend tests")
    parser.add_argument(
        "suite",
        nargs="?",
        choices=["all", "unit", "integration", "performance", "export", "import", "tenant", "database", "coverage"],
        default="all",
        help="Test suite to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-k", "--keyword",
        type=str,
        help="Run tests matching keyword"
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    args = parser.parse_args()
    
    # Base command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    
    # Add coverage (unless disabled)
    if not args.no_cov and args.suite != "performance":
        cmd.extend(["--cov=.", "--cov-report=term-missing"])
    
    # Add test suite filter
    if args.suite == "all":
        print("📋 Running ALL tests...")
    elif args.suite == "unit":
        print("🔬 Running UNIT tests only...")
        cmd.extend(["-m", "unit"])
    elif args.suite == "integration":
        print("🔗 Running INTEGRATION tests only...")
        cmd.extend(["-m", "integration"])
    elif args.suite == "performance":
        print("⚡ Running PERFORMANCE tests only...")
        cmd.extend(["-m", "performance"])
    elif args.suite == "export":
        print("📤 Running EXPORT tests...")
        cmd.append("tests/test_export_service.py")
    elif args.suite == "import":
        print("📥 Running IMPORT tests...")
        cmd.append("tests/test_import_service.py")
    elif args.suite == "tenant":
        print("🏢 Running TENANT tests...")
        cmd.append("tests/test_tenant_config.py")
    elif args.suite == "database":
        print("💾 Running DATABASE tests...")
        cmd.append("tests/test_database.py")
    elif args.suite == "coverage":
        print("📊 Generating coverage report...")
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    # Add keyword filter
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    # Run the tests
    exit_code = run_command(cmd)
    
    # Print summary
    print("\n" + "="*70)
    if exit_code == 0:
        print("✅ All tests passed!")
        if args.suite == "coverage":
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ Some tests failed!")
        print(f"Exit code: {exit_code}")
    print("="*70 + "\n")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

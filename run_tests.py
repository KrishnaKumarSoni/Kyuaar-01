#!/usr/bin/env python3
"""
Test runner script for Kyuaar QR packet management platform
Provides comprehensive testing with coverage reporting
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and print results"""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(command)}")
    print("-" * 60)
    
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED (exit code: {result.returncode})")
    
    return result.returncode == 0


def setup_test_environment():
    """Set up environment variables for testing"""
    os.environ['TESTING'] = 'true'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['FIREBASE_STORAGE_BUCKET'] = 'test-bucket'
    print("✅ Test environment configured")


def run_unit_tests(verbose=False, coverage=True):
    """Run unit tests"""
    cmd = ['python', '-m', 'pytest', 'tests/unit/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=.', '--cov-report=term-missing'])
    
    return run_command(cmd, "Running Unit Tests")


def run_integration_tests(verbose=False, coverage=True):
    """Run integration tests"""
    cmd = ['python', '-m', 'pytest', 'tests/integration/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=.', '--cov-append', '--cov-report=term-missing'])
    
    return run_command(cmd, "Running Integration Tests")


def run_e2e_tests(verbose=False, coverage=True):
    """Run end-to-end tests"""
    cmd = ['python', '-m', 'pytest', 'tests/e2e/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=.', '--cov-append', '--cov-report=term-missing'])
    
    return run_command(cmd, "Running End-to-End Tests")


def run_specific_tests(test_pattern, verbose=False):
    """Run specific tests matching pattern"""
    cmd = ['python', '-m', 'pytest', '-k', test_pattern]
    
    if verbose:
        cmd.append('-v')
    
    return run_command(cmd, f"Running Tests Matching: {test_pattern}")


def generate_coverage_report():
    """Generate HTML coverage report"""
    cmd = ['python', '-m', 'pytest', '--cov=.', '--cov-report=html', '--cov-report=xml']
    
    success = run_command(cmd, "Generating Coverage Report")
    
    if success:
        print(f"\n📊 Coverage report generated:")
        print(f"   HTML: file://{Path.cwd()}/htmlcov/index.html")
        print(f"   XML:  {Path.cwd()}/coverage.xml")
    
    return success


def run_linting():
    """Run code quality checks"""
    checks = [
        (['python', '-m', 'flake8', '.', '--count', '--statistics'], "Flake8 Linting"),
        (['python', '-m', 'black', '--check', '.'], "Black Code Formatting"),
        (['python', '-m', 'isort', '--check-only', '.'], "Import Sorting"),
    ]
    
    results = []
    for cmd, description in checks:
        try:
            results.append(run_command(cmd, description))
        except FileNotFoundError:
            print(f"⚠️  Skipping {description} - tool not installed")
            results.append(True)  # Don't fail if optional tools are missing
    
    return all(results)


def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-flask',
        'pytest-mock',
        'faker',
        'requests-mock'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All required test dependencies are installed")
    return True


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Run Kyuaar test suite')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--e2e', action='store_true', help='Run end-to-end tests only')
    parser.add_argument('--pattern', '-k', help='Run tests matching pattern')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--no-coverage', action='store_true', help='Skip coverage reporting')
    parser.add_argument('--lint', action='store_true', help='Run code quality checks')
    parser.add_argument('--coverage-only', action='store_true', help='Generate coverage report only')
    
    args = parser.parse_args()
    
    print("🧪 Kyuaar Test Suite Runner")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Set up test environment
    setup_test_environment()
    
    coverage = not args.no_coverage
    success = True
    
    if args.coverage_only:
        success = generate_coverage_report()
    elif args.lint:
        success = run_linting()
    elif args.pattern:
        success = run_specific_tests(args.pattern, args.verbose)
    elif args.unit:
        success = run_unit_tests(args.verbose, coverage)
    elif args.integration:
        success = run_integration_tests(args.verbose, coverage)
    elif args.e2e:
        success = run_e2e_tests(args.verbose, coverage)
    else:
        # Run full test suite
        results = []
        
        print("\n🎯 Running Full Test Suite")
        print("=" * 60)
        
        results.append(run_unit_tests(args.verbose, coverage))
        results.append(run_integration_tests(args.verbose, coverage))
        results.append(run_e2e_tests(args.verbose, coverage))
        
        if coverage:
            results.append(generate_coverage_report())
        
        # Optional linting
        if not args.no_coverage:
            print("\n🔍 Running Code Quality Checks")
            run_linting()  # Don't fail build on linting issues
        
        success = all(results)
    
    # Print summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed successfully!")
        print("\nNext steps:")
        print("1. Review coverage report in htmlcov/index.html")
        print("2. Address any failing tests")
        print("3. Deploy to staging environment")
    else:
        print("💥 Some tests failed!")
        print("\nNext steps:")
        print("1. Review failed test output above")
        print("2. Fix failing tests")
        print("3. Re-run test suite")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
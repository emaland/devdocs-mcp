#!/usr/bin/env python3
"""
Test runner for DevDocs MCP Server
"""

import subprocess
import sys
import os


def run_simple_tests():
    """Run the simple test runner."""
    print("Running simple tests...")
    try:
        subprocess.run([sys.executable, "tests/test_integration.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Simple tests failed: {e}")
        return False
    return True


def run_pytest():
    """Run pytest if available."""
    try:
        subprocess.run([sys.executable, "-m", "pytest", "-v"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Pytest failed: {e}")
        return False
    except FileNotFoundError:
        print("pytest not available, skipping...")
        return True


def run_linting():
    """Run code quality checks."""
    print("\nRunning code quality checks...")
    
    # Run black
    try:
        subprocess.run([sys.executable, "-m", "black", "--check", "."], check=True)
        print("✓ Black formatting check passed")
    except subprocess.CalledProcessError:
        print("⚠ Black formatting issues found")
    except FileNotFoundError:
        print("Black not available, skipping...")
    
    # Run ruff
    try:
        subprocess.run([sys.executable, "-m", "ruff", "check", "."], check=True)
        print("✓ Ruff linting passed")
    except subprocess.CalledProcessError:
        print("⚠ Ruff linting issues found")
    except FileNotFoundError:
        print("Ruff not available, skipping...")


def main():
    """Run all tests and checks."""
    print("DevDocs MCP Server Test Suite")
    print("=" * 40)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    success = True
    
    # Run simple tests
    if not run_simple_tests():
        success = False
    
    # Run pytest
    if not run_pytest():
        success = False
    
    # Run linting
    run_linting()
    
    if success:
        print("\n✓ All tests completed successfully!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
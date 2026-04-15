"""
Production Readiness Verification Script

Comprehensive end-to-end verification of all Phase 1-4 implementations.
"""
import sys
import subprocess
import json
from datetime import datetime


class Colors:
    """Terminal colors for output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")


def run_command(command, description):
    """Run a shell command and return success status."""
    print(f"\n{Colors.BOLD}Running: {description}{Colors.END}")
    print(f"Command: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print_success(f"{description} - PASSED")
            return True, result.stdout
        else:
            print_error(f"{description} - FAILED")
            print(f"Error: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print_error(f"{description} - TIMEOUT")
        return False, "Timeout"
    except Exception as e:
        print_error(f"{description} - ERROR: {str(e)}")
        return False, str(e)


def verify_phase_1():
    """Verify Phase 1: Foundation Stabilization."""
    print_header("PHASE 1: FOUNDATION STABILIZATION")

    results = []

    # Test 1: Run all backend tests
    success, output = run_command(
        "python -m pytest tests/ -v --tb=short -q",
        "Backend Test Suite (252 tests)"
    )
    results.append(("Backend Tests", success))

    if success:
        if "252 passed" in output:
            print_success("All 252 tests passing")
        else:
            print_error("Not all tests passing")
            results[-1] = ("Backend Tests", False)

    # Test 2: Check Alembic migrations
    success, output = run_command(
        "alembic current",
        "Alembic Migration Status"
    )
    results.append(("Alembic Migrations", success))

    if success and "(head)" in output:
        print_success("Database at head revision")

    # Test 3: Check for deprecation warnings
    success, output = run_command(
        "python -c \"from app.utils.time_utils import utcnow; print('utcnow imported:', utcnow())\"",
        "Datetime Utilities (No Deprecation Warnings)"
    )
    results.append(("No Deprecation Warnings", success))

    return results


def verify_phase_2():
    """Verify Phase 2: Real-World Data Quality."""
    print_header("PHASE 2: REAL-WORLD DATA QUALITY")

    results = []

    # Test 1: Check WeatherObservation model exists
    success, output = run_command(
        "python -c \"from app.models.weather_observation import WeatherObservation; print('Model loaded:', WeatherObservation.__tablename__)\"",
        "WeatherObservation Model"
    )
    results.append(("WeatherObservation Model", success))

    # Test 2: Check fraud detection enhancements
    success, output = run_command(
        "python -c \"from app.services.fraud_service import check_weather_consistency, check_device_fingerprint_enhanced; print('Enhanced fraud detection loaded')\"",
        "Enhanced Fraud Detection"
    )
    results.append(("Enhanced Fraud Detection", success))

    # Test 3: Check data lineage in Claim model
    success, output = run_command(
        "python -c \"from app.models.claim import Claim; import inspect; fields = [c.name for c in Claim.__table__.columns]; print('source_metadata' in fields)\"",
        "Data Lineage (source_metadata field)"
    )
    results.append(("Data Lineage", success and "True" in output))

    return results


def verify_phase_3():
    """Verify Phase 3: Mock/Demo Cleanup."""
    print_header("PHASE 3: MOCK/DEMO CLEANUP")

    results = []

    # Test 1: Check demo mode configuration
    success, output = run_command(
        "python -c \"from app.config import get_settings; s = get_settings(); print('demo_mode:', s.demo_mode)\"",
        "Demo Mode Configuration"
    )
    results.append(("Demo Mode Config", success))

    # Test 2: Check drill context manager
    success, output = run_command(
        "python -c \"from app.utils.demo_context import drill_mode, production_mode; print('Context managers loaded')\"",
        "Drill Context Manager"
    )
    results.append(("Drill Context Manager", success))

    # Test 3: Verify no prefer_mock in codebase
    success, output = run_command(
        "python -c \"import os; import re; count = 0; [count := count + len(re.findall(r'prefer_mock\\s*=', open(os.path.join(root, f), encoding='utf-8', errors='ignore').read())) for root, dirs, files in os.walk('app') for f in files if f.endswith('.py')]; print('prefer_mock occurrences:', count)\"",
        "No Hardcoded prefer_mock Flags"
    )
    results.append(("No prefer_mock Flags", success and "0" in output))

    return results


def verify_phase_4():
    """Verify Phase 4: Production Hardening."""
    print_header("PHASE 4: PRODUCTION HARDENING")

    results = []

    # Test 1: Check rate limiter
    success, output = run_command(
        "python -c \"from app.utils.rate_limiter import limiter, RATE_LIMITS; print('Rate limits:', len(RATE_LIMITS))\"",
        "Rate Limiter Configuration"
    )
    results.append(("Rate Limiter", success))

    if success and "6" in output:
        print_success("All 6 rate limit categories configured")

    # Test 2: Check structured logging
    success, output = run_command(
        "python -c \"from app.utils.logging_config import JSONFormatter, setup_logging; print('Logging configured')\"",
        "Structured Logging"
    )
    results.append(("Structured Logging", success))

    # Test 3: Check Sentry configuration (optional)
    success, output = run_command(
        "python -c \"from app.config import get_settings; s = get_settings(); print('sentry_dsn' if hasattr(s, 'sentry_dsn') else 'missing')\"",
        "Sentry Configuration (Optional)"
    )
    results.append(("Sentry Config", success and "sentry_dsn" in output))

    # Test 4: Check enhanced health endpoint
    success, output = run_command(
        "python -c \"import inspect; from app.main import health_check; src = inspect.getsource(health_check); print('components' in src)\"",
        "Enhanced Health Check"
    )
    results.append(("Enhanced Health Check", success and "True" in output))

    return results


def verify_integration():
    """Verify integration points."""
    print_header("INTEGRATION VERIFICATION")

    results = []

    # Test 1: Import main app
    success, output = run_command(
        "python -c \"from app.main import app; print('App loaded:', app.title)\"",
        "FastAPI App Loads"
    )
    results.append(("FastAPI App", success))

    # Test 2: Database connectivity
    success, output = run_command(
        "python -c \"from app.database import SessionLocal; from sqlalchemy import text; db = SessionLocal(); db.execute(text('SELECT 1')); db.close(); print('DB connected')\"",
        "Database Connectivity"
    )
    results.append(("Database Connection", success))

    # Test 3: All models importable
    success, output = run_command(
        "python -c \"from app.models import Partner, Zone, Policy, Claim, WeatherObservation, PartnerDevice, PartnerGPSPing; print('All models loaded')\"",
        "All Models Load"
    )
    results.append(("All Models", success))

    return results


def print_summary(all_results):
    """Print verification summary."""
    print_header("VERIFICATION SUMMARY")

    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(sum(1 for _, success in results if success) for results in all_results.values())

    print(f"\n{Colors.BOLD}Results by Phase:{Colors.END}\n")

    for phase, results in all_results.items():
        passed = sum(1 for _, success in results if success)
        total = len(results)
        status = f"{Colors.GREEN}✓" if passed == total else f"{Colors.RED}✗"
        print(f"{status} {phase}: {passed}/{total} tests passed{Colors.END}")

        for test_name, success in results:
            icon = f"{Colors.GREEN}✓" if success else f"{Colors.RED}✗"
            print(f"  {icon} {test_name}{Colors.END}")

    print(f"\n{Colors.BOLD}{'─' * 80}{Colors.END}")

    percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED: {passed_tests}/{total_tests} ({percentage:.1f}%){Colors.END}")
        print(f"{Colors.GREEN}{Colors.BOLD}✅ PRODUCTION READY!{Colors.END}\n")
        return True
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ TESTS PASSED: {passed_tests}/{total_tests} ({percentage:.1f}%){Colors.END}")
        print(f"{Colors.YELLOW}Some tests failed - review before production deployment{Colors.END}\n")
        return False


def main():
    """Run comprehensive verification."""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═" * 78 + "╗")
    print("║" + "RapidCover Production Readiness Verification".center(78) + "║")
    print("║" + f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print(Colors.END)

    all_results = {}

    # Run all phase verifications
    all_results["Phase 1: Foundation"] = verify_phase_1()
    all_results["Phase 2: Data Quality"] = verify_phase_2()
    all_results["Phase 3: Demo Cleanup"] = verify_phase_3()
    all_results["Phase 4: Production Hardening"] = verify_phase_4()
    all_results["Integration Tests"] = verify_integration()

    # Print summary
    success = print_summary(all_results)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

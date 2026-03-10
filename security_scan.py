#!/usr/bin/env python3
"""
Security scanning script for Rekapo backend.
Runs bandit (Python security linter) and safety (dependency vulnerability scanner).

Usage:
    python security_scan.py

Requirements:
    pip install bandit safety
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and print results."""
    print(f"\n{'=' * 80}")
    print(f"🔍 {description}")
    print(f"{'=' * 80}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"⚠️ {description} - FOUND ISSUES (return code: {result.returncode})")
        
        return result.returncode
    
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return 1


def main():
    """Run security scans."""
    print("🛡️ Rekapo Security Scanner")
    print("=" * 80)
    
    # Check if tools are installed
    print("\n📦 Checking required tools...")
    tools_missing = False
    
    for tool in ["bandit", "safety"]:
        result = subprocess.run(f"{tool} --version", shell=True, capture_output=True)
        if result.returncode != 0:
            print(f"❌ {tool} not found. Install with: pip install {tool}")
            tools_missing = True
        else:
            print(f"✅ {tool} found")
    
    if tools_missing:
        print("\n⚠️ Install missing tools with:")
        print("   pip install bandit safety")
        sys.exit(1)
    
    # Run security scans
    exit_codes = []
    
    # 1. Bandit - Python security linter
    # Scans for common security issues (SQL injection, hardcoded passwords, etc.)
    # Exclude venv to speed up scan (don't scan third-party dependencies)
    exit_codes.append(run_command(
        "bandit -r . -f json -o bandit_report.json --exclude ./venv,./venv/**,./ai_models/whisper/models/** && bandit -r . -f screen --exclude ./venv,./venv/**,./ai_models/whisper/models/**",
        "Bandit - Python Security Linter"
    ))
    
    # 2. Safety - Check dependencies for known vulnerabilities
    # Scans requirements.txt against SafetyDB
    exit_codes.append(run_command(
        "safety check --json --output safety_report.json || safety check",
        "Safety - Dependency Vulnerability Scanner"
    ))
    
    # 3. Bandit baseline (for thesis - show you're aware of issues)
    print(f"\n{'=' * 80}")
    print("📊 Summary")
    print(f"{'=' * 80}")
    
    if all(code == 0 for code in exit_codes):
        print("✅ All security scans passed!")
    else:
        print("⚠️ Security issues found. Review reports:")
        print("   - bandit_report.json")
        print("   - safety_report.json")
    
    print("\n💡 For thesis defense:")
    print("   - bandit checks for: SQL injection, hardcoded secrets, insecure functions")
    print("   - safety checks for: Known CVEs in dependencies")
    print("   - Run before each deployment to catch security regressions")
    
    print("\n📝 Next steps:")
    print("   1. Review findings in JSON reports")
    print("   2. Fix critical/high severity issues")
    print("   3. Document accepted risks for low severity issues")
    print("   4. Run 'npm audit' in Rekapo_admin/ and ProgresstifyFrontEnd/ for frontend security")


if __name__ == "__main__":
    main()

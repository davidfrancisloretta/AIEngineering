#!/usr/bin/env python3
"""
Initialize and run Reflex app with proper Node.js setup
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description=""):
    """Run a shell command and return success status"""
    if description:
        print(f"\n{'='*60}")
        print(f"  {description}")
        print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=os.getcwd())
    if result.returncode != 0:
        print(f"\n⚠️  Command failed with return code {result.returncode}")
        return False
    return True

def main():
    """Initialize and run the Reflex app"""
    app_dir = Path(__file__).parent
    os.chdir(app_dir)

    print("\n" + "="*60)
    print("  RAVE AI - Reflex Application Startup")
    print("="*60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Node.js available: {os.system('node --version > /dev/null 2>&1') == 0}")
    print(f"npm available: {os.system('npm --version > /dev/null 2>&1') == 0}")

    try:
        # Step 1: Check environment
        print("\n[1/3] Checking Reflex installation...")
        if not run_command(["reflex", "--version"], "Checking Reflex version"):
            print("ERROR: Reflex is not properly installed")
            sys.exit(1)

        # Step 2: Initialize Reflex
        print("\n[2/3] Initializing Reflex application...")
        # Reflex init will set up .web directory and frontend dependencies
        result = subprocess.run(
            ["reflex", "init"],
            input="\n\n",  # Send empty inputs to use defaults
            text=True,
            capture_output=False,
            timeout=300  # 5 minute timeout for init
        )

        # Reflex returns 0 on success, 1 on "already initialized" (which is fine)
        if result.returncode not in [0, 1]:
            print(f"\n⚠️  Reflex init exited with code {result.returncode}")
            print("Attempting to continue...")

        # Step 3: Run the app
        print("\n[3/3] Starting Reflex development server...")
        print("Reflex will now start on http://localhost:3000\n")

        # Set environment variable to suppress warnings
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        result = subprocess.run(
            ["reflex", "run", "--env", "dev"],
            env=env
        )

        if result.returncode != 0:
            print(f"\n⚠️  Reflex exited with code {result.returncode}")
            sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

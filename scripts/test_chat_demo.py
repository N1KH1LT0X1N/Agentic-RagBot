"""
Quick demo script to test the chatbot with pre-defined inputs
"""

import subprocess
import sys

# Test inputs
test_cases = [
    "help",  # Show biomarker help
    "glucose 185, HbA1c 8.2, cholesterol 235, triglycerides 210, HDL 38",  # Diabetes case
    "n",  # Don't save report
    "quit"  # Exit
]

print("="*70)
print("CLI Chatbot Demo Test")
print("="*70)
print("\nThis will run the chatbot with pre-defined inputs:")
for i, case in enumerate(test_cases, 1):
    print(f"  {i}. {case}")
print("\n" + "="*70 + "\n")

# Prepare input string
input_str = "\n".join(test_cases) + "\n"

# Run the chatbot with piped input
try:
    result = subprocess.run(
        [sys.executable, "scripts/chat.py"],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=120,
        encoding='utf-8',
        errors='replace'
    )

    print("STDOUT:")
    print(result.stdout)

    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)

    print(f"\nExit code: {result.returncode}")

except subprocess.TimeoutExpired:
    print("⚠️ Test timed out after 120 seconds")
except Exception as e:
    print(f"❌ Error running test: {e}")

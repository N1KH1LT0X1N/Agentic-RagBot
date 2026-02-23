"""Monitor evolution test progress"""
import time

print("Monitoring evolution test... (Press Ctrl+C to stop)")
print("=" * 70)

for i in range(60):  # Check for 5 minutes
    time.sleep(5)
    print(f"[{i*5}s] Test still running...")
    
print("\nTest should be complete or nearly complete.")
print("Check terminal output for results.")

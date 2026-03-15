# Locust configuration for load testing

# Import the test classes
from load_test import MediGuardUser, StressTestUser, SpikeTestUser

# Test configurations
class BasicLoadTest:
    user_classes = [MediGuardUser]
    host = "http://localhost:8000"
    num_users = 50
    hatch_rate = 5
    run_time = "5m"
    wait_time = between(1, 3)


class StressTest:
    user_classes = [StressTestUser, MediGuardUser]
    host = "http://localhost:8000"
    num_users = 200
    hatch_rate = 20
    run_time = "10m"
    wait_time = between(0.1, 0.5)


class SpikeTest:
    user_classes = [SpikeTestUser]
    host = "http://localhost:8000"
    num_users = 500
    hatch_rate = 100
    run_time = "2m"
    wait_time = between(0.01, 0.1)


class EnduranceTest:
    user_classes = [MediGuardUser]
    host = "http://localhost:8000"
    num_users = 100
    hatch_rate = 10
    run_time = "1h"
    wait_time = between(1, 3)


# Export for CLI usage
__all__ = ["MediGuardUser", "StressTestUser", "SpikeTestUser"]

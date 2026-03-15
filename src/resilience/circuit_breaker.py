"""
Circuit Breaker Pattern Implementation for MediGuard AI.
Provides fault tolerance and resilience for external service calls.
"""

import asyncio
import logging
import random
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CallResult:
    """Result of a circuit breaker call."""

    def __init__(self, success: bool, duration: float, error: Exception | None = None):
        self.success = success
        self.duration = duration
        self.error = error
        self.timestamp = time.time()


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception that counts as failure
    success_threshold: int = 3          # Successes needed to close circuit
    timeout: float = 30.0               # Call timeout in seconds
    max_retries: int = 3                # Maximum retry attempts
    retry_delay: float = 1.0            # Delay between retries
    fallback_function: Callable | None = None
    monitor_window: int = 100           # Number of calls to monitor
    slow_call_threshold: float = 5.0    # Duration considered "slow"
    metrics_enabled: bool = True
    name: str = "default"


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    slow_calls: int = 0
    timeouts: int = 0
    short_circuits: int = 0
    fallback_calls: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    call_history: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_call(self, result: CallResult):
        """Record a call result."""
        self.total_calls += 1
        self.call_history.append(result)

        if result.success:
            self.successful_calls += 1
            self.last_success_time = result.timestamp
        else:
            self.failed_calls += 1
            self.last_failure_time = result.timestamp

        if result.duration > 5.0:  # Slow call threshold
            self.slow_calls += 1

    def get_success_rate(self) -> float:
        """Get success rate percentage."""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100

    def get_average_duration(self) -> float:
        """Get average call duration."""
        if not self.call_history:
            return 0.0
        return sum(call.duration for call in self.call_history) / len(self.call_history)

    def get_recent_failures(self, window: int = 10) -> int:
        """Get number of failures in recent calls."""
        recent_calls = list(self.call_history)[-window:]
        return sum(1 for call in recent_calls if not call.success)


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.last_state_change = time.time()
        self.half_open_successes = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_successes = 0
                    logger.info(f"Circuit breaker {self.config.name} transitioning to HALF_OPEN")
                else:
                    self.metrics.short_circuits += 1
                    if self.config.fallback_function:
                        self.metrics.fallback_calls += 1
                        return await self._execute_fallback(*args, **kwargs)
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker {self.config.name} is OPEN"
                    )

        # Execute the call
        start_time = time.time()
        result = None
        error = None

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: func(*args, **kwargs)
                )

            # Record success
            duration = time.time() - start_time
            call_result = CallResult(success=True, duration=duration)
            self._on_success(call_result)

            return result

        except TimeoutError:
            duration = time.time() - start_time
            error = TimeoutError(f"Call timed out after {self.config.timeout}s")
            call_result = CallResult(success=False, duration=duration, error=error)
            self._on_failure(call_result)

        except self.config.expected_exception as e:
            duration = time.time() - start_time
            call_result = CallResult(success=False, duration=duration, error=e)
            self._on_failure(call_result)
            error = e

        except Exception as e:
            # Unexpected exception - still count as failure
            duration = time.time() - start_time
            call_result = CallResult(success=False, duration=duration, error=e)
            self._on_failure(call_result)
            error = e

        # Return fallback if available
        if error and self.config.fallback_function:
            self.metrics.fallback_calls += 1
            return await self._execute_fallback(*args, **kwargs)

        raise error

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset."""
        return time.time() - self.last_state_change >= self.config.recovery_timeout

    def _on_success(self, result: CallResult):
        """Handle successful call."""
        self.metrics.record_call(result)

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()
                logger.info(f"Circuit breaker {self.config.name} CLOSED after recovery")

    def _on_failure(self, result: CallResult):
        """Handle failed call."""
        self.metrics.record_call(result)

        if self.state == CircuitState.CLOSED:
            if self.metrics.get_recent_failures() >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()
                logger.warning(f"Circuit breaker {self.config.name} OPENED due to failures")

        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(f"Circuit breaker {self.config.name} OPENED again during HALF_OPEN")

    async def _execute_fallback(self, *args, **kwargs) -> Any:
        """Execute fallback function."""
        if asyncio.iscoroutinefunction(self.config.fallback_function):
            return await self.config.fallback_function(*args, **kwargs)
        else:
            return self.config.fallback_function(*args, **kwargs)

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_metrics(self) -> dict[str, Any]:
        """Get circuit metrics."""
        return {
            "state": self.state.value,
            "total_calls": self.metrics.total_calls,
            "successful_calls": self.metrics.successful_calls,
            "failed_calls": self.metrics.failed_calls,
            "slow_calls": self.metrics.slow_calls,
            "timeouts": self.metrics.timeouts,
            "short_circuits": self.metrics.short_circuits,
            "fallback_calls": self.metrics.fallback_calls,
            "success_rate": self.metrics.get_success_rate(),
            "average_duration": self.metrics.get_average_duration(),
            "last_failure_time": self.metrics.last_failure_time,
            "last_success_time": self.metrics.last_success_time
        }

    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.last_state_change = time.time()
        self.half_open_successes = 0
        logger.info(f"Circuit breaker {self.config.name} RESET")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

    def register(self, name: str, circuit_breaker: CircuitBreaker):
        """Register a circuit breaker."""
        self.circuit_breakers[name] = circuit_breaker

    def get(self, name: str) -> CircuitBreaker | None:
        """Get a circuit breaker by name."""
        return self.circuit_breakers.get(name)

    def create(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create and register a circuit breaker."""
        circuit_breaker = CircuitBreaker(config)
        self.register(name, circuit_breaker)
        return circuit_breaker

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: cb.get_metrics()
            for name, cb in self.circuit_breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            cb.reset()


# Global registry
_circuit_registry = CircuitBreakerRegistry()


def get_circuit_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    return _circuit_registry


def circuit_breaker(
    name: str = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception,
    success_threshold: int = 3,
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    fallback_function: Callable = None
):
    """Decorator for circuit breaker protection."""
    def decorator(func):
        circuit_name = name or f"{func.__module__}.{func.__name__}"

        # Get or create circuit breaker
        circuit = _circuit_registry.get(circuit_name)
        if not circuit:
            config = CircuitBreakerConfig(
                name=circuit_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                success_threshold=success_threshold,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
                fallback_function=fallback_function
            )
            circuit = _circuit_registry.create(circuit_name, config)

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await circuit.call(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            async def sync_wrapper(*args, **kwargs):
                return await circuit.call(func, *args, **kwargs)
            return sync_wrapper

    return decorator


class Bulkhead:
    """Bulkhead pattern implementation for resource isolation."""

    def __init__(self, max_concurrent: int, max_queue: int = 100):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = asyncio.Queue(maxsize=max_queue)
        self.active_tasks = set()
        self.metrics = {
            "total_requests": 0,
            "rejected_requests": 0,
            "active_tasks": 0,
            "max_active": 0
        }

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with bulkhead protection."""
        self.metrics["total_requests"] += 1

        try:
            # Try to acquire semaphore
            await self.semaphore.acquire()

            # Track active task
            task_id = id(asyncio.current_task())
            self.active_tasks.add(task_id)
            self.metrics["active_tasks"] = len(self.active_tasks)
            self.metrics["max_active"] = max(
                self.metrics["max_active"],
                self.metrics["active_tasks"]
            )

            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: func(*args, **kwargs)
                    )
            finally:
                self.active_tasks.discard(task_id)
                self.metrics["active_tasks"] = len(self.active_tasks)
                self.semaphore.release()

        except TimeoutError:
            self.metrics["rejected_requests"] += 1
            raise BulkheadFullException("Bulkhead is full")

    def get_metrics(self) -> dict[str, Any]:
        """Get bulkhead metrics."""
        return self.metrics.copy()


class BulkheadFullException(Exception):
    """Exception raised when bulkhead is full."""
    pass


class Retry:
    """Retry mechanism with exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: func(*args, **kwargs)
                    )
            except Exception as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.max_attempts} "
                        f"after {delay:.2f}s delay. Error: {e}"
                    )

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add randomness to prevent thundering herd
            delay *= (0.5 + random.random() * 0.5)

        return delay


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """Decorator for retry mechanism."""
    def decorator(func):
        retry_mechanism = Retry(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter
        )

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_mechanism.execute(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            async def sync_wrapper(*args, **kwargs):
                return await retry_mechanism.execute(func, *args, **kwargs)
            return sync_wrapper

    return decorator


# Combined resilience patterns
class ResilienceChain:
    """Chain multiple resilience patterns together."""

    def __init__(self, patterns: list[Any]):
        self.patterns = patterns

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through all patterns."""
        async def execute_with_patterns():
            # Apply patterns in reverse order (decorator-like)
            result = func
            for pattern in reversed(self.patterns):
                if isinstance(pattern, CircuitBreaker):
                    result = lambda f=result, p=pattern: p.call(f, *args, **kwargs)
                elif isinstance(pattern, Retry) or isinstance(pattern, Bulkhead):
                    result = lambda f=result, p=pattern: p.execute(f, *args, **kwargs)

            return await result()

        return await execute_with_patterns()


# Example usage and fallback functions
async def default_fallback(*args, **kwargs) -> Any:
    """Default fallback function."""
    logger.warning("Using default fallback")
    return {"error": "Service temporarily unavailable", "fallback": True}


async def cache_fallback(*args, **kwargs) -> Any:
    """Fallback that returns cached data if available."""
    # This would implement cache-based fallback
    logger.info("Attempting cache fallback")
    return {"data": None, "cached": False, "message": "No cached data available"}


# Health check for circuit breakers
async def get_circuit_breaker_health() -> dict[str, Any]:
    """Get health status of all circuit breakers."""
    registry = get_circuit_registry()

    healthy = True
    details = {}

    for name, cb in registry.circuit_breakers.items():
        metrics = cb.get_metrics()
        state = metrics["state"]

        if state == "open":
            healthy = False

        details[name] = {
            "state": state,
            "success_rate": metrics["success_rate"],
            "total_calls": metrics["total_calls"]
        }

    return {
        "healthy": healthy,
        "circuit_breakers": details
    }

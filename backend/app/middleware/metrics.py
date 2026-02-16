"""
Prometheus-compatible metrics for monitoring.

Generates metrics in Prometheus text exposition format without
requiring the prometheus_client library. All metric collection
is thread-safe via threading.Lock.

Tracked metrics:
- http_requests_total (counter) - by method, endpoint, status_code
- http_request_duration_seconds (histogram) - by method, endpoint
- http_requests_in_progress (gauge) - by method
- llm_requests_total (counter) - by provider, operation, status
- llm_request_duration_seconds (histogram) - by provider, operation
- active_users_total (gauge) - users active in last 15 min
- rate_limit_hits_total (counter) - by limit_type
"""

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsCollector:
    """Thread-safe metrics collector generating Prometheus text exposition format."""

    # Standard histogram buckets (seconds)
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    # Metric descriptions for HELP lines
    METRIC_HELP = {
        "http_requests_total": "Total number of HTTP requests",
        "http_request_duration_seconds": "HTTP request duration in seconds",
        "http_requests_in_progress": "Number of HTTP requests currently being processed",
        "llm_requests_total": "Total number of LLM provider requests",
        "llm_request_duration_seconds": "LLM request duration in seconds",
        "active_users_total": "Number of users active in the last 15 minutes",
        "rate_limit_hits_total": "Total number of rate limit hits",
        "process_uptime_seconds": "Time since process start in seconds",
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, Dict[Tuple, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._histograms: Dict[str, List[Tuple[Tuple, float]]] = defaultdict(list)
        self._gauges: Dict[str, Dict[Tuple, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Counter operations
    # ------------------------------------------------------------------

    def inc_counter(self, name: str, labels: dict, value: int = 1) -> None:
        """Increment a counter metric."""
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._counters[name][key] += value

    # ------------------------------------------------------------------
    # Histogram operations
    # ------------------------------------------------------------------

    def observe_histogram(self, name: str, labels: dict, value: float) -> None:
        """Record a histogram observation."""
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._histograms[name].append((key, value))

    # ------------------------------------------------------------------
    # Gauge operations
    # ------------------------------------------------------------------

    def set_gauge(self, name: str, labels: dict, value: float) -> None:
        """Set a gauge value."""
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._gauges[name][key] = value

    def inc_gauge(self, name: str, labels: dict, value: float = 1) -> None:
        """Increment a gauge value."""
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._gauges[name][key] += value

    def dec_gauge(self, name: str, labels: dict, value: float = 1) -> None:
        """Decrement a gauge value."""
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._gauges[name][key] -= value

    # ------------------------------------------------------------------
    # Convenience helpers for domain-specific metrics
    # ------------------------------------------------------------------

    def record_llm_request(
        self,
        provider: str,
        operation: str,
        status: str,
        duration: float,
    ) -> None:
        """Record an LLM provider request with count and duration.

        Args:
            provider: LLM provider name (e.g. openai, anthropic, google, ollama).
            operation: Operation type (e.g. tailor_resume, generate_cover_letter).
            status: Outcome status (e.g. success, error, timeout).
            duration: Request duration in seconds.
        """
        self.inc_counter(
            "llm_requests_total",
            {"provider": provider, "operation": operation, "status": status},
        )
        self.observe_histogram(
            "llm_request_duration_seconds",
            {"provider": provider, "operation": operation},
            duration,
        )

    def set_active_users(self, count: int) -> None:
        """Set the active users gauge.

        Args:
            count: Number of users active in the observation window.
        """
        self.set_gauge("active_users_total", {}, float(count))

    def record_rate_limit_hit(self, limit_type: str) -> None:
        """Increment the rate limit hit counter.

        Args:
            limit_type: The type of rate limit triggered (e.g. general, auth, ai).
        """
        self.inc_counter("rate_limit_hits_total", {"limit_type": limit_type})

    # ------------------------------------------------------------------
    # Prometheus text exposition
    # ------------------------------------------------------------------

    @staticmethod
    def _format_labels(label_tuple: Tuple) -> str:
        """Convert a sorted label tuple to Prometheus label string."""
        if not label_tuple:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in label_tuple)

    def format_prometheus(self) -> str:
        """Generate Prometheus text exposition format.

        Returns a string conforming to the Prometheus text-based exposition
        format (version 0.0.4).
        """
        lines: List[str] = []
        lines.append("# ResuBoost AI Metrics")
        lines.append(
            f"# Generated at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
        )
        lines.append("")

        with self._lock:
            # -- Process uptime gauge (always present) --
            uptime = time.time() - self._start_time
            help_text = self.METRIC_HELP.get(
                "process_uptime_seconds", "Time since process start"
            )
            lines.append(f"# HELP process_uptime_seconds {help_text}")
            lines.append("# TYPE process_uptime_seconds gauge")
            lines.append(f"process_uptime_seconds {uptime:.2f}")
            lines.append("")

            # -- Counters --
            for name, label_values in sorted(self._counters.items()):
                help_text = self.METRIC_HELP.get(name, "Counter metric")
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} counter")
                for labels, value in sorted(label_values.items()):
                    label_str = self._format_labels(labels)
                    lines.append(f"{name}{{{label_str}}} {value}")
                lines.append("")

            # -- Gauges --
            for name, label_values in sorted(self._gauges.items()):
                help_text = self.METRIC_HELP.get(name, "Gauge metric")
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} gauge")
                for labels, value in sorted(label_values.items()):
                    label_str = self._format_labels(labels)
                    if label_str:
                        lines.append(f"{name}{{{label_str}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
                lines.append("")

            # -- Histograms (sum, count, and bucket quantiles) --
            for name, observations in sorted(self._histograms.items()):
                # Group observations by their label set
                grouped: Dict[Tuple, List[float]] = defaultdict(list)
                for labels, value in observations:
                    grouped[labels].append(value)

                help_text = self.METRIC_HELP.get(name, "Histogram metric")
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} histogram")
                for labels, values in sorted(grouped.items()):
                    label_str = self._format_labels(labels)
                    count = len(values)
                    total = sum(values)

                    for bucket in self.DEFAULT_BUCKETS:
                        bucket_count = sum(1 for v in values if v <= bucket)
                        if label_str:
                            lines.append(
                                f'{name}_bucket{{{label_str},le="{bucket}"}} {bucket_count}'
                            )
                        else:
                            lines.append(
                                f'{name}_bucket{{le="{bucket}"}} {bucket_count}'
                            )

                    # +Inf bucket always equals count
                    if label_str:
                        lines.append(
                            f'{name}_bucket{{{label_str},le="+Inf"}} {count}'
                        )
                    else:
                        lines.append(f'{name}_bucket{{le="+Inf"}} {count}')

                    if label_str:
                        lines.append(f"{name}_sum{{{label_str}}} {total:.6f}")
                        lines.append(f"{name}_count{{{label_str}}} {count}")
                    else:
                        lines.append(f"{name}_sum {total:.6f}")
                        lines.append(f"{name}_count {count}")
                lines.append("")

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics


# ---------------------------------------------------------------------------
# HTTP metrics middleware
# ---------------------------------------------------------------------------


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that instruments HTTP requests with Prometheus-style metrics.

    Tracks request count, duration, and in-progress gauge for every request
    except a configurable set of excluded paths (e.g. /metrics itself).

    Label conventions match the specification:
    - http_requests_total: method, endpoint, status_code
    - http_request_duration_seconds: method, endpoint
    - http_requests_in_progress: method
    """

    EXCLUDED_PATHS = {"/metrics", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method

        # Skip instrumentation for utility endpoints
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Collapse numeric path segments to avoid high-cardinality labels
        normalized_endpoint = self._normalize_path(path)

        metrics = get_metrics()
        metrics.inc_gauge("http_requests_in_progress", {"method": method})

        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            status_code = str(response.status_code)

            metrics.inc_counter(
                "http_requests_total",
                {
                    "method": method,
                    "endpoint": normalized_endpoint,
                    "status_code": status_code,
                },
            )
            metrics.observe_histogram(
                "http_request_duration_seconds",
                {"method": method, "endpoint": normalized_endpoint},
                duration,
            )
            return response
        except Exception:
            duration = time.time() - start_time
            metrics.inc_counter(
                "http_requests_total",
                {
                    "method": method,
                    "endpoint": normalized_endpoint,
                    "status_code": "500",
                },
            )
            metrics.observe_histogram(
                "http_request_duration_seconds",
                {"method": method, "endpoint": normalized_endpoint},
                duration,
            )
            raise
        finally:
            metrics.dec_gauge("http_requests_in_progress", {"method": method})

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize URL path to reduce label cardinality.

        Numeric path segments (e.g. ``/api/resumes/42``) are replaced with
        ``:id`` so that per-resource paths do not explode the metric
        cardinality.
        """
        parts = path.strip("/").split("/")
        normalized = []
        for part in parts:
            if part.isdigit():
                normalized.append(":id")
            else:
                normalized.append(part)
        return "/" + "/".join(normalized)

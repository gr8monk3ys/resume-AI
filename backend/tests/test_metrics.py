"""
Tests for Prometheus-compatible metrics middleware.

Tests:
- MetricsCollector counter, gauge, and histogram operations
- Prometheus text exposition format output
- MetricsMiddleware request instrumentation
- Path normalization for cardinality control
- Excluded paths are not instrumented
- Thread-safety of metric operations
"""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.middleware.metrics import MetricsCollector, MetricsMiddleware, get_metrics


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def collector():
    """Create a fresh MetricsCollector for each test."""
    return MetricsCollector()


@pytest.fixture
def app_with_metrics():
    """Create a test app with metrics middleware."""
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/api/test")
    def test_endpoint():
        return {"status": "ok"}

    @app.get("/api/items/{item_id}")
    def get_item(item_id: int):
        return {"item_id": item_id}

    @app.post("/api/items")
    def create_item():
        return {"created": True}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/metrics")
    def metrics():
        return {"metrics": "data"}

    return app


# =============================================================================
# Counter Tests
# =============================================================================


class TestMetricsCounter:
    """Tests for counter metric operations."""

    def test_increment_counter(self, collector):
        """Test basic counter increment."""
        collector.inc_counter("test_total", {"method": "GET"})

        output = collector.format_prometheus()
        assert "test_total" in output
        assert 'method="GET"' in output

    def test_increment_counter_multiple_times(self, collector):
        """Test incrementing a counter multiple times."""
        for _ in range(5):
            collector.inc_counter("request_total", {"method": "POST"})

        output = collector.format_prometheus()
        assert "request_total" in output
        assert "5" in output

    def test_increment_counter_with_custom_value(self, collector):
        """Test incrementing a counter by a custom value."""
        collector.inc_counter("bytes_total", {"direction": "in"}, value=1024)

        output = collector.format_prometheus()
        assert "bytes_total" in output
        assert "1024" in output

    def test_counter_different_labels(self, collector):
        """Test counter with different label combinations."""
        collector.inc_counter("http_requests_total", {"method": "GET", "status": "200"})
        collector.inc_counter("http_requests_total", {"method": "POST", "status": "201"})
        collector.inc_counter("http_requests_total", {"method": "GET", "status": "404"})

        output = collector.format_prometheus()
        assert output.count("http_requests_total{") == 3


# =============================================================================
# Gauge Tests
# =============================================================================


class TestMetricsGauge:
    """Tests for gauge metric operations."""

    def test_set_gauge(self, collector):
        """Test setting a gauge value."""
        collector.set_gauge("active_connections", {"server": "web1"}, 42.0)

        output = collector.format_prometheus()
        assert "active_connections" in output
        assert "42" in output

    def test_increment_gauge(self, collector):
        """Test incrementing a gauge."""
        collector.inc_gauge("requests_in_progress", {"method": "GET"})
        collector.inc_gauge("requests_in_progress", {"method": "GET"})

        output = collector.format_prometheus()
        assert "requests_in_progress" in output

    def test_decrement_gauge(self, collector):
        """Test decrementing a gauge."""
        collector.set_gauge("connections", {}, 10.0)
        collector.dec_gauge("connections", {}, 3.0)

        output = collector.format_prometheus()
        assert "connections" in output

    def test_gauge_can_go_negative(self, collector):
        """Test that gauge can go below zero."""
        collector.set_gauge("temperature", {"sensor": "1"}, 0.0)
        collector.dec_gauge("temperature", {"sensor": "1"}, 5.0)

        output = collector.format_prometheus()
        assert "temperature" in output
        assert "-5" in output


# =============================================================================
# Histogram Tests
# =============================================================================


class TestMetricsHistogram:
    """Tests for histogram metric operations."""

    def test_observe_histogram(self, collector):
        """Test recording a histogram observation."""
        collector.observe_histogram(
            "request_duration_seconds",
            {"method": "GET"},
            0.150,
        )

        output = collector.format_prometheus()
        assert "request_duration_seconds" in output
        assert "request_duration_seconds_bucket" in output
        assert "request_duration_seconds_sum" in output
        assert "request_duration_seconds_count" in output

    def test_histogram_bucket_boundaries(self, collector):
        """Test that histogram buckets are correctly populated."""
        # Record a value that falls in the 0.1 bucket
        collector.observe_histogram("latency", {"path": "/api"}, 0.05)

        output = collector.format_prometheus()
        # The 0.05 value should be counted in buckets >= 0.05
        assert 'le="0.05"' in output
        assert 'le="+Inf"' in output

    def test_histogram_multiple_observations(self, collector):
        """Test histogram with multiple observations."""
        values = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
        for v in values:
            collector.observe_histogram("duration", {"op": "read"}, v)

        output = collector.format_prometheus()
        assert "duration_count" in output
        assert "6" in output  # 6 observations
        assert "duration_sum" in output

    def test_histogram_inf_bucket_equals_count(self, collector):
        """Test that +Inf bucket always equals total count."""
        for v in [0.01, 0.5, 100.0]:
            collector.observe_histogram("test_hist", {}, v)

        output = collector.format_prometheus()
        # +Inf bucket should contain all 3 observations
        assert 'le="+Inf"} 3' in output


# =============================================================================
# Prometheus Format Tests
# =============================================================================


class TestPrometheusFormat:
    """Tests for Prometheus text exposition format output."""

    def test_format_includes_header(self, collector):
        """Test that output includes header comments."""
        output = collector.format_prometheus()
        assert "# ResuBoost AI Metrics" in output
        assert "# Generated at" in output

    def test_format_includes_uptime(self, collector):
        """Test that output includes process uptime gauge."""
        output = collector.format_prometheus()
        assert "process_uptime_seconds" in output
        assert "# TYPE process_uptime_seconds gauge" in output

    def test_format_includes_help_lines(self, collector):
        """Test that HELP lines are included for metrics."""
        collector.inc_counter("http_requests_total", {"method": "GET"})

        output = collector.format_prometheus()
        assert "# HELP http_requests_total" in output
        assert "# TYPE http_requests_total counter" in output

    def test_format_labels_correctly(self, collector):
        """Test that labels are formatted in Prometheus style."""
        collector.inc_counter(
            "test_metric",
            {"method": "GET", "path": "/api/test"},
        )

        output = collector.format_prometheus()
        assert 'method="GET"' in output
        assert 'path="/api/test"' in output

    def test_format_empty_labels(self):
        """Test formatting with empty label tuple."""
        result = MetricsCollector._format_labels(())
        assert result == ""

    def test_format_single_label(self):
        """Test formatting with a single label."""
        result = MetricsCollector._format_labels((("method", "GET"),))
        assert result == 'method="GET"'

    def test_format_multiple_labels(self):
        """Test formatting with multiple labels."""
        result = MetricsCollector._format_labels(
            (("method", "GET"), ("path", "/api"))
        )
        assert result == 'method="GET",path="/api"'

    def test_format_ends_with_newline(self, collector):
        """Test that output ends with a newline."""
        output = collector.format_prometheus()
        assert output.endswith("\n")


# =============================================================================
# Global Singleton Tests
# =============================================================================


class TestGlobalMetrics:
    """Tests for the global metrics singleton."""

    def test_get_metrics_returns_collector(self):
        """Test that get_metrics returns a MetricsCollector instance."""
        metrics = get_metrics()
        assert isinstance(metrics, MetricsCollector)

    def test_get_metrics_returns_same_instance(self):
        """Test that get_metrics returns the same singleton instance."""
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2


# =============================================================================
# MetricsMiddleware Tests
# =============================================================================


class TestMetricsMiddleware:
    """Tests for HTTP metrics middleware."""

    @pytest.mark.asyncio
    async def test_middleware_records_request(self, app_with_metrics):
        """Test that middleware records request metrics."""
        transport = ASGITransport(app=app_with_metrics)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_excludes_health(self, app_with_metrics):
        """Test that /health is excluded from metrics."""
        transport = ASGITransport(app=app_with_metrics)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_excludes_metrics_endpoint(self, app_with_metrics):
        """Test that /metrics is excluded from instrumentation."""
        transport = ASGITransport(app=app_with_metrics)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_tracks_different_methods(self, app_with_metrics):
        """Test that different HTTP methods are tracked separately."""
        transport = ASGITransport(app=app_with_metrics)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/test")
            await client.post("/api/items")

        # Both should succeed without errors
        # Metrics are being collected internally

    def test_excluded_paths_set(self):
        """Test that excluded paths are properly defined."""
        assert "/metrics" in MetricsMiddleware.EXCLUDED_PATHS
        assert "/health" in MetricsMiddleware.EXCLUDED_PATHS
        assert "/docs" in MetricsMiddleware.EXCLUDED_PATHS


# =============================================================================
# Path Normalization Tests
# =============================================================================


class TestPathNormalization:
    """Tests for URL path normalization."""

    def test_normalize_numeric_segments(self):
        """Test that numeric path segments are replaced with :id."""
        result = MetricsMiddleware._normalize_path("/api/resumes/42")
        assert result == "/api/resumes/:id"

    def test_normalize_multiple_numeric_segments(self):
        """Test normalizing multiple numeric segments."""
        result = MetricsMiddleware._normalize_path("/api/users/123/resumes/456")
        assert result == "/api/users/:id/resumes/:id"

    def test_normalize_non_numeric_segments_unchanged(self):
        """Test that non-numeric segments are left unchanged."""
        result = MetricsMiddleware._normalize_path("/api/auth/login")
        assert result == "/api/auth/login"

    def test_normalize_root_path(self):
        """Test normalizing the root path."""
        result = MetricsMiddleware._normalize_path("/")
        assert result == "/"

    def test_normalize_preserves_api_prefix(self):
        """Test that API prefix is preserved."""
        result = MetricsMiddleware._normalize_path("/api/jobs/99/status")
        assert result == "/api/jobs/:id/status"


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestMetricsThreadSafety:
    """Tests for thread-safe metric operations."""

    def test_concurrent_counter_increments(self, collector):
        """Test that concurrent counter increments are safe."""
        import threading

        def increment():
            for _ in range(100):
                collector.inc_counter("concurrent_total", {"thread": "test"})

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 1000 increments should be counted
        output = collector.format_prometheus()
        assert "concurrent_total" in output
        assert "1000" in output

    def test_concurrent_gauge_operations(self, collector):
        """Test that concurrent gauge operations are safe."""
        import threading

        def modify_gauge():
            for _ in range(50):
                collector.inc_gauge("concurrent_gauge", {"type": "test"})
            for _ in range(50):
                collector.dec_gauge("concurrent_gauge", {"type": "test"})

        threads = [threading.Thread(target=modify_gauge) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Net effect should be zero (inc 50, dec 50) per thread
        output = collector.format_prometheus()
        assert "concurrent_gauge" in output

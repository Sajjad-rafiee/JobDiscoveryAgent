"""Optional OpenTelemetry tracing, off by default.

`init_telemetry()` is a no-op unless `OTEL_TRACES_EXPORTER=otlp`. When it is a
no-op, every span created via `get_tracer()` uses the OpenTelemetry API's
default no-op tracer provider — spans are cheap, inert objects with no
exporter and no network calls. This is what keeps tracing safe to leave
wired into the code path without requiring Jaeger for normal use or tests.

Propagation uses OpenTelemetry's default W3C Trace Context + Baggage
propagators; no custom propagation code is needed.
"""

import atexit
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

DEFAULT_SERVICE_NAME = "job-discovery-agent"

_enabled: bool | None = None


def init_telemetry() -> bool:
    """Configure the OpenTelemetry SDK if tracing is enabled. Idempotent.

    Returns whether tracing is enabled. Safe to call more than once (later
    calls just return the result of the first call) and safe to never call.
    """
    global _enabled
    if _enabled is not None:
        return _enabled

    if os.environ.get("OTEL_TRACES_EXPORTER", "").strip().lower() != "otlp":
        _enabled = False
        return False

    service_name = os.environ.get("OTEL_SERVICE_NAME", DEFAULT_SERVICE_NAME)
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    # BatchSpanProcessor exports on a timer in a background thread; a
    # short-lived CLI run can otherwise exit before it ever flushes.
    atexit.register(provider.shutdown)

    HTTPXClientInstrumentor().instrument()

    _enabled = True
    return True


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(DEFAULT_SERVICE_NAME)

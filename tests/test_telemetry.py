from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from langchain_core.messages import AIMessage

import utils.telemetry as telemetry_module
from agent import graph as graph_module
from agent.runtime import invoke_agent
from models.job import JobSearchResult
from tests.backend_samples import search_result_json
from tools import job_search as job_search_module


class PlainAnswerModel:
    def invoke(self, messages):
        return AIMessage(content="Hello! How can I help you?")


class ToolCallThenAnswerModel:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_jobs",
                        "args": {"query": "AI Engineer", "location": "Berlin"},
                        "id": "call_1",
                    }
                ],
            )
        return AIMessage(content="Here are some AI Engineer jobs in Berlin.")


class BackendShapedSearchClient:
    def search_jobs(self, query):
        return JobSearchResult.from_api_response(
            [search_result_json(title="AI Engineer", description="SECRET_JOB_DESCRIPTION")]
        )

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def _reset_global_tracer_provider(monkeypatch):
    """Undo OpenTelemetry's process-wide "set once" latch on the tracer provider.

    `trace.set_tracer_provider()` is guarded by an internal `Once` object, not
    just the `_TRACER_PROVIDER` variable — resetting only the variable still
    leaves later calls silently ignored. Both must be reset per test so each
    test gets its own real provider instead of a leftover from a prior test.
    """
    monkeypatch.setattr(trace, "_TRACER_PROVIDER", None)
    monkeypatch.setattr(trace, "_TRACER_PROVIDER_SET_ONCE", trace.Once())


def _real_tracer_provider(monkeypatch):
    """Install a real TracerProvider backed by an in-memory exporter.

    Bypasses init_telemetry()'s OTLP/env-driven setup entirely, so these
    tests never touch the network or need Jaeger, while still exercising
    real span creation/attribute recording.
    """
    _reset_global_tracer_provider(monkeypatch)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def _spans_by_name(exporter, name):
    return [s for s in exporter.get_finished_spans() if s.name == name]


def _set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")


def test_init_telemetry_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(telemetry_module, "_enabled", None)
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)

    assert telemetry_module.init_telemetry() is False


def _stub_out_network_exporter(monkeypatch):
    """Replace the real OTLP exporter/batch processor with in-process no-ops.

    init_telemetry() normally builds a BatchSpanProcessor around a real
    OTLPSpanExporter, which spawns a background thread that retries against
    a real endpoint (slow, and not something a unit test should depend on).
    These tests only need to verify init_telemetry()'s own control flow —
    env check, resource/provider setup, HTTPX instrumentation — not that
    spans actually reach a collector.
    """
    monkeypatch.setattr(telemetry_module, "OTLPSpanExporter", lambda: InMemorySpanExporter())
    monkeypatch.setattr(telemetry_module, "BatchSpanProcessor", SimpleSpanProcessor)


def test_init_telemetry_enables_when_configured(monkeypatch):
    monkeypatch.setattr(telemetry_module, "_enabled", None)
    _reset_global_tracer_provider(monkeypatch)
    _stub_out_network_exporter(monkeypatch)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")

    try:
        assert telemetry_module.init_telemetry() is True
    finally:
        HTTPXClientInstrumentor().uninstrument()


def test_init_telemetry_registers_shutdown_at_exit(monkeypatch):
    """A short-lived CLI run must still flush pending spans before exiting —
    BatchSpanProcessor otherwise only exports on a background timer."""
    monkeypatch.setattr(telemetry_module, "_enabled", None)
    _reset_global_tracer_provider(monkeypatch)
    _stub_out_network_exporter(monkeypatch)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")

    registered = []
    monkeypatch.setattr("atexit.register", lambda fn: registered.append(fn))

    try:
        telemetry_module.init_telemetry()
        provider = trace.get_tracer_provider()

        assert provider.shutdown in registered
    finally:
        HTTPXClientInstrumentor().uninstrument()


def test_init_telemetry_is_idempotent(monkeypatch):
    monkeypatch.setattr(telemetry_module, "_enabled", None)
    _reset_global_tracer_provider(monkeypatch)
    _stub_out_network_exporter(monkeypatch)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")

    try:
        telemetry_module.init_telemetry()
        provider_after_first_call = trace.get_tracer_provider()

        telemetry_module.init_telemetry()

        assert trace.get_tracer_provider() is provider_after_first_call
    finally:
        HTTPXClientInstrumentor().uninstrument()


def test_invoke_agent_creates_invoke_agent_and_chat_spans(monkeypatch):
    exporter = _real_tracer_provider(monkeypatch)
    _set_gemini_env(monkeypatch)
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: PlainAnswerModel())

    invoke_agent([{"role": "user", "content": "Find AI Engineer jobs in Berlin."}])

    assert len(_spans_by_name(exporter, "invoke_agent")) == 1
    assert len(_spans_by_name(exporter, "chat")) == 1


def test_invoke_agent_span_has_safe_operation_attribute(monkeypatch):
    exporter = _real_tracer_provider(monkeypatch)
    _set_gemini_env(monkeypatch)
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: PlainAnswerModel())

    invoke_agent([{"role": "user", "content": "hi"}])

    [span] = _spans_by_name(exporter, "invoke_agent")
    assert span.attributes["gen_ai.operation.name"] == "invoke_agent"


def test_chat_span_records_provider_and_model(monkeypatch):
    exporter = _real_tracer_provider(monkeypatch)
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: PlainAnswerModel())
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    invoke_agent([{"role": "user", "content": "hi"}])

    [span] = _spans_by_name(exporter, "chat")
    assert span.attributes["gen_ai.operation.name"] == "chat"
    assert span.attributes["gen_ai.provider.name"] == "gemini"
    assert span.attributes["gen_ai.request.model"] == "test-model"


def test_tool_loop_creates_execute_tool_span_with_safe_attributes(monkeypatch):
    exporter = _real_tracer_provider(monkeypatch)
    _set_gemini_env(monkeypatch)
    model = ToolCallThenAnswerModel()
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: model)
    monkeypatch.setattr(job_search_module, "get_search_client", BackendShapedSearchClient)

    invoke_agent([{"role": "user", "content": "Find AI Engineer jobs in Berlin."}])

    [span] = _spans_by_name(exporter, "execute_tool")
    assert span.attributes["gen_ai.operation.name"] == "execute_tool"
    assert span.attributes["tool.name"] == "search_jobs"
    assert span.attributes["tool.call.status"] == "success"
    assert span.attributes["result.count"] == 1


def test_no_span_attribute_contains_sensitive_payloads(monkeypatch):
    exporter = _real_tracer_provider(monkeypatch)
    _set_gemini_env(monkeypatch)
    model = ToolCallThenAnswerModel()
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: model)
    monkeypatch.setattr(job_search_module, "get_search_client", BackendShapedSearchClient)

    invoke_agent(
        [{"role": "user", "content": "SECRET_USER_PROMPT: find AI Engineer jobs in Berlin."}]
    )

    forbidden = ("SECRET_USER_PROMPT", "SECRET_JOB_DESCRIPTION", "Here are some AI Engineer")
    for span in exporter.get_finished_spans():
        for value in span.attributes.values():
            text = str(value)
            for marker in forbidden:
                assert marker not in text, f"{marker!r} leaked into span {span.name!r}"


def test_execute_tool_span_marks_errors(monkeypatch):
    from api.client import CareerAPIError

    class FailingClient:
        def search_jobs(self, query):
            raise CareerAPIError("boom")

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()

    exporter = _real_tracer_provider(monkeypatch)
    _set_gemini_env(monkeypatch)
    model = ToolCallThenAnswerModel()
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: model)
    monkeypatch.setattr(job_search_module, "get_search_client", FailingClient)

    invoke_agent([{"role": "user", "content": "Find AI Engineer jobs in Berlin."}])

    [span] = _spans_by_name(exporter, "execute_tool")
    assert span.attributes["tool.call.status"] == "error"
    assert "result.count" not in span.attributes


def test_httpx_instrumentation_creates_client_span(monkeypatch):
    # HTTPXClientInstrumentor wraps httpx's real HTTPTransport.handle_request,
    # not arbitrary transports — httpx.MockTransport bypasses that class
    # entirely, so it can never produce a span here. A real (local, loopback)
    # HTTP server is the honest way to exercise this instrumentation.
    import http.server
    import threading

    import httpx

    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    exporter = _real_tracer_provider(monkeypatch)
    HTTPXClientInstrumentor().instrument()
    try:
        with httpx.Client() as client:
            client.get(f"http://127.0.0.1:{server.server_port}/ping")
    finally:
        HTTPXClientInstrumentor().uninstrument()
        server.shutdown()
        thread.join(timeout=5)

    client_spans = [s for s in exporter.get_finished_spans() if s.kind.name == "CLIENT"]
    assert len(client_spans) == 1
    assert client_spans[0].attributes.get("http.status_code") == 501

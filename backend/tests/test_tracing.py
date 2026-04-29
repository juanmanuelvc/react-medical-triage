"""Unit tests for backend/tracing/otel.py.

Uses InMemorySpanExporter so no real OTLP endpoint is needed.
"""

import datetime
from unittest.mock import MagicMock, patch

import litellm
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tracing.otel import get_tracer, setup_tracing

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_in_memory_provider() -> tuple[TracerProvider, InMemorySpanExporter]:
    """Return a TracerProvider that captures spans in memory."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


# ---------------------------------------------------------------------------
# setup_tracing
# ---------------------------------------------------------------------------


def test_setup_tracing_sets_global_tracer_provider():
    """setup_tracing() replaces the default (NoOp) global TracerProvider."""
    original_provider = trace.get_tracer_provider()

    with patch("tracing.otel.OTLPSpanExporter"):
        setup_tracing()

    provider_after = trace.get_tracer_provider()
    assert provider_after is not original_provider
    assert isinstance(provider_after, TracerProvider)

    # Restore so other tests are not affected.
    trace.set_tracer_provider(original_provider)


def test_setup_tracing_registers_litellm_callback():
    """setup_tracing() appends the OTel callback to litellm.callbacks."""
    original_callbacks = list(litellm.callbacks)

    with patch("tracing.otel.OTLPSpanExporter"):
        setup_tracing()

    assert len(litellm.callbacks) > len(original_callbacks)

    # Restore.
    litellm.callbacks = original_callbacks


# ---------------------------------------------------------------------------
# LiteLLM callback hook
# ---------------------------------------------------------------------------


def test_otel_callback_sets_llm_attributes_on_current_span():
    """The LiteLLM success callback records llm.* attributes on the active span."""
    from tracing.otel import _OtelLiteLLMCallback

    provider, exporter = _make_in_memory_provider()
    tracer = provider.get_tracer("test")

    callback = _OtelLiteLLMCallback()

    start_time = datetime.datetime(2024, 1, 1, 0, 0, 0)
    end_time = datetime.datetime(2024, 1, 1, 0, 0, 1)  # 1 second later

    response_obj = MagicMock()
    response_obj.usage.prompt_tokens = 42
    response_obj.usage.completion_tokens = 10

    kwargs = {"model": "openai/qwen2.5-0.5B-Instruct"}

    with tracer.start_as_current_span("test_span"):
        callback.log_success_event(kwargs, response_obj, start_time, end_time)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs is not None
    assert attrs["llm.model"] == "openai/qwen2.5-0.5B-Instruct"
    assert attrs["llm.tokens_prompt"] == 42
    assert attrs["llm.tokens_completion"] == 10
    assert attrs["llm.latency_ms"] == pytest.approx(1000.0, abs=1.0)


def test_otel_callback_noop_when_no_active_span():
    """The callback does not crash when there is no active span."""
    from tracing.otel import _OtelLiteLLMCallback

    callback = _OtelLiteLLMCallback()
    response_obj = MagicMock()
    response_obj.usage.prompt_tokens = 5
    response_obj.usage.completion_tokens = 3
    kwargs = {"model": "openai/test"}
    start_time = datetime.datetime(2024, 1, 1)
    end_time = datetime.datetime(2024, 1, 1, 0, 0, 1)

    # Must not raise even without an active span context.
    callback.log_success_event(kwargs, response_obj, start_time, end_time)


# ---------------------------------------------------------------------------
# get_tracer
# ---------------------------------------------------------------------------


def test_get_tracer_returns_tracer():
    """get_tracer() returns a usable Tracer instance."""
    tracer = get_tracer()
    assert tracer is not None
    # A Tracer is usable as a context manager.
    with tracer.start_as_current_span("smoke_test") as span:
        assert span is not None

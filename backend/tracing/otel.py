"""OpenTelemetry setup and LiteLLM callback hook for the react-medical-triage service."""

import datetime

import litellm
from litellm.integrations.custom_logger import CustomLogger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from core.config import settings


class _OtelLiteLLMCallback(CustomLogger):
    """LiteLLM callback that writes LLM metrics to the active OTel span."""

    def log_success_event(
        self,
        kwargs: dict,
        response_obj: object,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ) -> None:
        """Record LLM token counts and latency on the current span.

        Args:
            kwargs: LiteLLM call kwargs (contains ``model``).
            response_obj: The LiteLLM response object (has ``.usage``).
            start_time: Wall-clock time the LLM call started.
            end_time: Wall-clock time the LLM call finished.
        """
        span = trace.get_current_span()
        if not span.is_recording():
            return

        usage = getattr(response_obj, "usage", None)
        prompt_tokens: int = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens: int = getattr(usage, "completion_tokens", 0) or 0
        latency_ms: float = (end_time - start_time).total_seconds() * 1000

        span.set_attribute("llm.model", kwargs.get("model", ""))
        span.set_attribute("llm.tokens_prompt", prompt_tokens)
        span.set_attribute("llm.tokens_completion", completion_tokens)
        span.set_attribute("llm.latency_ms", latency_ms)


def setup_tracing() -> None:
    """Configure OTel SDK with OTLP gRPC exporter and register the LiteLLM callback hook.

    Sets the global TracerProvider, attaches a BatchSpanProcessor that exports to the
    OTLP endpoint defined in ``settings.otel_exporter_otlp_endpoint``, and appends
    an ``_OtelLiteLLMCallback`` instance to ``litellm.callbacks`` so that every
    ``litellm.acompletion`` call automatically records LLM metrics on the current span.
    """
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    litellm.callbacks.append(_OtelLiteLLMCallback())


def get_tracer() -> trace.Tracer:
    """Return the OTel tracer for this service.

    Returns:
        A ``Tracer`` bound to ``settings.otel_service_name``.
        If ``setup_tracing`` has not been called, returns a no-op tracer.
    """
    return trace.get_tracer(settings.otel_service_name)

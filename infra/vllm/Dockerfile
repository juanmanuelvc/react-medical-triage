# vLLM in CPU-only mode.
# Builds are slow (~10 min) and the model download is ~1 GB the first run.
# Set VLLM_TARGET_DEVICE=cpu at build time so vLLM skips CUDA kernel compilation.
FROM python:3.12-slim

ENV VLLM_TARGET_DEVICE=cpu
ENV HF_HOME=/models

RUN pip install --no-cache-dir "vllm>=0.6.0"

EXPOSE 8000

CMD ["python", "-m", "vllm.entrypoints.openai.api_server", \
     "--model", "Qwen/Qwen2.5-0.5B-Instruct", \
     "--device", "cpu", \
     "--dtype", "float32", \
     "--max-model-len", "2048"]

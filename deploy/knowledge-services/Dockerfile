# Local, loopback-only service image. Build and real-model tests are separate gates.
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home expertos
WORKDIR /app
COPY pyproject.toml README.md ./
COPY tiny_experts ./tiny_experts
RUN python -m pip install --no-cache-dir --no-deps . \
    && mkdir -p /state && chown 10001:10001 /state
USER 10001:10001
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
ENTRYPOINT ["python", "-m", "tiny_experts.knowledge_services"]
CMD ["--root", "/state", "serve", "--port", "8765"]

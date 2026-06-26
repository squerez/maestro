# Optional feature set — pass at build time with --build-arg EXTRAS=<value>
#
#   docker build .                                        # framework only
#   docker build --build-arg EXTRAS=ui .                 # + web UI
#   docker build --build-arg EXTRAS=ui,observability .   # + UI + Prometheus metrics
#   docker build --build-arg EXTRAS=all .                # everything
#
# Available extras: ui, observability, lineage, quality, databricks, polars, all
ARG EXTRAS=""

FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock README.md ./
COPY maestro/ ./maestro/
COPY examples/ ./examples/

ARG EXTRAS
RUN if [ -n "$EXTRAS" ]; then \
        extra_flags=""; \
        for e in $(echo "$EXTRAS" | tr ',' ' '); do \
            extra_flags="$extra_flags --extra $e"; \
        done; \
        uv sync --no-dev $extra_flags; \
    else \
        uv sync --no-dev; \
    fi

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Default: interactive Python interpreter; overridden per service in docker-compose / k8s
CMD ["python"]

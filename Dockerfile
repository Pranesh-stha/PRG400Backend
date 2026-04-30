# Stage 1: Builder — install dependencies into an isolated virtual environment
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Test — builder venv + dev/test dependencies + source files
FROM builder AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY ./app ./app
COPY ./tests ./tests

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["pytest", "--cov=app", "--cov-report=term-missing", "-v"]


# Stage 3: Runtime — lean production image, no build tools
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY ./app ./app

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run as non-root user (security best practice)
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

# Factor VII: port is read from $PORT env var, defaulting to 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

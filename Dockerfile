
FROM python:3.11-slim AS build-env

# Install and configure poetry
ARG POETRY_VERSION=1.4.0
RUN pip install poetry=="${POETRY_VERSION}" \
    && poetry config virtualenvs.create false

WORKDIR /app
# Copy poetry files first - optimization to only do poetry install when config changes
COPY poetry.lock pyproject.toml ./
# Install dependencies
RUN poetry install --without dev --no-ansi

# Copy source code
COPY . .

# Default port
ENV PORT=8000
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=1

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:server


FROM python:3.10-slim AS build-env

# Install and configure poetry
ARG POETRY_VERSION=1.1.13
RUN pip install poetry=="${POETRY_VERSION}" \
    && poetry config virtualenvs.create false

WORKDIR /app
# Copy poetry files
COPY poetry.lock pyproject.toml ./
# Install dependencies
RUN poetry install --no-dev --no-ansi
# Copy project files
COPY *.py .

# Default port
ENV PORT=8000
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=1

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:server

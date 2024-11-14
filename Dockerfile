# Use Python 3.12.2 base image
FROM python:3.12.2-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Copy pyproject.toml and poetry.lock to the container
COPY pyproject.toml poetry.lock ./

# Configure Poetry to create the virtual environment inside the project directory
RUN poetry config virtualenvs.in-project true

# Install project dependencies
RUN poetry install --no-root --no-interaction --no-ansi

# Ensure the virtual environment's bin directory is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the application code
COPY . .

# Copy the model download script
COPY download_model.py .

# Run the model download script
RUN poetry run python download_model.py

# Expose the port that the app runs on
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Set the entrypoint to run the application with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]


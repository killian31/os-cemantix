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

# Download the model file during the build process
# Ensure that the model URL is accessible during the build
RUN poetry run python -c "\
import os; \
import requests; \
MODEL_URL = 'https://embeddings.net/embeddings/frWac_no_postag_no_phrase_700_skip_cut50.bin'; \
MODEL_PATH = 'models/frWac_no_postag_no_phrase_700_skip_cut50.bin'; \
if not os.path.exists(MODEL_PATH): \
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True); \
    print('Downloading the model...'); \
    response = requests.get(MODEL_URL, stream=True); \
    with open(MODEL_PATH, 'wb') as f: \
        for chunk in response.iter_content(chunk_size=8192): \
            if chunk: \
                f.write(chunk); \
    print('Model downloaded.'); \
else: \
    print('Model already exists.');"

# Expose the port that the app runs on
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Set the entrypoint to run the application with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]

